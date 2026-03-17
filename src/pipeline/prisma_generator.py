"""PRISMA 2020 flow diagram generator."""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.schemas import Paper, PrismaConfig, PrismaFlowData, ScreeningResult


class PrismaGenerator:
    """Generates PRISMA 2020 flow diagram data and reports."""

    def __init__(self, config: Optional[PrismaConfig] = None):
        self.config = config or self._default_config()

    def _default_config(self) -> PrismaConfig:
        """Get default PRISMA configuration."""
        return PrismaConfig(
            review_type="original",
            title_abstract_exclusion_reasons=["Not relevant"],
            full_text_exclusion_reasons=["Full text not available"],
            inclusion_criteria=["Relevant to research question"],
        )

    def generate_flow_data(
        self,
        papers: list[Paper],
        results: list[ScreeningResult],
    ) -> PrismaFlowData:
        """Generate PRISMA flow diagram data from screening results."""
        flow = PrismaFlowData()

        flow.identification_identified = len(papers)

        doi_groups = {}
        for paper in papers:
            doi = paper.doi or paper.id
            doi_groups[doi] = doi_groups.get(doi, 0) + 1

        duplicates = sum(count - 1 for count in doi_groups.values() if count > 1)
        flow.identification_removed_duplicates = duplicates
        flow.identification_after_duplicates = len(papers) - duplicates

        abstract_excluded = sum(
            1 for r in results
            if r.stage == "title_abstract" and r.decision == "exclude"
        )
        flow.screening_abstract_excluded = abstract_excluded

        excluded_reasons = {}
        for r in results:
            if r.stage == "title_abstract" and r.decision == "exclude" and r.reason:
                reason = r.reason
                excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
        flow.screening_abstract_excluded_reasons = excluded_reasons

        flow.screening_sought_retrieval = sum(
            1 for r in results
            if r.stage == "title_abstract" and r.decision == "include"
        )

        fulltext_excluded = sum(
            1 for r in results
            if r.stage == "full_text" and r.decision == "exclude"
        )
        flow.eligibility_fulltext_excluded = fulltext_excluded

        ft_excluded_reasons = {}
        for r in results:
            if r.stage == "full_text" and r.decision == "exclude" and r.reason:
                reason = r.reason
                ft_excluded_reasons[reason] = ft_excluded_reasons.get(reason, 0) + 1
        flow.eligibility_fulltext_excluded_reasons = ft_excluded_reasons

        flow.included_studies = sum(
            1 for r in results
            if r.decision == "include"
        )

        flow.total_screened = len(results)
        flow.total_excluded = sum(
            1 for r in results if r.decision == "exclude"
        )

        return flow

    def export_flow_diagram(
        self,
        flow_data: PrismaFlowData,
        output_path: str = "outputs/prisma/flow_diagram.json",
        format: str = "json",
    ) -> str:
        """Export flow diagram data to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_file, "w") as f:
                json.dump(flow_data.model_dump(), f, indent=2)
        elif format == "csv":
            self._export_csv(flow_data, output_file)

        return str(output_file)

    def _export_csv(self, flow_data: PrismaFlowData, output_file: Path):
        """Export flow diagram data to CSV."""
        import csv

        rows = [
            ["Stage", "Count"],
            ["Records identified", flow_data.identification_identified],
            ["Records removed duplicates", flow_data.identification_removed_duplicates],
            ["Records after duplicates", flow_data.identification_after_duplicates],
            ["Records screened abstract", flow_data.identification_after_duplicates],
            ["Records excluded abstract", flow_data.screening_abstract_excluded],
            ["Records sought retrieval", flow_data.screening_sought_retrieval],
            ["Records not retrieved", flow_data.screening_not_retrieved],
            ["Reports assessed full-text", flow_data.screening_sought_retrieval],
            ["Reports excluded full-text", flow_data.eligibility_fulltext_excluded],
            ["Studies included", flow_data.included_studies],
        ]

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    def generate_summary(
        self,
        flow_data: PrismaFlowData,
    ) -> dict:
        """Generate summary statistics."""
        return {
            "total_identified": flow_data.identification_identified,
            "total_screened": flow_data.total_screened,
            "total_included": flow_data.included_studies,
            "total_excluded": flow_data.total_excluded,
            "inclusion_rate": (
                flow_data.included_studies / flow_data.total_screened * 100
                if flow_data.total_screened > 0 else 0
            ),
            "generated_at": datetime.now().isoformat(),
            "review_type": self.config.review_type,
        }

    def generate_report(
        self,
        papers: list[Paper],
        results: list[ScreeningResult],
        output_dir: str = "outputs/prisma",
    ) -> dict:
        """Generate complete PRISMA report."""
        flow_data = self.generate_flow_data(papers, results)

        output_path = Path(output_dir) / f"flow_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.export_flow_diagram(flow_data, str(output_path) + ".json")

        summary = self.generate_summary(flow_data)

        return {
            "flow_diagram": flow_data.model_dump(),
            "summary": summary,
        }

    def generate_markdown_report(
        self,
        papers: list[Paper],
        results: list[ScreeningResult],
        included_papers: list[Paper],
        extraction_data: list,
        quality_data: list,
    ) -> str:
        """Generate full PRISMA 2020 markdown report."""
        flow_data = self.generate_flow_data(papers, results)
        now = datetime.now().strftime("%B %d, %Y")

        md = []
        md.append("# Systematic Review Findings Report\n")
        md.append(f"**Date:** {now}")
        md.append("**Review Protocol:** PRISMA 2020 Guidelines\n")
        md.append("---\n")

        md.append("## Executive Summary\n")
        total_studies = flow_data.included_studies
        md.append(f"This systematic review identified **{total_studies} studies** meeting inclusion criteria.")
        md.append(f"The review followed PRISMA 2020 guidelines.\n")
        md.append("---\n")

        md.extend(self._generate_flow_section(flow_data))
        md.append("---\n")

        md.extend(self._generate_methods_section())
        md.append("---\n")

        md.extend(self._generate_study_characteristics_section(included_papers, extraction_data))
        md.append("---\n")

        md.extend(self._generate_quality_section(quality_data))
        md.append("---\n")

        md.extend(self._generate_included_studies_table(included_papers, extraction_data))
        md.append("---\n")

        md.extend(self._generate_limitations_section())
        md.append("---\n")

        md.append("---\n")
        md.append(f"*Report generated: {now}*")

        return "\n".join(md)

    def _generate_flow_section(self, flow_data: PrismaFlowData) -> list[str]:
        md = []
        md.append("## 1. PRISMA Flow Diagram\n")
        md.append("### 1.1 Flow Statistics\n")
        md.append("| Stage | Count | Percentage |")
        md.append("|-------|-------|------------|")

        total = flow_data.identification_identified or 1
        md.append(f"| Records identified | {flow_data.identification_identified} | 100% |")

        after_dupes = flow_data.identification_after_duplicates or 1
        md.append(f"| After duplicates removed | {flow_data.identification_after_duplicates} | {flow_data.identification_after_duplicates/total*100:.1f}% |")

        md.append(f"| Screened | {flow_data.identification_after_duplicates} | 100% |")

        abs_excluded = flow_data.screening_abstract_excluded
        md.append(f"| Excluded at title/abstract | {abs_excluded} | {abs_excluded/after_dupes*100:.1f}% |")

        sought = flow_data.screening_sought_retrieval
        md.append(f"| Assessed for full-text | {sought} | {sought/after_dupes*100:.1f}% |")

        ft_excluded = flow_data.eligibility_fulltext_excluded
        md.append(f"| Excluded at full-text | {ft_excluded} | {ft_excluded/sought*100:.1f}% |" if sought > 0 else "| Excluded at full-text | 0 | 0% |")

        md.append(f"| **Studies included** | **{flow_data.included_studies}** | **{flow_data.included_studies/after_dupes*100:.1f}%** |\n")

        md.append("### 1.2 Mermaid Flowchart\n")
        md.append("```mermaid")
        md.append("flowchart TD")
        md.append(f"    A[Records Identified<br/>n={flow_data.identification_identified}] --> B[Duplicate Records Removed<br/>n={flow_data.identification_removed_duplicates}]")
        md.append(f"    B --> C[Records Screened<br/>n={flow_data.identification_after_duplicates}]")
        md.append(f"    C --> D[Excluded by Title/Abstract<br/>n={abs_excluded}]")
        md.append(f"    D --> E[Records Eligible<br/>n={sought}]")
        md.append(f"    E --> F[Full-Text Assessed<br/>n={sought}]")
        md.append(f"    F --> G[Excluded Full-Text<br/>n={ft_excluded}]")
        md.append(f"    G --> H[Studies Included<br/>n={flow_data.included_studies}]")
        md.append("    style A fill:#e1f5fe")
        md.append("    style C fill:#fff3e0")
        md.append("    style F fill:#fff3e0")
        md.append("    style H fill:#e8f5e9")
        md.append("```\n")

        md.append("### 1.3 Exclusion Reasons\n")
        if flow_data.screening_abstract_excluded_reasons:
            md.append("| Reason | Count |")
            md.append("|--------|-------|")
            for reason, count in flow_data.screening_abstract_excluded_reasons.items():
                md.append(f"| {reason} | {count} |")

        return md

    def _generate_methods_section(self) -> list[str]:
        md = []
        md.append("## 2. Methods\n")
        md.append("### 2.1 Search Strategy\n")
        md.append("This systematic review searched the following databases: IEEE Xplore, Scopus, Web of Science, ACM Digital Library.")
        md.append("Search strings were developed following PRISMA 2020 guidelines.\n")

        md.append("### 2.2 Eligibility Criteria\n")
        md.append("| Criterion | Description |")
        md.append("|-----------|-------------|")
        md.append("| Language | English |")
        md.append("| Publication type | Journal articles, conference papers, preprints |")
        md.append("| Topic | Relevant to research question |\n")

        md.append("### 2.3 Screening Process\n")
        md.append("1. Records imported from databases and duplicates removed")
        md.append("2. Title and abstract screening using automated eligibility criteria")
        md.append("3. Full-text assessment for all included records")
        md.append("4. Data extraction for included studies")
        md.append("5. Quality assessment using Mixed Methods Appraisal Tool (MMAT)\n")

        return md

    def _generate_study_characteristics_section(self, papers: list[Paper], extraction_data: list) -> list[str]:
        md = []
        md.append("## 3. Study Characteristics\n")

        md.append("### 3.1 Publication Year Distribution\n")
        year_counts = Counter(p.year for p in papers if p.year)
        md.append("| Year | Count |")
        md.append("|------------|------|")
        for year in sorted(year_counts.keys()):
            md.append(f"| {year} | {year_counts[year]} |")

        md.append("\n### 3.2 Distribution by Source\n")
        source_counts = Counter(p.source.value for p in papers)
        md.append("| Source | Count |")
        md.append("|--------|-------|")
        for source, count in source_counts.most_common(10):
            md.append(f"| {source} | {count} |")

        if extraction_data:
            md.append("\n### 3.3 Research Focus Distribution\n")
            focus_counts = Counter(e.research_focus for e in extraction_data if e.research_focus)
            md.append("| Research Focus | Count |")
            md.append("|------------|------|")
            for focus, count in focus_counts.most_common():
                md.append(f"| {focus} | {count} |")

            md.append("\n### 3.4 Blockchain Platform Distribution\n")
            platform_counts = Counter(e.blockchain_platform for e in extraction_data if e.blockchain_platform)
            md.append("| Platform | Count |")
            md.append("|------------|------|")
            for platform, count in platform_counts.most_common():
                md.append(f"| {platform} | {count} |")

        return md

    def _generate_quality_section(self, quality_data: list) -> list[str]:
        md = []
        md.append("## 4. Quality Assessment\n")

        if not quality_data:
            md.append("No quality assessment data available.")
            return md

        rating_counts = Counter(q.rating.value if q.rating else "unknown" for q in quality_data)
        md.append("### 4.1 Quality Ratings Distribution\n")
        md.append("| Rating | Description | Count |")
        md.append("|--------|-------------|-------|")

        rating_desc = {
            "excellent": "Score 5 - clear methodology, rigorous evaluation",
            "good": "Score 4 - minor methodological gaps",
            "acceptable": "Score 3 - some concerns",
            "poor": "Score 2 - significant gaps",
            "very_poor": "Score 1 - cannot assess",
        }
        for rating in ["excellent", "good", "acceptable", "poor", "very_poor"]:
            count = rating_counts.get(rating, 0)
            desc = rating_desc.get(rating, "")
            md.append(f"| {rating.capitalize()} | {desc} | {count} |")

        scores = [q.overall_score for q in quality_data if q.overall_score is not None]
        if scores:
            mean_score = sum(scores) / len(scores)
            md.append(f"\n**Mean Quality Score:** {mean_score:.2f} / 1.0")

        md.append("\n### 4.2 MMAT Item Scores\n")
        md.append("| MMAT Item | Yes | Can't tell | Rate |")
        md.append("|-----------|-----|------------|------|")

        mmat_items = [
            ("clear_research_questions", "Clear Research Questions"),
            ("appropriate_methodology", "Appropriate Methodology"),
            ("rigorous_data_collection", "Rigorous Data Collection"),
            ("sound_analysis", "Sound Analysis"),
            ("well_supported_conclusions", "Well-supported Conclusions"),
        ]

        for field, label in mmat_items:
            yes_count = sum(1 for q in quality_data if q.mmat_score and q.mmat_score.model_dump().get(field) == "Yes")
            cant_tell = sum(1 for q in quality_data if q.mmat_score and q.mmat_score.model_dump().get(field) == "Can't tell")
            rate = (yes_count / len(quality_data) * 100) if quality_data else 0
            md.append(f"| {label} | {yes_count} | {cant_tell} | {rate:.1f}% |")

        return md

    def _generate_included_studies_table(self, papers: list[Paper], extraction_data: list) -> list[str]:
        md = []
        md.append("## 5. Included Studies\n")

        if not papers:
            md.append("No studies included.")
            return md

        md.append("| Study_ID | Title | Year | Authors | Source |")
        md.append("| --- | --- | --- | --- | --- |")

        for i, paper in enumerate(papers[:100]):
            study_id = f"REV{i+1:03d}"
            title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title
            authors = ", ".join(paper.authors[:3]) if paper.authors else "N/A"
            year = paper.year or "N/A"
            source = paper.source.value
            md.append(f"| {study_id} | {title} | {year} | {authors} | {source} |")

        if len(papers) > 100:
            md.append(f"\n*... and {len(papers) - 100} more studies*")

        return md

    def _generate_limitations_section(self) -> list[str]:
        md = []
        md.append("## 6. Limitations\n")
        md.append("- **Language restriction:** English publications only")
        md.append("- **Database coverage:** May miss specialized sources")
        md.append("- **Classification based on title/abstract:** May have errors")
        md.append("- **Automated extraction:** Key findings require manual verification\n")
        return md
