"""Pydantic data models for the SLR engine."""
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceName(str, Enum):
    WOS = "wos"
    IEEE = "ieee"
    ACM = "acm"
    SCOPUS = "scopus"
    ARXIV = "arxiv"


class FileFormat(str, Enum):
    BIBTEX = "bibtex"
    CSV = "csv"


class SourceConfig(BaseModel):
    enabled: bool = False
    file_path: Optional[str] = None
    format: FileFormat = FileFormat.BIBTEX


class ArxivQuery(BaseModel):
    query: str
    max_results: int = 50


class ArxivConfig(BaseModel):
    enabled: bool = False
    max_results: int = 100
    queries: list[ArxivQuery] = Field(default_factory=list)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    categories: list[str] = Field(default_factory=list)


class SourcesConfig(BaseModel):
    wos: SourceConfig = Field(default_factory=SourceConfig)
    ieee: SourceConfig = Field(default_factory=SourceConfig)
    acm: SourceConfig = Field(default_factory=SourceConfig)
    scopus: SourceConfig = Field(default_factory=SourceConfig)
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)


class ModelConfig(BaseModel):
    name: str = "allenai/scibert_scivocab_uncased"
    approach: str = "zero-shot"
    device: str = "auto"


class PicocLabel(BaseModel):
    enabled: bool = True
    prompt: str
    description: str


class PicocLabels(BaseModel):
    population: PicocLabel
    intervention: PicocLabel
    comparison: PicocLabel
    outcomes: PicocLabel
    context: PicocLabel


class RelevanceConfig(BaseModel):
    enabled: bool = True
    include_prompt: str = "This paper is relevant to the research question"
    exclude_prompt: str = "This paper is not relevant to the research question"
    threshold: float = 0.5


class Thresholds(BaseModel):
    include: float = 0.6
    exclude: float = 0.3
    uncertain: float = 0.3
    confidence: float = 0.15


class ScreeningStage(BaseModel):
    enabled: bool = True
    min_text_length: int = 50


class ScreeningStages(BaseModel):
    title_abstract: ScreeningStage = Field(default_factory=ScreeningStage)
    full_text: ScreeningStage = Field(default_factory=ScreeningStage)


class ClassificationConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    labels: Optional[PicocLabels] = None
    relevance: RelevanceConfig = Field(default_factory=RelevanceConfig)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    stages: ScreeningStages = Field(default_factory=ScreeningStages)


class PrismaConfig(BaseModel):
    review_type: str = "original"
    title_abstract_exclusion_reasons: list[str]
    full_text_exclusion_reasons: list[str]
    inclusion_criteria: list[str]
    include_flow_diagram: bool = True
    include_table_studies: bool = True
    include_summary_statistics: bool = True
    flow_diagram: str = "json"
    statistics: str = "json"
    export_path: str = "outputs/prisma"
    primary_reviewer: str = ""
    secondary_reviewer: str = ""
    conflict_resolution: str = ""


class Paper(BaseModel):
    id: str
    source: SourceName
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    journal: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    full_text: Optional[str] = None
    raw_metadata: dict = Field(default_factory=dict)


class ScreeningResult(BaseModel):
    paper_id: str
    stage: str
    relevance_score: float = 0.0
    relevance_label: str = "unclassified"
    picoc_scores: dict[str, float] = Field(default_factory=dict)
    decision: str = "pending"
    reason: Optional[str] = None
    confidence: float = 0.0


class PrismaFlowData(BaseModel):
    identification_identified: int = 0
    identification_removed_duplicates: int = 0
    identification_after_duplicates: int = 0
    screening_abstract_excluded: int = 0
    screening_abstract_excluded_reasons: dict[str, int] = Field(default_factory=dict)
    screening_sought_retrieval: int = 0
    screening_not_retrieved: int = 0
    eligibility_fulltext_excluded: int = 0
    eligibility_fulltext_excluded_reasons: dict[str, int] = Field(default_factory=dict)
    included_studies: int = 0
    total_screened: int = 0
    total_excluded: int = 0


class EngineState(BaseModel):
    papers: list[Paper] = Field(default_factory=list)
    screening_results: list[ScreeningResult] = Field(default_factory=list)
    prisma_flow: PrismaFlowData = Field(default_factory=PrismaFlowData)
    config_loaded: bool = False
