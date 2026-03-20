"""Converters router - handles document format conversions."""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.schemas import ConvertMarkdownRequest, ConvertMarkdownResponse
from src.converters.md_to_latex import convert_markdown_to_latex, wrap_in_document

router = APIRouter(prefix="/convert", tags=["converters"])

logger = logging.getLogger(__name__)


@router.post("/markdown-to-latex", response_model=ConvertMarkdownResponse)
async def convert_md_to_latex(request: ConvertMarkdownRequest):
    """Convert markdown content to LaTeX format."""
    try:
        if request.file_path:
            path = Path(request.file_path)
            if not path.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
            markdown_content = path.read_text(encoding="utf-8")
            output_dir = str(path.parent / "mermaid_diagrams")
            base_filename = path.stem
        elif request.markdown:
            markdown_content = request.markdown
            output_dir = "outputs/mermaid_diagrams"
            base_filename = "diagram"
        else:
            raise HTTPException(status_code=400, detail="Either 'markdown' or 'file_path' must be provided")
        
        logger.debug("Starting markdown to LaTeX conversion")
        latex_content = convert_markdown_to_latex(
            markdown_content,
            output_dir=output_dir if request.extract_mermaid else None,
            base_filename=base_filename
        )
        logger.debug("Conversion completed, length: %d", len(latex_content))
        
        if request.wrap_document:
            latex_content = wrap_in_document(latex_content, request.title)
        
        return ConvertMarkdownResponse(latex=latex_content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Markdown to LaTeX conversion failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
