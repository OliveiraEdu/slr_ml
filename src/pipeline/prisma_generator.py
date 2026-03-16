"""PRISMA 2020 flow diagram generator."""
import json
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
