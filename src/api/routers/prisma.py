"""PRISMA router - handles PRISMA flow diagrams and reports."""
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.models.schemas import (
    ConvertMarkdownRequest, ConvertMarkdownResponse, PrismaChecklist, 
    PrismaChecklistItem, PrismaProtocol
)
from src.pipeline.prisma_generator import PrismaGenerator
from src.pipeline.extraction import ExtractionExtractor, QualityAssessor, SynthesisGenerator
from src.converters.md_to_latex import convert_markdown_to_latex, wrap_in_document

router = APIRouter(prefix="/prisma", tags=["prisma"])

import logging

logger = logging.getLogger(__name__)


class UpdateProtocolRequest(BaseModel):
    title: Optional[str] = None
    registration_number: Optional[str] = None
    registration_date: Optional[str] = None
    review_stage: Optional[str] = None
    start_date: Optional[str] = None
    expected_end_date: Optional[str] = None
    actual_end_date: Optional[str] = None


class UpdateChecklistItemRequest(BaseModel):
    item_number: int
    status: str
    page_reference: Optional[str] = None
    notes: Optional[str] = None


def get_app_state():
    from src.api.main import app_state
    return app_state


def get_included_papers():
    app_state = get_app_state()
    return [
        p for p in app_state["papers"]
        if any(r.paper_id == p.id and r.decision.value == "include" for r in app_state["results"])
    ]


@router.get("/flow")
async def get_prisma_flow():
    """Get PRISMA flow diagram data."""
    app_state = get_app_state()
    generator = PrismaGenerator(app_state.get("prisma_config"))
    flow_data = generator.generate_flow_data(
        app_state["papers"],
        app_state["results"],
    )
    return flow_data.model_dump()


@router.get("/export")
async def export_prisma_flow(format: str = Query("json", regex="^(json|csv)$")):
    """Export PRISMA flow diagram."""
    app_state = get_app_state()
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


@router.post("/extract")
async def run_extraction():
    """Run extraction and quality assessment on included studies."""
    app_state = get_app_state()
    included_papers = get_included_papers()

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


@router.get("/report")
async def get_prisma_report(format: str = Query("markdown", regex="^(markdown|json|latex)$")):
    """Generate full PRISMA 2020 report."""
    app_state = get_app_state()
    included_papers = get_included_papers()
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

    if format == "latex":
        prisma_cfg = app_state.get("prisma_config")
        title = prisma_cfg.title if prisma_cfg and hasattr(prisma_cfg, "title") else "PRISMA 2020 Report"
        latex_content = convert_markdown_to_latex(markdown_report)
        latex_content = wrap_in_document(latex_content, title)
        output_path = output_dir / f"report_{timestamp}.tex"
        with open(output_path, "w") as f:
            f.write(latex_content)
        return {
            "status": "generated",
            "format": "latex",
            "report": latex_content,
            "path": str(output_path),
        }

    output_path = output_dir / f"report_{timestamp}.md"
    with open(output_path, "w") as f:
        f.write(markdown_report)

    return {
        "status": "generated",
        "format": "markdown",
        "report": markdown_report,
        "path": str(output_path),
    }


@router.get("/extraction")
async def get_extraction_data():
    """Get extraction data for included studies."""
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    if not extraction_data:
        return {"status": "not_extracted", "message": "Run /prisma/extract first"}

    return {
        "total": len(extraction_data),
        "data": [e.model_dump() for e in extraction_data],
    }


@router.get("/quality")
async def get_quality_data():
    """Get quality assessment data."""
    app_state = get_app_state()
    quality_data = app_state.get("quality_data", [])
    if not quality_data:
        return {"status": "not_assessed", "message": "Run /prisma/extract first"}

    return {
        "total": len(quality_data),
        "data": [q.model_dump() for q in quality_data],
    }


@router.get("/quality/{paper_id}")
async def get_quality_for_paper(paper_id: str):
    """Get quality assessment for a specific paper."""
    app_state = get_app_state()
    quality_data = app_state.get("quality_data", [])
    
    for q in quality_data:
        if q.paper_id == paper_id:
            return q.model_dump()
    
    raise HTTPException(status_code=404, detail=f"No quality data for paper {paper_id}")


@router.put("/quality/{paper_id}")
async def update_quality(paper_id: str, quality_data: dict):
    """Update quality assessment for a paper."""
    app_state = get_app_state()
    quality_list = app_state.get("quality_data", [])
    
    for i, q in enumerate(quality_list):
        if q.paper_id == paper_id:
            for key, value in quality_data.items():
                if hasattr(q, key):
                    setattr(q, key, value)
            quality_list[i] = q
            app_state["quality_data"] = quality_list
            return {"status": "updated", "paper_id": paper_id, "quality": q.model_dump()}
    
    raise HTTPException(status_code=404, detail=f"No quality data for paper {paper_id}")


@router.post("/quality/assess")
async def assess_quality():
    """Run quality assessment on included papers."""
    app_state = get_app_state()
    included_papers = get_included_papers()
    
    if not included_papers:
        return {"status": "no_included", "message": "No included papers found."}
    
    assessor = QualityAssessor()
    quality_data = assessor.assess(included_papers)
    app_state["quality_data"] = quality_data
    
    return {
        "status": "assessed",
        "papers_assessed": len(quality_data),
        "mean_score": sum(q.overall_score for q in quality_data) / len(quality_data) if quality_data else 0,
    }


# PRISMA 2020 Checklist Endpoints

@router.get("/checklist", response_model=PrismaChecklist)
async def get_prisma_checklist():
    """Get PRISMA 2020 checklist with all 27 items."""
    app_state = get_app_state()
    checklist = app_state.get("prisma_checklist")
    
    if not checklist:
        checklist = PrismaChecklist.create_default()
        app_state["prisma_checklist"] = checklist
    
    return checklist


@router.put("/protocol")
async def update_protocol(request: UpdateProtocolRequest):
    """Update the review protocol information."""
    app_state = get_app_state()
    checklist = app_state.get("prisma_checklist")
    
    if not checklist:
        checklist = PrismaChecklist.create_default()
        app_state["prisma_checklist"] = checklist
    
    protocol = checklist.protocol
    
    if request.title is not None:
        protocol.title = request.title
    if request.registration_number is not None:
        protocol.registration_number = request.registration_number
    if request.registration_date is not None:
        protocol.registration_date = request.registration_date
    if request.review_stage is not None:
        protocol.review_stage = request.review_stage
    if request.start_date is not None:
        protocol.start_date = request.start_date
    if request.expected_end_date is not None:
        protocol.expected_end_date = request.expected_end_date
    if request.actual_end_date is not None:
        protocol.actual_end_date = request.actual_end_date
    
    return {
        "status": "updated",
        "protocol": protocol.model_dump(),
    }


@router.put("/checklist/item")
async def update_checklist_item(request: UpdateChecklistItemRequest):
    """Update a specific checklist item."""
    app_state = get_app_state()
    checklist = app_state.get("prisma_checklist")
    
    if not checklist:
        checklist = PrismaChecklist.create_default()
        app_state["prisma_checklist"] = checklist
    
    for item in checklist.items:
        if item.item_number == request.item_number:
            item.status = request.status
            item.page_reference = request.page_reference
            item.notes = request.notes
            break
    
    checklist.completeness_score = _calculate_completeness(checklist.items)
    
    return {
        "status": "updated",
        "item_number": request.item_number,
        "completeness_score": checklist.completeness_score,
    }


@router.get("/checklist/report")
async def get_checklist_report():
    """Generate a PRISMA 2020 checklist report."""
    app_state = get_app_state()
    checklist = app_state.get("prisma_checklist")
    
    if not checklist:
        checklist = PrismaChecklist.create_default()
        app_state["prisma_checklist"] = checklist
    
    sections = {}
    for item in checklist.items:
        if item.section not in sections:
            sections[item.section] = {
                "section": item.section,
                "items": [],
                "completed": 0,
                "total": 0,
            }
        sections[item.section]["items"].append(item.model_dump())
        sections[item.section]["total"] += 1
        if item.status == "reported":
            sections[item.section]["completed"] += 1
    
    return {
        "protocol": checklist.protocol.model_dump(),
        "sections": list(sections.values()),
        "completeness_score": checklist.completeness_score,
        "total_items": len(checklist.items),
        "completed_items": sum(1 for item in checklist.items if item.status == "reported"),
    }


def _calculate_completeness(items: list[PrismaChecklistItem]) -> float:
    """Calculate checklist completeness as percentage."""
    if not items:
        return 0.0
    completed = sum(1 for item in items if item.status == "reported")
    return (completed / len(items)) * 100


@router.post("/report/full")
async def generate_full_prisma_report(
    format: str = Query("markdown", regex="^(markdown|latex)$"),
):
    """Generate complete PRISMA 2020 report including checklist."""
    app_state = get_app_state()
    checklist = app_state.get("prisma_checklist")
    
    if not checklist:
        checklist = PrismaChecklist.create_default()
        app_state["prisma_checklist"] = checklist
    
    included_papers = get_included_papers()
    extraction_data = app_state.get("extraction_data", [])
    quality_data = app_state.get("quality_data", [])
    
    generator = PrismaGenerator(app_state.get("prisma_config"))
    flow_data = generator.generate_flow_data(app_state["papers"], app_state["results"])
    
    report_sections = []
    
    report_sections.append("# Systematic Literature Review Report\n")
    report_sections.append(f"**Review Title:** {checklist.protocol.title}\n")
    report_sections.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n")
    report_sections.append(f"**Protocol Registration:** {checklist.protocol.registration_number or 'Not registered'}\n")
    report_sections.append("---\n")
    
    report_sections.append("## 1. PRISMA Flow Diagram\n")
    report_sections.append(f"**Records identified:** {flow_data.identification_identified}\n")
    report_sections.append(f"**After duplicates removed:** {flow_data.identification_after_duplicates}\n")
    report_sections.append(f"**Records screened:** {flow_data.total_screened}\n")
    report_sections.append(f"**Full-text assessed:** {flow_data.screening_sought_retrieval}\n")
    report_sections.append(f"**Studies included:** {flow_data.included_studies}\n")
    report_sections.append("\n### 1.2 Exclusion Reasons\n")
    if flow_data.screening_abstract_excluded_reasons:
        report_sections.append("| Reason | Count |\n|--------|-------|\n")
        for reason, count in flow_data.screening_abstract_excluded_reasons.items():
            report_sections.append(f"| {reason} | {count} |\n")
    
    report_sections.append("\n## 2. PRISMA 2020 Checklist\n")
    report_sections.append(f"**Completeness Score:** {checklist.completeness_score:.1f}%\n")
    
    for section_name, section_data in _group_by_section(checklist.items).items():
        report_sections.append(f"\n### {section_name}\n")
        for item in section_data:
            status_icon = "✓" if item.status == "reported" else "○"
            report_sections.append(f"{status_icon} **{item.item_number}.** {item.description}")
            if item.page_reference:
                report_sections.append(f" *(p. {item.page_reference})*")
            report_sections.append("\n")
    
    report_sections.append("\n## 3. Study Characteristics\n")
    if included_papers:
        report_sections.append(f"**Number of included studies:** {len(included_papers)}\n")
    
    report_sections.append("\n## 4. Risk of Bias Assessment\n")
    report_sections.append("Methods for assessing ML screening accuracy and human review quality.\n")
    
    report_sections.append("\n## 5. Synthesis of Results\n")
    report_sections.append("Narrative synthesis of included studies...\n")
    
    report = "".join(report_sections)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/prisma")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if format == "latex":
        title = checklist.protocol.title
        latex_content = convert_markdown_to_latex(report)
        latex_content = wrap_in_document(latex_content, title)
        output_path = output_dir / f"prisma_full_report_{timestamp}.tex"
        with open(output_path, "w") as f:
            f.write(latex_content)
        return {
            "status": "generated",
            "format": "latex",
            "path": str(output_path),
        }
    
    output_path = output_dir / f"prisma_full_report_{timestamp}.md"
    with open(output_path, "w") as f:
        f.write(report)
    
    return {
        "status": "generated",
        "format": "markdown",
        "report": report,
        "path": str(output_path),
    }


def _group_by_section(items: list[PrismaChecklistItem]) -> dict:
    """Group checklist items by section."""
    sections = {}
    for item in items:
        if item.section not in sections:
            sections[item.section] = []
        sections[item.section].append(item)
    return sections


# Synthesis Endpoints

@router.get("/synthesis")
async def get_synthesis():
    """Get synthesis statistics from extracted data."""
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    quality_data = app_state.get("quality_data", [])
    
    if not extraction_data:
        return {
            "status": "no_data",
            "message": "No extraction data available. Run /prisma/extract first.",
        }
    
    synthesizer = SynthesisGenerator()
    synthesis = synthesizer.synthesize(extraction_data, quality_data)
    
    return synthesis


@router.get("/synthesis/platforms")
async def get_platform_analysis():
    """Get detailed blockchain platform analysis."""
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    
    if not extraction_data:
        return {"status": "no_data", "message": "No extraction data available."}
    
    synthesizer = SynthesisGenerator()
    platforms = synthesizer._analyze_platforms(extraction_data)
    
    return {
        "platform_distribution": platforms,
        "total_studies": len(extraction_data),
    }


@router.get("/synthesis/distributions")
async def get_distributions():
    """Get distribution statistics for key variables."""
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    
    if not extraction_data:
        return {"status": "no_data", "message": "No extraction data available."}
    
    synthesizer = SynthesisGenerator()
    
    distributions = {
        "blockchain_platforms": synthesizer._analyze_platforms(extraction_data),
        "approach_types": synthesizer._analyze_approaches(extraction_data),
        "evaluation_methods": synthesizer._analyze_evaluations(extraction_data),
        "blockchain_analysis": synthesizer._analyze_blockchains(extraction_data),
    }
    
    return distributions


@router.get("/synthesis/gaps")
async def get_research_gaps():
    """Identify research gaps from extracted data."""
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    
    if not extraction_data:
        return {"status": "no_data", "message": "No extraction data available."}
    
    synthesizer = SynthesisGenerator()
    gaps = synthesizer._identify_gaps(extraction_data)
    trends = synthesizer._identify_trends(extraction_data)
    
    return {
        "research_gaps": gaps,
        "identified_trends": trends,
        "total_studies": len(extraction_data),
    }


@router.post("/synthesis/report")
async def generate_synthesis_report(
    format: str = Query("markdown", regex="^(markdown|latex|json)$"),
):
    """Generate a synthesis report."""
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    quality_data = app_state.get("quality_data", [])
    papers = app_state.get("papers", [])
    
    if not extraction_data:
        return {
            "status": "no_data",
            "message": "No extraction data available. Run /prisma/extract first.",
        }
    
    synthesizer = SynthesisGenerator()
    synthesis = synthesizer.synthesize(extraction_data, quality_data)
    
    paper_map = {p.id: p for p in papers}
    
    report_sections = []
    report_sections.append("# Synthesis Report\n")
    report_sections.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n")
    report_sections.append("---\n")
    
    report_sections.append("## 1. Overview\n")
    overview = synthesis["overview"]
    report_sections.append(f"- **Total Studies:** {overview['total_studies']}\n")
    report_sections.append(f"- **Studies with Blockchain:** {overview['with_blockchain']}\n")
    report_sections.append(f"- **Studies with Provenance Model:** {overview['with_provenance']}\n")
    report_sections.append(f"- **Studies with maDMP Standard:** {overview['with_madmp']}\n")
    
    report_sections.append("\n## 2. Blockchain Platforms\n")
    platforms = synthesis["platform_distribution"]
    if platforms.get("platforms"):
        report_sections.append("| Platform | Count |")
        report_sections.append("|----------|-------|")
        for platform, count in platforms["platforms"].items():
            report_sections.append(f"| {platform} | {count} |")
    
    report_sections.append("\n## 3. Research Approaches\n")
    approaches = synthesis["approach_types"]
    if approaches:
        report_sections.append("| Approach | Count |")
        report_sections.append("|---------|-------|")
        for approach, count in approaches.items():
            report_sections.append(f"| {approach} | {count} |")
    
    report_sections.append("\n## 4. Evaluation Methods\n")
    evals = synthesis["evaluation_analysis"]
    if evals.get("methods"):
        report_sections.append("| Method | Count |")
        report_sections.append("|--------|-------|")
        for method, count in evals["methods"].items():
            report_sections.append(f"| {method} | {count} |")
    
    report_sections.append("\n## 5. Quality Assessment\n")
    quality = synthesis["quality_overview"]
    if "rating_distribution" in quality:
        report_sections.append("| Rating | Count |")
        report_sections.append("|--------|-------|")
        for rating, count in quality["rating_distribution"].items():
            report_sections.append(f"| {rating} | {count} |")
        report_sections.append(f"\n**Mean Score:** {quality.get('mean_score', 0):.2f}\n")
    
    report_sections.append("\n## 6. Research Gaps\n")
    gaps = synthesis["research_gaps"]
    if gaps:
        for gap in gaps:
            report_sections.append(f"- {gap}\n")
    else:
        report_sections.append("No significant gaps identified.\n")
    
    report_sections.append("\n## 7. Identified Trends\n")
    trends = synthesis["trends"]
    if trends:
        for trend in trends:
            report_sections.append(f"- {trend}\n")
    else:
        report_sections.append("No specific trends identified.\n")
    
    report_sections.append("\n---\n")
    report_sections.append(f"*Report generated: {datetime.now().strftime('%B %d, %Y')}*\n")
    
    report = "".join(report_sections)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/prisma")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if format == "latex":
        latex_content = convert_markdown_to_latex(report)
        latex_content = wrap_in_document(latex_content, "Synthesis Report")
        output_path = output_dir / f"synthesis_report_{timestamp}.tex"
        with open(output_path, "w") as f:
            f.write(latex_content)
        return {
            "status": "generated",
            "format": "latex",
            "path": str(output_path),
        }
    
    if format == "json":
        return {
            "status": "generated",
            "format": "json",
            "synthesis": synthesis,
        }
    
    output_path = output_dir / f"synthesis_report_{timestamp}.md"
    with open(output_path, "w") as f:
        f.write(report)
    
    return {
        "status": "generated",
        "format": "markdown",
        "report": report,
        "path": str(output_path),
    }


@router.get("/extraction/template")
async def get_extraction_template():
    """Get the maDMP/blockchain extraction template."""
    from src.models.schemas import ExtractionTemplate
    template = ExtractionTemplate.create_madmp_template()
    return template.model_dump()


@router.put("/extraction/{paper_id}")
async def update_extraction(
    paper_id: str,
    extraction_data: dict,
):
    """Update extraction data for a specific paper."""
    app_state = get_app_state()
    extraction = app_state.get("extraction_data", [])
    
    for i, e in enumerate(extraction):
        if e.paper_id == paper_id:
            for key, value in extraction_data.items():
                if hasattr(e, key):
                    setattr(e, key, value)
            extraction[i] = e
            app_state["extraction_data"] = extraction
            return {
                "status": "updated",
                "paper_id": paper_id,
                "extraction": e.model_dump(),
            }
    
    return {
        "status": "not_found",
        "message": f"No extraction data found for paper {paper_id}",
    }


@router.get("/extraction/export")
async def export_extraction_csv():
    """Export extraction data as CSV."""
    import csv
    from io import StringIO
    
    app_state = get_app_state()
    extraction_data = app_state.get("extraction_data", [])
    papers = app_state.get("papers", [])
    
    if not extraction_data:
        raise HTTPException(status_code=400, detail="No extraction data. Run /prisma/extract first.")
    
    paper_map = {p.id: p for p in papers}
    
    fieldnames = [
        "study_id", "paper_id", "citation",
        "research_focus", "approach_type", "system_description",
        "blockchain_platform", "blockchain_type", "consensus_mechanism", "smart_contract_language",
        "madmp_standard", "metadata_schema", "linked_data_support", "fair_principles_compliance",
        "provenance_model", "provenance_approach", "verification_mechanism",
        "storage_integration", "data_partitioning", "data_encryption",
        "permission_model", "access_control_mechanism",
        "evaluation_method", "performance_metrics", "scalability_assessment", "benchmarks_reported",
        "key_findings", "contributions", "novel_aspects", "limitations", "future_work",
        "methodological_quality", "extraction_date",
    ]
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    
    for e in extraction_data:
        row = e.model_dump()
        paper = paper_map.get(e.paper_id)
        if paper:
            row["citation"] = f"{', '.join(paper.authors[:3]) if paper.authors else 'Unknown'}{f' ({paper.year})' if paper.year else ''}"
        output.write(row)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/prisma")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"extraction_data_{timestamp}.csv"
    
    output.seek(0)
    output_path.write_text(output.getvalue(), encoding="utf-8")
    
    return {
        "status": "exported",
        "format": "csv",
        "path": str(output_path),
        "rows": len(extraction_data),
    }


@router.get("/quality/export")
async def export_quality_csv():
    """Export quality assessment data as CSV."""
    import csv
    from io import StringIO
    
    app_state = get_app_state()
    quality_data = app_state.get("quality_data", [])
    papers = app_state.get("papers", [])
    
    if not quality_data:
        raise HTTPException(status_code=400, detail="No quality data. Run /prisma/extract first.")
    
    paper_map = {p.id: p for p in papers}
    
    fieldnames = [
        "paper_id", "citation", "rating", "overall_score",
        "screening_question", "qualitative_1", "qualitative_2", "quantitative_1", "quantitative_2", "mixed_1",
        "notes",
    ]
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    
    for q in quality_data:
        row = q.model_dump()
        paper = paper_map.get(q.paper_id)
        if paper:
            row["citation"] = f"{', '.join(paper.authors[:3]) if paper.authors else 'Unknown'}{f' ({paper.year})' if paper.year else ''}"
        output.write(row)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/prisma")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"quality_assessment_{timestamp}.csv"
    
    output.seek(0)
    output_path.write_text(output.getvalue(), encoding="utf-8")
    
    return {
        "status": "exported",
        "format": "csv",
        "path": str(output_path),
        "rows": len(quality_data),
    }
