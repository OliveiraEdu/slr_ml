"""Configuration loader for YAML-based settings."""
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from src.models.schemas import (
    ArxivConfig,
    ClassificationConfig,
    ModelConfig,
    PicocLabel,
    PicocLabels,
    PrismaConfig,
    RelevanceConfig,
    ScreeningStages,
    SourcesConfig,
    Thresholds,
)


class ConfigLoader:
    """Loads and manages YAML configuration files."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._sources: Optional[SourcesConfig] = None
        self._classification: Optional[ClassificationConfig] = None
        self._prisma: Optional[PrismaConfig] = None

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        """Load a YAML file from the config directory."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        with open(filepath, "r") as f:
            return yaml.safe_load(f)

    def load_all(self) -> tuple[SourcesConfig, ClassificationConfig, PrismaConfig]:
        """Load all configuration files."""
        self._sources = self.load_sources()
        self._classification = self.load_classification()
        self._prisma = self.load_prisma()
        return self._sources, self._classification, self._prisma

    def load_sources(self) -> SourcesConfig:
        """Load sources configuration."""
        data = self._load_yaml("sources.yaml")
        return SourcesConfig(**data["sources"])

    def load_classification(self) -> ClassificationConfig:
        """Load classification configuration."""
        data = self._load_yaml("classification.yaml")
        cls_data = data.get("classification", {})
        
        model = ModelConfig(**cls_data.get("model", {}))
        
        labels_data = cls_data.get("labels", {})
        labels = None
        if labels_data:
            labels = PicocLabels(
                population=PicocLabel(**labels_data.get("population", {})),
                intervention=PicocLabel(**labels_data.get("intervention", {})),
                comparison=PicocLabel(**labels_data.get("comparison", {})),
                outcomes=PicocLabel(**labels_data.get("outcomes", {})),
                context=PicocLabel(**labels_data.get("context", {})),
            )
        
        relevance = RelevanceConfig(**cls_data.get("relevance", {}))
        thresholds = Thresholds(**cls_data.get("thresholds", {}))
        stages = ScreeningStages(**cls_data.get("stages", {}))
        
        return ClassificationConfig(
            model=model,
            labels=labels,
            relevance=relevance,
            thresholds=thresholds,
            stages=stages,
        )

    def load_prisma(self) -> PrismaConfig:
        """Load PRISMA configuration."""
        data = self._load_yaml("prisma.yaml")
        prisma_data = data.get("prisma", {})
        
        return PrismaConfig(
            review_type=prisma_data.get("review_type", "original"),
            title_abstract_exclusion_reasons=prisma_data.get(
                "title_abstract_exclusion_reasons", []
            ),
            full_text_exclusion_reasons=prisma_data.get(
                "full_text_exclusion_reasons", []
            ),
            inclusion_criteria=prisma_data.get("inclusion_criteria", []),
            include_flow_diagram=prisma_data.get("include_flow_diagram", True),
            include_table_studies=prisma_data.get("include_table_studies", True),
            include_summary_statistics=prisma_data.get(
                "include_summary_statistics", True
            ),
            flow_diagram=prisma_data.get("output", {}).get("flow_diagram", "json"),
            statistics=prisma_data.get("output", {}).get("statistics", "json"),
            export_path=prisma_data.get("output", {}).get("export_path", "outputs/prisma"),
            primary_reviewer=prisma_data.get("reviewers", {}).get("primary", ""),
            secondary_reviewer=prisma_data.get("reviewers", {}).get("secondary", ""),
            conflict_resolution=prisma_data.get("reviewers", {}).get(
                "conflict_resolution", ""
            ),
        )

    @property
    def sources(self) -> SourcesConfig:
        """Get loaded sources config."""
        if self._sources is None:
            self._sources = self.load_sources()
        return self._sources

    @property
    def classification(self) -> ClassificationConfig:
        """Get loaded classification config."""
        if self._classification is None:
            self._classification = self.load_classification()
        return self._classification

    @property
    def prisma(self) -> PrismaConfig:
        """Get loaded PRISMA config."""
        if self._prisma is None:
            self._prisma = self.load_prisma()
        return self._prisma

    def get_enabled_sources(self) -> list[str]:
        """Get list of enabled source names."""
        enabled = []
        for name in ["wos", "ieee", "acm", "scopus", "arxiv"]:
            source = getattr(self.sources, name)
            if source.enabled:
                enabled.append(name)
        return enabled

    def get_arxiv_queries(self) -> list[dict]:
        """Get arXiv queries configuration."""
        arxiv = self.sources.arxiv
        if not arxiv.enabled:
            return []
        
        queries = []
        for q in arxiv.queries:
            queries.append({
                "query": q.query,
                "max_results": q.max_results,
            })
        return queries


_default_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dir: str = "config") -> ConfigLoader:
    """Get or create the default configuration loader."""
    global _default_loader
    if _default_loader is None:
        _default_loader = ConfigLoader(config_dir)
    return _default_loader


def load_config(config_dir: str = "config") -> tuple[SourcesConfig, ClassificationConfig, PrismaConfig]:
    """Convenience function to load all configs."""
    loader = get_config_loader(config_dir)
    return loader.load_all()
