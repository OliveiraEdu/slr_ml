"""FastAPI application for the SLR Engine."""
import logging
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import papers, screening, prisma, enrichment, config, converters, enhanced_screening

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PRISMA 2020 SLR Engine",
    description="Systematic Literature Review Engine with ML-powered screening",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(screening.router)
app.include_router(prisma.router)
app.include_router(enrichment.router)
app.include_router(config.router)
app.include_router(converters.router)
app.include_router(enhanced_screening.router)

app_state = {
    "papers": [],
    "results": [],
    "config_loaded": False,
    "sources_config": None,
    "classification_config": None,
    "prisma_config": None,
    "extraction_data": [],
    "quality_data": [],
    "prisma_checklist": None,
}


@app.on_event("startup")
async def startup_event():
    """Load configuration on startup."""
    try:
        from src.models.config_loader import ConfigLoader
        config_dir = Path("config")
        if config_dir.exists():
            loader = ConfigLoader(str(config_dir))
            sources, classification, prisma_cfg = loader.load_all()
            app_state["sources_config"] = sources
            app_state["classification_config"] = classification
            app_state["prisma_config"] = prisma_cfg
            app_state["config_loaded"] = True
            logger.info("Configuration loaded successfully on startup")
        else:
            logger.warning("Config directory not found, skipping auto-load")
    except Exception as e:
        logger.error(f"Failed to load config on startup: {e}", exc_info=True)
        app_state["config_loaded"] = False


@app.get("/")
async def root():
    return {"message": "PRISMA 2020 SLR Engine API", "version": "0.5.0"}


@app.get("/health")
async def health_check():
    """Check health of API and dependent services."""
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
            except httpx.TimeoutException:
                services[name]["status"] = "unhealthy"
                services[name]["error"] = "Connection timeout"
                overall_healthy = False
            except httpx.RequestError as e:
                services[name]["status"] = "unhealthy"
                services[name]["error"] = f"Request error: {str(e)}"
                logger.warning("ML worker health check failed: %s", str(e))
                overall_healthy = False
            except Exception as e:
                services[name]["status"] = "unhealthy"
                services[name]["error"] = str(e)
                logger.error("Unexpected error in health check: %s", str(e))
                overall_healthy = False
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "services": services,
        "papers_loaded": len(app_state["papers"]),
        "config_loaded": app_state["config_loaded"],
    }
