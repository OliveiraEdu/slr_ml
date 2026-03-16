"""FastAPI application for the SLR Engine."""
from typing import Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.models.config_loader import ConfigLoader
from src.models.schemas import (
    Paper, PrismaFlowData, ScreeningResult, SourceName,
    SourcesConfig, ClassificationConfig, PrismaConfig,
)
from src.loaders.bibtex_loader import BibtexLoader
from src.loaders.csv_loader import CsvLoader
from src.connectors.arxiv_connector import ArxivConnector
from src.pipeline.deduplication import Deduplicator
from src.pipeline.screening import ScreeningPipeline, ScreeningManager
from src.pipeline.prisma_generator import PrismaGenerator
from src.ml.classifier import SciBERTClassifier


app = FastAPI(
    title="PRISMA 2020 SLR Engine",
    description="Systematic Literature Review Engine with ML-powered screening",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoadConfigRequest(BaseModel):
    config_dir: str = "config"


class ImportRequest(BaseModel):
    source: str
    file_path: str
    format: str = "bibtex"


class ArxivRequest(BaseModel):
    query: str
    max_results: int = 50
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    categories: list[str] = []


class DedupeRequest(BaseModel):
    papers: list[Paper]


class ScreenRequest(BaseModel):
    papers: list[Paper]
    stage: str = "title_abstract"
    include_prompt: str = "This paper is relevant to the research question"
    exclude_prompt: str = "This paper is not relevant to the research question"
    threshold: float = 0.5


app_state = {
    "papers": [],
    "results": [],
    "config_loaded": False,
    "sources_config": None,
    "classification_config": None,
    "prisma_config": None,
}


@app.get("/")
async def root():
    return {"message": "PRISMA 2020 SLR Engine API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "papers_loaded": len(app_state["papers"]),
        "config_loaded": app_state["config_loaded"],
    }


@app.post("/config/load")
async def load_config(request: LoadConfigRequest):
    """Load configuration from YAML files."""
    try:
        loader = ConfigLoader(request.config_dir)
        sources, classification, prisma = loader.load_all()

        app_state["sources_config"] = sources
        app_state["classification_config"] = classification
        app_state["prisma_config"] = prisma
        app_state["config_loaded"] = True

        return {
            "status": "loaded",
            "enabled_sources": loader.get_enabled_sources(),
            "config_dir": request.config_dir,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/status")
async def config_status():
    """Get current configuration status."""
    return {
        "loaded": app_state["config_loaded"],
        "enabled_sources": _get_enabled_sources(),
    }


def _get_enabled_sources():
    sources = app_state["sources_config"]
    if not sources:
        return []
    enabled = []
    for name in ["wos", "ieee", "acm", "scopus", "arxiv"]:
        source = getattr(sources, name, None)
        if source and source.enabled:
            enabled.append(name)
    return enabled


@app.post("/papers/import")
async def import_papers(request: ImportRequest):
    """Import papers from BibTeX or CSV file."""
    try:
        source = SourceName(request.source.lower())

        if request.format.lower() == "bibtex":
            loader = BibtexLoader()
            papers = loader.load_file(request.file_path, source)
        elif request.format.lower() == "csv":
            loader = CsvLoader()
            papers = loader.load_file(request.file_path, source, format_type=request.source.lower())
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

        app_state["papers"].extend(papers)

        return {
            "status": "imported",
            "source": request.source,
            "count": len(papers),
            "total_papers": len(app_state["papers"]),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/papers/arxiv")
async def query_arxiv(request: ArxivRequest):
    """Query arXiv API for papers."""
    try:
        connector = ArxivConnector()
        papers = connector.search(
            query=request.query,
            max_results=request.max_results,
            date_from=request.date_from,
            date_to=request.date_to,
            categories=request.categories if request.categories else None,
        )

        app_state["papers"].extend(papers)

        return {
            "status": "imported",
            "source": "arxiv",
            "query": request.query,
            "count": len(papers),
            "total_papers": len(app_state["papers"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/papers/list")
async def list_papers(
    source: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
):
    """List loaded papers."""
    papers = app_state["papers"]

    if source:
        papers = [p for p in papers if p.source.value == source.lower()]

    total = len(papers)
    papers_page = papers[offset:offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "papers": [p.model_dump() for p in papers_page],
    }


@app.post("/papers/dedupe")
async def deduplicate_papers(request: DedupeRequest):
    """Run deduplication on papers."""
    try:
        dedup = Deduplicator()
        papers, report = dedup.deduplicate(request.papers)

        app_state["papers"] = papers

        return {
            "status": "deduplicated",
            "original_count": report["original_count"],
            "duplicates_removed": report["duplicates_removed"],
            "final_count": report["final_count"],
            "duplicate_groups": report["duplicate_groups"][:10],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/screening/run")
async def run_screening(request: ScreenRequest):
    """Run ML screening on papers."""
    try:
        classifier = SciBERTClassifier(
            model_name="allenai/scibert_scivocab_uncased",
            device="cpu",
        )

        results = []
        for paper in request.papers:
            result = classifier.classify_relevance(
                paper=paper,
                include_prompt=request.include_prompt,
                exclude_prompt=request.exclude_prompt,
                threshold=request.threshold,
            )
            results.append(result)

        app_state["results"].extend(results)

        included = sum(1 for r in results if r.decision == "include")
        excluded = sum(1 for r in results if r.decision == "exclude")
        uncertain = sum(1 for r in results if r.decision == "uncertain")

        classifier.unload()

        return {
            "status": "screening_complete",
            "stage": request.stage,
            "total_screened": len(results),
            "included": included,
            "excluded": excluded,
            "uncertain": uncertain,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screening/results")
async def get_screening_results(
    decision: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    """Get screening results."""
    results = app_state["results"]

    if decision:
        results = [r for r in results if r.decision == decision]

    return {
        "total": len(results),
        "results": [r.model_dump() for r in results[:limit]],
    }


@app.get("/prisma/flow")
async def get_prisma_flow():
    """Get PRISMA flow diagram data."""
    generator = PrismaGenerator(app_state.get("prisma_config"))
    flow_data = generator.generate_flow_data(
        app_state["papers"],
        app_state["results"],
    )
    return flow_data.model_dump()


@app.get("/prisma/export")
async def export_prisma_flow(format: str = Query("json", regex="^(json|csv)$")):
    """Export PRISMA flow diagram."""
    generator = PrismaGenerator(app_state.get("prisma_config"))
    flow_data = generator.generate_flow_data(
        app_state["papers"],
        app_state["results"],
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/prisma")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"flow_diagram_{timestamp}.{format}"

    generator.export_flow_diagram(flow_data, str(output_path), format)

    return {
        "status": "exported",
        "format": format,
        "path": str(output_path),
    }


@app.post("/papers/clear")
async def clear_papers():
    """Clear all loaded papers and results."""
    app_state["papers"] = []
    app_state["results"] = []
    return {"status": "cleared"}
