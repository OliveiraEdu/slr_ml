"""FastAPI application for the SLR Engine."""
from typing import Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.models.config_loader import ConfigLoader
from src.models.schemas import (
    Paper, PrismaFlowData, ScreeningResult, SourceName,
    SourcesConfig, ClassificationConfig, PrismaConfig,
    RankingWeights,
)
from src.loaders.bibtex_loader import BibtexLoader
from src.loaders.csv_loader import CsvLoader
from src.connectors.arxiv_connector import ArxivConnector
from src.pipeline.deduplication import Deduplicator
from src.pipeline.screening import ScreeningPipeline, ScreeningManager
from src.pipeline.prisma_generator import PrismaGenerator
from src.pipeline.extraction import ExtractionExtractor, QualityAssessor
from src.ml.classifier import SciBERTClassifier, BackendType
from src.connectors.doi_connector import DOIMetadataConnector


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


class UpdateClassificationRequest(BaseModel):
    """Request model for updating classification configuration."""
    research_question: Optional[str] = None
    relevance: Optional[dict] = None
    thresholds: Optional[dict] = None
    model: Optional[dict] = None
    sub_questions: Optional[dict] = None
    inclusion_criteria: Optional[dict] = None
    exclusion_criteria: Optional[dict] = None
    keywords: Optional[dict] = None


class ImportRequest(BaseModel):
    source: str
    file_path: str
    format: str = "bibtex"


class ImportDirectoryRequest(BaseModel):
    directory: str = "inputs"
    auto_detect: bool = True


class ArxivRequest(BaseModel):
    query: str
    max_results: int = 50
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    categories: list[str] = []


class DedupeRequest(BaseModel):
    papers: Optional[list[Paper]] = None


class ScreenRequest(BaseModel):
    papers: Optional[list[Paper]] = None
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
    "extraction_data": [],
    "quality_data": [],
}


@app.get("/")
async def root():
    return {"message": "PRISMA 2020 SLR Engine API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    import httpx
    
    services = {
        "api": {"status": "healthy", "url": "self"},
        "ml_worker": {"status": "unhealthy", "url": "http://ml-worker:8001/health"},
    }
    
    overall_healthy = True
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, info in services.items():
            if info["url"] == "self":
                continue
            try:
                response = await client.get(info["url"])
                if response.status_code == 200:
                    services[name]["status"] = "healthy"
                else:
                    services[name]["status"] = "unhealthy"
                    services[name]["error"] = f"HTTP {response.status_code}"
                    overall_healthy = False
            except Exception as e:
                services[name]["status"] = "unhealthy"
                services[name]["error"] = str(e)
                overall_healthy = False
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "services": services,
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


@app.get("/config/classification")
async def get_classification_config():
    """Get current classification configuration."""
    import yaml
    
    config_path = Path("config/classification.yaml")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Classification config not found")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    return {"classification": config}


@app.put("/config/classification")
async def update_classification_config(request: UpdateClassificationRequest):
    """Update classification configuration (research question, sub-questions, criteria, thresholds, etc.)."""
    import yaml
    
    config_path = Path("config/classification.yaml")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Classification config not found")
    
    with open(config_path) as f:
        current_config = yaml.safe_load(f)
    
    if "classification" not in current_config:
        current_config["classification"] = {}
    
    cls_config = current_config["classification"]
    
    if request.research_question is not None:
        cls_config["research_question"] = request.research_question
    
    if request.relevance is not None:
        cls_config["relevance"] = request.relevance
    
    if request.thresholds is not None:
        cls_config["thresholds"] = request.thresholds
    
    if request.model is not None:
        cls_config["model"] = request.model
    
    if request.sub_questions is not None:
        cls_config["sub_questions"] = request.sub_questions
    
    if request.inclusion_criteria is not None:
        cls_config["inclusion_criteria"] = request.inclusion_criteria
    
    if request.exclusion_criteria is not None:
        cls_config["exclusion_criteria"] = request.exclusion_criteria
    
    if request.keywords is not None:
        cls_config["keywords"] = request.keywords
    
    with open(config_path, "w") as f:
        yaml.dump(current_config, f, default_flow_style=False)
    
    app_state["classification_config"] = None
    
    return {
        "status": "updated",
        "config_path": str(config_path),
        "updated_fields": {
            "research_question": request.research_question is not None,
            "relevance": request.relevance is not None,
            "thresholds": request.thresholds is not None,
            "model": request.model is not None,
            "sub_questions": request.sub_questions is not None,
            "inclusion_criteria": request.inclusion_criteria is not None,
            "exclusion_criteria": request.exclusion_criteria is not None,
            "keywords": request.keywords is not None,
        }
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


@app.post("/papers/import-directory")
async def import_directory(request: ImportDirectoryRequest):
    """
    Import all supported files from a directory.
    
    Automatically detects source (wos, ieee, acm, scopus) and format (bibtex, csv)
    based on filename patterns.
    """
    import os
    import re
    
    SOURCE_PATTERNS = {
        "wos": [r"wos.*\.bib", r"wos.*\.csv", r"savedrecs.*\.bib"],
        "ieee": [r"ieee.*\.bib", r"ieee.*\.csv"],
        "acm": [r"acm.*\.bib", r"acm.*\.csv"],
        "scopus": [r"scopus.*\.bib", r"scopus.*\.csv", r"export.*\.csv"],
    }
    
    SOURCE_MAPPING = {
        "bib": "bibtex",
        "csv": "csv",
    }
    
    dir_path = Path(request.directory)
    if not dir_path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.directory}")
    
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {request.directory}")
    
    all_papers = []
    files_imported = []
    errors = []
    
    for file_path in dir_path.iterdir():
        if not file_path.is_file():
            continue
        
        filename = file_path.name.lower()
        ext = file_path.suffix.lower().lstrip(".")
        
        detected_source = None
        for source, patterns in SOURCE_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, filename):
                    detected_source = source
                    break
            if detected_source:
                break
        
        if not detected_source:
            continue
        
        try:
            file_format = SOURCE_MAPPING.get(ext, ext)
            
            if file_format == "bibtex":
                loader = BibtexLoader()
                papers = loader.load_file(str(file_path), SourceName(detected_source))
            elif file_format == "csv":
                loader = CsvLoader()
                papers = loader.load_file(str(file_path), SourceName(detected_source), format_type=detected_source)
            else:
                errors.append(f"{file_path.name}: unsupported format {file_format}")
                continue
            
            all_papers.extend(papers)
            files_imported.append({
                "file": file_path.name,
                "source": detected_source,
                "format": file_format,
                "count": len(papers),
            })
            
        except Exception as e:
            errors.append(f"{file_path.name}: {str(e)}")
    
    if not files_imported:
        return {
            "status": "no_files",
            "message": "No supported files found in directory",
            "directory": request.directory,
            "supported_patterns": SOURCE_PATTERNS,
        }
    
    app_state["papers"].extend(all_papers)
    
    return {
        "status": "imported",
        "directory": request.directory,
        "files_imported": files_imported,
        "total_files": len(files_imported),
        "total_papers": len(all_papers),
        "total_papers_in_store": len(app_state["papers"]),
        "errors": errors if errors else None,
    }


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
async def deduplicate_papers(
    request: DedupeRequest = Body(default=DedupeRequest()),
):
    """Run deduplication on papers. Uses papers from app_state if none provided."""
    try:
        # Use papers from request or from app_state
        papers_to_dedupe = request.papers if request.papers else app_state["papers"]
        
        if not papers_to_dedupe:
            return {
                "status": "no_papers",
                "message": "No papers to deduplicate",
            }
        
        dedup = Deduplicator()
        papers, report = dedup.deduplicate(papers_to_dedupe)

        # Update app_state with deduplicated papers
        if not request.papers:
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
async def run_screening(
    request: ScreenRequest = Body(default=ScreenRequest()),
):
    """Run ML screening on papers. Falls back to keyword-based if PyTorch unavailable."""
    try:
        # Use papers from request or from app_state
        papers_to_screen = request.papers if request.papers else app_state["papers"]
        
        if not papers_to_screen:
            return {
                "status": "no_papers",
                "message": "No papers to screen",
            }
        
        # Load keywords from config if available
        keywords = {}
        if app_state.get("classification_config") and app_state["classification_config"].keywords:
            keywords = {
                "required": app_state["classification_config"].keywords.required or [],
                "optional": app_state["classification_config"].keywords.optional or [],
            }
        
        # Get ranking weights from config
        ranking_weights = RankingWeights()
        if app_state.get("classification_config") and app_state["classification_config"].ranking_weights:
            ranking_weights = app_state["classification_config"].ranking_weights
        
        classifier = SciBERTClassifier(
            model_name="allenai/scibert_scivocab_uncased",
            device="cpu",
            backend=BackendType.AUTO,
            keywords=keywords,
            ranking_weights=ranking_weights,
        )

        results = []
        for paper in papers_to_screen:
            result = classifier.classify_relevance(
                paper=paper,
                include_prompt=request.include_prompt,
                exclude_prompt=request.exclude_prompt,
                threshold=request.threshold,
            )
            results.append(result)

        # Update app_state results if using app_state papers
        if not request.papers:
            app_state["results"] = results
        else:
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
            "backend": classifier.backend.value if hasattr(classifier.backend, 'value') else str(classifier.backend),
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


@app.get("/screening/rank")
async def rank_papers(
    n: int = Query(50, ge=1, le=500, description="Number of top papers to return"),
    decision: Optional[str] = Query(None, description="Filter by decision (include/exclude/uncertain)"),
    sort_by: str = Query("composite", regex="^(composite|relevance|citations|recency)$", description="Sort by composite, relevance, citations, or recency"),
):
    """Get top N papers ranked by composite score (relevance + citations + recency)."""
    results = app_state["results"]
    papers = app_state["papers"]
    
    if decision:
        results = [r for r in results if r.decision == decision]
    
    paper_map = {p.id: p for p in papers}
    
    ranked = []
    for r in results:
        p = paper_map.get(r.paper_id)
        if p:
            ranked.append({
                "paper": p.model_dump(),
                "result": r.model_dump(),
            })
    
    if sort_by == "relevance":
        ranked.sort(key=lambda x: x["result"]["relevance_score"], reverse=True)
    elif sort_by == "citations":
        ranked.sort(key=lambda x: x["result"]["citation_score"], reverse=True)
    elif sort_by == "recency":
        ranked.sort(key=lambda x: x["result"]["recency_score"], reverse=True)
    else:
        ranked.sort(key=lambda x: x["result"]["composite_score"], reverse=True)
    
    return {
        "total": len(ranked),
        "top_n": n,
        "sort_by": sort_by,
        "papers": ranked[:n],
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


@app.post("/prisma/extract")
async def run_extraction():
    """Run extraction and quality assessment on included studies."""
    included_papers = [
        p for p in app_state["papers"]
        if any(r.paper_id == p.id and r.decision == "include" for r in app_state["results"])
    ]

    if not included_papers:
        return {
            "status": "no_included",
            "message": "No included papers found. Run screening first.",
        }

    extractor = ExtractionExtractor()
    extraction_data = extractor.extract(included_papers)

    assessor = QualityAssessor()
    quality_data = assessor.assess(included_papers)

    app_state["extraction_data"] = extraction_data
    app_state["quality_data"] = quality_data

    return {
        "status": "extracted",
        "papers_extracted": len(extraction_data),
        "quality_assessed": len(quality_data),
    }


@app.get("/prisma/report")
async def get_prisma_report(format: str = Query("markdown", regex="^(markdown|json)$")):
    """Generate full PRISMA 2020 report."""
    included_papers = [
        p for p in app_state["papers"]
        if any(r.paper_id == p.id and r.decision == "include" for r in app_state["results"])
    ]

    extraction_data = app_state.get("extraction_data", [])
    quality_data = app_state.get("quality_data", [])

    if not included_papers:
        raise HTTPException(status_code=400, detail="No included papers found. Run screening first.")

    generator = PrismaGenerator(app_state.get("prisma_config"))

    if format == "json":
        flow_data = generator.generate_flow_data(app_state["papers"], app_state["results"])
        return {
            "flow_data": flow_data.model_dump(),
            "extraction_data": [e.model_dump() for e in extraction_data],
            "quality_data": [q.model_dump() for q in quality_data],
        }

    markdown_report = generator.generate_markdown_report(
        app_state["papers"],
        app_state["results"],
        included_papers,
        extraction_data,
        quality_data,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/prisma")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"report_{timestamp}.md"

    with open(output_path, "w") as f:
        f.write(markdown_report)

    return {
        "status": "generated",
        "format": "markdown",
        "report": markdown_report,
        "path": str(output_path),
    }


@app.get("/prisma/extraction")
async def get_extraction_data():
    """Get extraction data for included studies."""
    extraction_data = app_state.get("extraction_data", [])
    if not extraction_data:
        return {"status": "not_extracted", "message": "Run /prisma/extract first"}

    return {
        "total": len(extraction_data),
        "data": [e.model_dump() for e in extraction_data],
    }


@app.get("/prisma/quality")
async def get_quality_data():
    """Get quality assessment data."""
    quality_data = app_state.get("quality_data", [])
    if not quality_data:
        return {"status": "not_assessed", "message": "Run /prisma/extract first"}

    return {
        "total": len(quality_data),
        "data": [q.model_dump() for q in quality_data],
    }


@app.post("/papers/clear")
async def clear_papers():
    """Clear all loaded papers and results."""
    app_state["papers"] = []
    app_state["results"] = []
    return {"status": "cleared"}


@app.post("/papers/enrich")
async def enrich_papers_with_doi(
    skip_existing: bool = True,
    email: Optional[str] = None,
    limit: Optional[int] = None,
):
    """Enrich paper metadata using CrossRef and DataCite APIs.

    Queries DOI metadata to get citation counts, references, publication dates,
    and other metadata. Uses free tier rate limits (10 req/sec).

    Args:
        skip_existing: Skip papers that already have citation counts
        email: Optional email for CrossRef (higher rate limits: 50/sec)
        limit: Maximum number of papers to enrich (default: all)
    """
    papers = app_state.get("papers", [])
    papers_with_doi = [p for p in papers if p.doi]

    if not papers_with_doi:
        return {
            "status": "no_dois",
            "message": "No papers with DOIs found",
            "total_papers": len(papers),
            "papers_with_doi": 0,
        }

    if limit:
        papers_with_doi = papers_with_doi[:limit]

    connector = DOIMetadataConnector(email=email, rate_limit=0.1)
    enriched_papers = connector.batch_enrich(papers_with_doi, skip_existing=skip_existing)

    total_citations = sum(p.citations for p in enriched_papers)
    enriched_count = sum(1 for p in enriched_papers if p.raw_metadata.get("doi_source"))

    paper_map = {p.id: p for p in papers}
    paper_map.update({p.id: p for p in enriched_papers})
    app_state["papers"] = list(paper_map.values())

    return {
        "status": "enriched",
        "total_papers": len(enriched_papers),
        "papers_with_doi": len(papers_with_doi),
        "newly_enriched": enriched_count,
        "total_citations": total_citations,
    }


@app.get("/papers/enrich/{paper_id}")
async def enrich_single_paper(
    paper_id: str,
    email: Optional[str] = None,
):
    """Enrich a single paper by ID using CrossRef/DataCite."""
    papers = app_state.get("papers", [])
    paper = next((p for p in papers if p.id == paper_id), None)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.doi:
        return {
            "status": "no_doi",
            "message": "Paper has no DOI",
            "paper_id": paper_id,
        }

    connector = DOIMetadataConnector(email=email, rate_limit=0.1)
    enriched_paper = connector.enrich_paper(paper)

    for i, p in enumerate(papers):
        if p.id == paper_id:
            papers[i] = enriched_paper
            break

    return {
        "status": "enriched",
        "paper_id": paper_id,
        "doi": enriched_paper.doi,
        "citations": enriched_paper.citations,
        "publisher": enriched_paper.raw_metadata.get("publisher"),
        "publication_date": enriched_paper.raw_metadata.get("publication_date"),
        "source": enriched_paper.raw_metadata.get("doi_source"),
    }
