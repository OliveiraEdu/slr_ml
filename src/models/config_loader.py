"""Configuration loader for YAML-based settings."""
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from src.models.schemas import (
    ArxivConfig,
    ClassificationConfig,
    ClassificationLabel,
    ExclusionCriteria,
    InclusionCriteria,
    KeywordsConfig,
    ModelConfig,
    PrismaConfig,
    RelevanceConfig,
    ScreeningStages,
    SourcesConfig,
    SubQuestions,
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
        """Load classification configuration with flexible schema."""
        data = self._load_yaml("classification.yaml")
        cls_data = data.get("classification", {})
        
        # Model config
        model = ModelConfig(**cls_data.get("model", {}))
        
        # Research question
        research_question = cls_data.get("research_question")
        
        # Relevance config
        relevance = RelevanceConfig(**cls_data.get("relevance", {}))
        
        # Thresholds
        thresholds = Thresholds(**cls_data.get("thresholds", {}))
        
        # Stages
        stages = ScreeningStages(**cls_data.get("stages", {}))
        
        # Sub-questions (optional)
        sub_questions = None
        sq_data = cls_data.get("sub_questions", {})
        if sq_data:
            sub_questions = SubQuestions(
                sq1_blockchain_platforms=ClassificationLabel(**sq_data.get("sq1_blockchain_platforms", {})),
                sq2_provenance_model=ClassificationLabel(**sq_data.get("sq2_provenance_model", {})),
                sq3_architecture=ClassificationLabel(**sq_data.get("sq3_architecture", {})),
                sq4_permissioned_vs_permissionless=ClassificationLabel(**sq_data.get("sq4_permissioned_vs_permissionless", {})),
                sq5_evaluation=ClassificationLabel(**sq_data.get("sq5_evaluation", {})),
            )
        
        # Inclusion criteria (optional)
        inclusion_criteria = None
        inc_data = cls_data.get("inclusion_criteria", {})
        if inc_data:
            inclusion_criteria = InclusionCriteria(
                i1_language=ClassificationLabel(**inc_data.get("i1_language", {})),
                i2_publication_type=ClassificationLabel(**inc_data.get("i2_publication_type", {})),
                i3_date_range=ClassificationLabel(**inc_data.get("i3_date_range", {})),
                i4_technical_implementation=ClassificationLabel(**inc_data.get("i4_technical_implementation", {})),
                i5_domain_relevance=ClassificationLabel(**inc_data.get("i5_domain_relevance", {})),
            )
        
        # Exclusion criteria (optional)
        exclusion_criteria = None
        exc_data = cls_data.get("exclusion_criteria", {})
        if exc_data:
            exclusion_criteria = ExclusionCriteria(
                e1_opinion_pieces=ClassificationLabel(**exc_data.get("e1_opinion_pieces", {})),
                e2_non_research=ClassificationLabel(**exc_data.get("e2_non_research", {})),
                e3_no_implementation=ClassificationLabel(**exc_data.get("e3_no_implementation", {})),
                e4_duplicates=ClassificationLabel(**exc_data.get("e4_duplicates", {})),
                e5_no_fulltext=ClassificationLabel(**exc_data.get("e5_no_fulltext", {})),
                e6_no_blockchain=ClassificationLabel(**exc_data.get("e6_no_blockchain", {})),
                e7_no_scientific_data=ClassificationLabel(**exc_data.get("e7_no_scientific_data", {})),
            )
        
        # Keywords (optional)
        keywords = None
        kw_data = cls_data.get("keywords", {})
        if kw_data:
            keywords = KeywordsConfig(**kw_data)
        
        return ClassificationConfig(
            model=model,
            research_question=research_question,
            relevance=relevance,
            sub_questions=sub_questions,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            keywords=keywords,
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
