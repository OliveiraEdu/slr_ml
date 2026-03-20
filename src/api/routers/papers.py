"""Papers router - handles paper import, export, and listing."""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from src.models.schemas import Paper, SourceName, FullTextSource, ScreeningDecision
from src.loaders.bibtex_loader import BibtexLoader
from src.loaders.csv_loader import CsvLoader
from src.connectors.arxiv_connector import ArxivConnector
from src.connectors.url_downloader import URLDownloader, get_all_source_urls, get_source_urls
from src.pipeline.deduplication import Deduplicator

router = APIRouter(prefix="/papers", tags=["papers"])

FT_STORAGE_DIR = Path("outputs/fulltext")
FT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_DIR = Path("inputs")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


def get_app_state():
    from src.api.main import app_state
    return app_state


@router.post("/import")
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

        app_state = get_app_state()
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


@router.post("/import-directory")
async def import_directory(request: ImportDirectoryRequest):
    """Import all supported files from a directory."""
    app_state = get_app_state()
    
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


@router.post("/arxiv")
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

        app_state = get_app_state()
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


@router.get("/list")
async def list_papers(
    source: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
):
    """List loaded papers."""
    app_state = get_app_state()
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


@router.post("/dedupe")
async def deduplicate_papers(
    request: DedupeRequest = Body(default=DedupeRequest()),
):
    """Run deduplication on papers."""
    app_state = get_app_state()
    try:
        papers_to_dedupe = request.papers if request.papers else app_state["papers"]
        
        if not papers_to_dedupe:
            return {
                "status": "no_papers",
                "message": "No papers to deduplicate",
            }
        
        dedup = Deduplicator()
        papers, report = dedup.deduplicate(papers_to_dedupe)

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


@router.post("/clear")
async def clear_papers():
    """Clear all loaded papers and results."""
    app_state = get_app_state()
    app_state["papers"] = []
    app_state["results"] = []
    return {"status": "cleared"}


# Full-Text Management Endpoints

class AttachFullTextRequest(BaseModel):
    content: Optional[str] = None
    file_path: Optional[str] = None


class FlagPaperRequest(BaseModel):
    reason: str


@router.get("/flagged")
async def get_flagged_papers():
    """Get papers flagged for no full-text availability."""
    app_state = get_app_state()
    papers = app_state["papers"]
    
    flagged = [p for p in papers if p.flagged_reason is not None]
    
    return {
        "total": len(flagged),
        "flagged_papers": [
            {
                "id": p.id,
                "title": p.title,
                "source": p.source.value,
                "flagged_reason": p.flagged_reason,
            }
            for p in flagged
        ],
    }


@router.post("/flag/{paper_id}")
async def flag_paper(paper_id: str, request: FlagPaperRequest):
    """Flag a paper for no full-text availability."""
    app_state = get_app_state()
    
    for i, paper in enumerate(app_state["papers"]):
        if paper.id == paper_id:
            app_state["papers"][i].flagged_reason = request.reason
            app_state["papers"][i].full_text_retrievable = False
            
            for j, result in enumerate(app_state["results"]):
                if result.paper_id == paper_id:
                    app_state["results"][j].flagged_for_no_ft = True
            
            return {
                "status": "flagged",
                "paper_id": paper_id,
                "reason": request.reason,
            }
    
    raise HTTPException(status_code=404, detail="Paper not found")


@router.get("/retrievable")
async def get_retrievable_papers():
    """Get papers eligible for full-text retrieval (have DOI or are ArXiv)."""
    app_state = get_app_state()
    papers = app_state["papers"]
    results = app_state["results"]
    
    # Get papers that passed Stage 1 and need FT
    included_ids = {
        r.paper_id for r in results 
        if r.decision == ScreeningDecision.INCLUDE 
        and r.phase.value == "title_abstract"
    }
    
    retrievable = []
    unavailable = []
    
    for paper in papers:
        if paper.id not in included_ids:
            continue
            
        if paper.source == SourceName.ARXIV:
            retrievable.append(paper)
        elif paper.doi:
            retrievable.append(paper)
        elif paper.flagged_reason:
            unavailable.append(paper)
        else:
            unavailable.append(paper)
    
    return {
        "retrievable_count": len(retrievable),
        "unavailable_count": len(unavailable),
        "retrievable_papers": [
            {
                "id": p.id,
                "title": p.title,
                "source": p.source.value,
                "has_doi": bool(p.doi),
                "is_arxiv": p.source == SourceName.ARXIV,
            }
            for p in retrievable
        ],
        "unavailable_papers": [
            {
                "id": p.id,
                "title": p.title,
                "source": p.source.value,
                "reason": p.flagged_reason or "No DOI and not ArXiv",
            }
            for p in unavailable
        ],
    }


@router.get("/{paper_id}/fulltext")
async def get_paper_fulltext(paper_id: str):
    """Get full-text content for a paper."""
    app_state = get_app_state()
    
    paper = next((p for p in app_state["papers"] if p.id == paper_id), None)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.full_text:
        return {
            "paper_id": paper_id,
            "source": paper.full_text_source,
            "content": paper.full_text,
            "storage": "inline",
        }
    
    if paper.full_text_path:
        path = Path(paper.full_text_path)
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return {
                "paper_id": paper_id,
                "source": paper.full_text_source,
                "content": content,
                "storage": "file",
                "path": str(path),
            }
    
    return {
        "paper_id": paper_id,
        "source": paper.full_text_source,
        "content": None,
        "status": "not_retrieved",
    }


@router.post("/{paper_id}/fulltext")
async def attach_paper_fulltext(paper_id: str, request: AttachFullTextRequest):
    """Attach full-text content to a paper."""
    app_state = get_app_state()
    
    for i, paper in enumerate(app_state["papers"]):
        if paper.id == paper_id:
            content = None
            source = FullTextSource.MANUAL
            
            if request.content:
                content = request.content
                source = FullTextSource.MANUAL
                
            elif request.file_path:
                path = Path(request.file_path)
                if not path.exists():
                    raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
                content = path.read_text(encoding="utf-8")
                source = FullTextSource.MANUAL
                
                # Save copy to outputs
                dest_path = FT_STORAGE_DIR / f"{paper_id}.txt"
                dest_path.write_text(content, encoding="utf-8")
                app_state["papers"][i].full_text_path = str(dest_path)
            
            else:
                raise HTTPException(status_code=400, detail="Either 'content' or 'file_path' required")
            
            app_state["papers"][i].full_text = content
            app_state["papers"][i].full_text_source = source
            
            # Update screening results
            for j, result in enumerate(app_state["results"]):
                if result.paper_id == paper_id:
                    app_state["results"][j].full_text_retrieved = True
                    app_state["results"][j].full_text_source = source
            
            return {
                "status": "attached",
                "paper_id": paper_id,
                "source": source.value,
                "length": len(content) if content else 0,
            }
    
    raise HTTPException(status_code=404, detail="Paper not found")


@router.get("/progress/fulltext")
async def get_fulltext_progress():
    """Get full-text retrieval progress."""
    app_state = get_app_state()
    papers = app_state["papers"]
    results = app_state["results"]
    
    included_ids = {
        r.paper_id for r in results 
        if r.decision == ScreeningDecision.INCLUDE 
        and r.phase.value == "title_abstract"
    }
    
    total_needed = sum(1 for p in papers if p.id in included_ids)
    retrieved = 0
    flagged = 0
    pending = 0
    
    for paper in papers:
        if paper.id not in included_ids:
            continue
        
        if paper.full_text or paper.full_text_path:
            retrieved += 1
        elif paper.flagged_reason:
            flagged += 1
        else:
            pending += 1
    
    return {
        "total_needed": total_needed,
        "retrieved": retrieved,
        "pending": pending,
        "flagged": flagged,
        "progress_percent": round((retrieved / total_needed * 100) if total_needed > 0 else 0, 1),
    }


# URL Import Endpoints

class ImportFromURLRequest(BaseModel):
    source: str
    url: str


class ImportFromConfigRequest(BaseModel):
    sources: Optional[list[str]] = None  # If None, import all enabled


@router.get("/sources")
async def get_available_sources():
    """Get list of configured data sources from data_sources.yaml."""
    try:
        from src.connectors.url_downloader import load_data_sources_config
        config = load_data_sources_config()
        
        sources = config.get("sources", {})
        download_config = config.get("download", {})
        
        available = []
        for name, conf in sources.items():
            if conf.get("enabled", False):
                available.append({
                    "name": name,
                    "description": conf.get("description", ""),
                    "base_url": conf.get("base_url", ""),
                    "files": conf.get("files", []),
                    "format": conf.get("format", "auto"),
                })
        
        return {
            "status": "loaded",
            "config_path": "config/data_sources.yaml",
            "output_dir": download_config.get("output_dir", "inputs"),
            "sources": available,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_from_url(request: ImportFromURLRequest):
    """Download a file from URL and save to inputs directory."""
    try:
        downloader = URLDownloader(
            cache_dir="cache/downloads",
            retry_attempts=3,
        )
        
        filename = request.url.split("/")[-1]
        output_path = DOWNLOAD_DIR / filename
        
        path, content = downloader.download_file(
            url=request.url,
            output_path=str(output_path),
            use_cache=True,
        )
        
        return {
            "status": "downloaded",
            "url": request.url,
            "local_path": path,
            "size": len(content),
            "source": request.source,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-all")
async def download_all_sources(
    request: ImportFromConfigRequest = ImportFromConfigRequest(),
):
    """Download all configured source files from their URLs."""
    try:
        downloader = URLDownloader(
            cache_dir="cache/downloads",
            retry_attempts=3,
        )
        
        config = downloader.load_config() if hasattr(downloader, 'load_config') else None
        all_urls = get_all_source_urls(config)
        
        if request.sources:
            all_urls = {k: v for k, v in all_urls.items() if k in request.sources}
        
        if not all_urls:
            return {
                "status": "no_sources",
                "message": "No enabled sources found or requested",
            }
        
        results = {
            "sources": {},
            "total_downloaded": 0,
            "total_failed": 0,
        }
        
        for source_name, urls in all_urls.items():
            source_results = downloader.download_multiple(
                urls=urls,
                output_dir=str(DOWNLOAD_DIR),
                source_name=source_name,
            )
            
            results["sources"][source_name] = source_results
            results["total_downloaded"] += len(source_results["successful"])
            results["total_failed"] += len(source_results["failed"])
        
        return {
            "status": "complete",
            "download_dir": str(DOWNLOAD_DIR),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-downloaded")
async def import_downloaded_files(
    directory: str = "inputs",
    auto_detect: bool = True,
):
    """Import all downloaded files from a directory.
    
    This is typically called after downloading files with /papers/download-all.
    """
    return await import_directory(
        ImportDirectoryRequest(
            directory=directory,
            auto_detect=auto_detect,
        )
    )


@router.post("/import-from-url")
async def import_and_load_from_url(request: ImportFromURLRequest):
    """Download a file from URL and immediately import it as papers."""
    try:
        downloader = URLDownloader(
            cache_dir="cache/downloads",
            retry_attempts=3,
        )
        
        filename = request.url.split("/")[-1]
        output_path = DOWNLOAD_DIR / filename
        
        path, _ = downloader.download_file(
            url=request.url,
            output_path=str(output_path),
            use_cache=True,
        )
        
        ext = filename.lower().split(".")[-1]
        source = SourceName(request.source.lower())
        
        if ext == "bib":
            loader = BibtexLoader()
            papers = loader.load_file(path, source)
        elif ext == "csv":
            loader = CsvLoader()
            papers = loader.load_file(path, source, format_type=request.source.lower())
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}",
            )
        
        app_state = get_app_state()
        app_state["papers"].extend(papers)
        
        return {
            "status": "imported",
            "source": request.source,
            "url": request.url,
            "file_path": path,
            "papers_imported": len(papers),
            "total_papers": len(app_state["papers"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
