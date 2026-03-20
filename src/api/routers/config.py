"""Configuration router - handles config loading and updating."""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.config_loader import ConfigLoader

router = APIRouter(prefix="/config", tags=["config"])

import yaml


class LoadConfigRequest(BaseModel):
    config_dir: str = "config"


class UpdateClassificationRequest(BaseModel):
    research_question: Optional[str] = None
    relevance: Optional[dict] = None
    thresholds: Optional[dict] = None
    model: Optional[dict] = None
    sub_questions: Optional[dict] = None
    inclusion_criteria: Optional[dict] = None
    exclusion_criteria: Optional[dict] = None
    keywords: Optional[dict] = None


def get_app_state():
    from src.api.main import app_state
    return app_state


def _get_enabled_sources():
    app_state = get_app_state()
    sources = app_state["sources_config"]
    if not sources:
        return []
    enabled = []
    for name in ["wos", "ieee", "acm", "scopus", "arxiv"]:
        source = getattr(sources, name, None)
        if source and source.enabled:
            enabled.append(name)
    return enabled


@router.post("/load")
async def load_config(request: LoadConfigRequest):
    """Load configuration from YAML files."""
    app_state = get_app_state()
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


@router.get("/status")
async def config_status():
    """Get current configuration status."""
    app_state = get_app_state()
    return {
        "loaded": app_state["config_loaded"],
        "enabled_sources": _get_enabled_sources(),
    }


@router.get("/classification")
async def get_classification_config():
    """Get current classification configuration."""
    config_path = Path("config/classification.yaml")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Classification config not found")
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        return {"classification": config}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"Invalid YAML: {str(e)}")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"File error: {str(e)}")


@router.put("/classification")
async def update_classification_config(request: UpdateClassificationRequest):
    """Update classification configuration."""
    config_path = Path("config/classification.yaml")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Classification config not found")
    
    try:
        with open(config_path) as f:
            current_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"Invalid YAML: {str(e)}")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"File error: {str(e)}")
    
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
    
    try:
        with open(config_path, "w") as f:
            yaml.dump(current_config, f, default_flow_style=False)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Write error: {str(e)}")
    
    app_state = get_app_state()
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
