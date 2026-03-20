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


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScreeningMethod(str, Enum):
    ML = "ml"
    MANUAL = "manual"
    HYBRID = "hybrid"


class ScreeningDecision(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"
    PENDING = "pending"


class ScreeningPhase(str, Enum):
    TITLE_ABSTRACT = "title_abstract"
    FULL_TEXT = "full_text"


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


class ClassificationLabel(BaseModel):
    enabled: bool = True
    prompt: str
    description: str = ""


class SubQuestions(BaseModel):
    sq1_blockchain_platforms: ClassificationLabel
    sq2_provenance_model: ClassificationLabel
    sq3_architecture: ClassificationLabel
    sq4_permissioned_vs_permissionless: ClassificationLabel
    sq5_evaluation: ClassificationLabel


class InclusionCriteria(BaseModel):
    i1_language: ClassificationLabel
    i2_publication_type: ClassificationLabel
    i3_date_range: ClassificationLabel
    i4_technical_implementation: ClassificationLabel
    i5_domain_relevance: ClassificationLabel


class ExclusionCriteria(BaseModel):
    e1_opinion_pieces: ClassificationLabel
    e2_non_research: ClassificationLabel
    e3_no_implementation: ClassificationLabel
    e4_duplicates: ClassificationLabel
    e5_no_fulltext: ClassificationLabel
    e6_no_blockchain: ClassificationLabel
    e7_no_scientific_data: ClassificationLabel


class KeywordsConfig(BaseModel):
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)


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


class RankingWeights(BaseModel):
    relevance: float = 0.5
    citations: float = 0.3
    recency: float = 0.2


class ScreeningStage(BaseModel):
    enabled: bool = True
    min_text_length: int = 50


class ScreeningStages(BaseModel):
    title_abstract: ScreeningStage = Field(default_factory=ScreeningStage)
    full_text: ScreeningStage = Field(default_factory=ScreeningStage)


class ClassificationConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    research_question: Optional[str] = None
    relevance: RelevanceConfig = Field(default_factory=RelevanceConfig)
    sub_questions: Optional[SubQuestions] = None
    inclusion_criteria: Optional[InclusionCriteria] = None
    exclusion_criteria: Optional[ExclusionCriteria] = None
    keywords: Optional[KeywordsConfig] = None
    thresholds: Thresholds = Field(default_factory=Thresholds)
    stages: ScreeningStages = Field(default_factory=ScreeningStages)
    ranking_weights: RankingWeights = Field(default_factory=RankingWeights)


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


class FullTextSource(str, Enum):
    DOI = "doi"
    ARXIV = "arxiv"
    MANUAL = "manual"
    UNAVAILABLE = "unavailable"
    FLAGGED = "flagged"


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
    citations: int = 0
    full_text: Optional[str] = None
    full_text_source: Optional[FullTextSource] = None
    full_text_path: Optional[str] = None
    full_text_retrievable: bool = True
    flagged_reason: Optional[str] = None
    raw_metadata: dict = Field(default_factory=dict)
    crossref_id: Optional[str] = None
    datacite_id: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    referenced_works: list[str] = Field(default_factory=list)


class ScreeningResult(BaseModel):
    paper_id: str
    phase: ScreeningPhase = ScreeningPhase.TITLE_ABSTRACT
    relevance_score: float = 0.0
    relevance_label: str = "unclassified"
    citation_score: float = 0.0
    recency_score: float = 0.0
    composite_score: float = 0.0
    picoc_scores: dict[str, float] = Field(default_factory=dict)
    decision: ScreeningDecision = ScreeningDecision.PENDING
    confidence: float = 0.0
    confidence_band: ConfidenceBand = ConfidenceBand.LOW
    screened_by: ScreeningMethod = ScreeningMethod.ML
    reason: Optional[str] = None
    exclusion_category: Optional[str] = None
    notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    # Two-stage workflow fields
    stage_1_decision: Optional[ScreeningDecision] = None
    stage_1_confidence: Optional[float] = None
    stage_1_reviewed_at: Optional[str] = None
    stage_2_decision: Optional[ScreeningDecision] = None
    stage_2_confidence: Optional[float] = None
    stage_2_reviewed_at: Optional[str] = None
    progressed_to_stage_2: bool = False
    full_text_retrieved: bool = False
    full_text_source: Optional[FullTextSource] = None
    flagged_for_no_ft: bool = False


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
    # Two-stage workflow additions
    stage_2_eligible: int = 0
    stage_2_screened: int = 0
    flagged_no_doi: int = 0
    arxiv_preprints: int = 0
    full_text_retrieved: int = 0
    full_text_unavailable: int = 0


class EngineState(BaseModel):
    papers: list[Paper] = Field(default_factory=list)
    screening_results: list[ScreeningResult] = Field(default_factory=list)
    prisma_flow: PrismaFlowData = Field(default_factory=PrismaFlowData)
    config_loaded: bool = False


class ExtractionData(BaseModel):
    study_id: str
    paper_id: str
    
    # Publication info
    citation: Optional[str] = None
    
    # Research Focus
    research_focus: Optional[str] = None
    approach_type: Optional[str] = None  # Technical implementation, Survey, Framework, etc.
    
    # System Information
    system_name: Optional[str] = None
    system_description: Optional[str] = None
    
    # Blockchain Characteristics
    blockchain_platform: Optional[str] = None  # Ethereum, Hyperledger Fabric, IPFS, etc.
    blockchain_type: Optional[str] = None  # Public, Private, Consortium
    consensus_mechanism: Optional[str] = None  # PoW, PoS, PBFT, etc.
    smart_contract_language: Optional[str] = None  # Solidity, Go, etc.
    
    # Data Management
    madmp_standard: Optional[str] = None  # DMP Common Standard, RO-Crate, Dublin Core, etc.
    metadata_schema: Optional[str] = None
    linked_data_support: bool = False
    fair_principles_compliance: Optional[str] = None  # Fully, Partially, Not compliant
    
    # Provenance Tracking
    provenance_model: Optional[str] = None  # PROV-O, DCAT, custom, etc.
    provenance_approach: Optional[str] = None  # On-chain, Off-chain, Hybrid
    verification_mechanism: Optional[str] = None
    
    # Storage Integration
    storage_integration: Optional[str] = None  # On-chain, Off-chain, IPFS, Swarm, etc.
    data_partitioning: Optional[str] = None
    data_encryption: bool = False
    
    # Permission Model
    permission_model: Optional[str] = None  # Permissioned, Permissionless, Hybrid
    access_control_mechanism: Optional[str] = None
    
    # Evaluation
    evaluation_method: Optional[str] = None  # Experimental, Case study, Simulation, etc.
    performance_metrics: Optional[str] = None
    scalability_assessment: Optional[str] = None
    benchmarks_reported: bool = False
    
    # Key Findings
    key_findings: Optional[str] = None
    contributions: Optional[str] = None
    novel_aspects: Optional[str] = None
    
    # Limitations & Future Work
    limitations: Optional[str] = None
    future_work: Optional[str] = None
    
    # Quality Assessment
    quality_score: Optional[float] = None
    methodological_quality: Optional[str] = None
    
    # Extraction metadata
    extracted_by: Optional[str] = "system"
    extraction_date: Optional[str] = None
    notes: Optional[str] = None


class ExtractionField(BaseModel):
    name: str
    label: str
    field_type: str  # text, select, multiselect, boolean, number
    options: Optional[list[str]] = None
    required: bool = False
    category: Optional[str] = None
    description: Optional[str] = None


class ExtractionTemplate(BaseModel):
    name: str
    description: str
    fields: list[ExtractionField]
    version: str = "1.0"
    
    @classmethod
    def create_madmp_template(cls) -> "ExtractionTemplate":
        return cls(
            name="maDMP Blockchain Provenance",
            description="Extraction template for maDMP and blockchain provenance studies",
            fields=[
                ExtractionField(
                    name="approach_type",
                    label="Approach Type",
                    field_type="select",
                    options=["Technical Implementation", "Framework", "Survey", "Case Study", "Protocol", "Tool"],
                    required=True,
                    category="Research Focus",
                ),
                ExtractionField(
                    name="blockchain_platform",
                    label="Blockchain Platform",
                    field_type="multiselect",
                    options=["Ethereum", "Hyperledger Fabric", "Hyperledger Indy", "Corda", "IPFS", "Polkadot", "Cardano", "Multi-chain", "Other"],
                    required=True,
                    category="Blockchain",
                ),
                ExtractionField(
                    name="blockchain_type",
                    label="Blockchain Type",
                    field_type="select",
                    options=["Public", "Private", "Consortium", "Hybrid"],
                    required=False,
                    category="Blockchain",
                ),
                ExtractionField(
                    name="consensus_mechanism",
                    label="Consensus Mechanism",
                    field_type="select",
                    options=["Proof of Work", "Proof of Stake", "PBFT", "Raft", "Practical Byzantine Fault Tolerance", "Other"],
                    required=False,
                    category="Blockchain",
                ),
                ExtractionField(
                    name="madmp_standard",
                    label="DMP Standard",
                    field_type="select",
                    options=["DMP Common Standard", "RO-Crate", "Dublin Core", "DCAT", "Custom", "None"],
                    required=False,
                    category="Data Management",
                ),
                ExtractionField(
                    name="fair_principles_compliance",
                    label="FAIR Principles Compliance",
                    field_type="select",
                    options=["Fully Compliant", "Partially Compliant", "Not Compliant", "Not Assessed"],
                    required=False,
                    category="Data Management",
                ),
                ExtractionField(
                    name="provenance_model",
                    label="Provenance Model",
                    field_type="select",
                    options=["PROV-O", "DCAT", "OPM", "Custom", "None"],
                    required=False,
                    category="Provenance",
                ),
                ExtractionField(
                    name="provenance_approach",
                    label="Provenance Approach",
                    field_type="select",
                    options=["On-chain", "Off-chain", "Hybrid"],
                    required=False,
                    category="Provenance",
                ),
                ExtractionField(
                    name="permission_model",
                    label="Permission Model",
                    field_type="select",
                    options=["Permissioned", "Permissionless", "Hybrid"],
                    required=False,
                    category="Access Control",
                ),
                ExtractionField(
                    name="evaluation_method",
                    label="Evaluation Method",
                    field_type="select",
                    options=["Experimental", "Case Study", "Simulation", "Theoretical Analysis", "Not Evaluated"],
                    required=False,
                    category="Evaluation",
                ),
                ExtractionField(
                    name="scalability_assessment",
                    label="Scalability Assessment",
                    field_type="select",
                    options=["High", "Medium", "Low", "Not Assessed"],
                    required=False,
                    category="Evaluation",
                ),
                ExtractionField(
                    name="key_findings",
                    label="Key Findings",
                    field_type="text",
                    required=False,
                    category="Findings",
                ),
                ExtractionField(
                    name="novel_aspects",
                    label="Novel Aspects",
                    field_type="text",
                    required=False,
                    category="Findings",
                ),
            ],
        )


class QualityRating(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    VERY_POOR = "very_poor"


class MMATScore(BaseModel):
    clear_research_questions: Optional[str] = None
    appropriate_methodology: Optional[str] = None
    rigorous_data_collection: Optional[str] = None
    sound_analysis: Optional[str] = None
    well_supported_conclusions: Optional[str] = None


class QualityAssessment(BaseModel):
    paper_id: str
    mmat_score: Optional[MMATScore] = None
    rating: Optional[QualityRating] = None
    overall_score: Optional[float] = None
    notes: Optional[str] = None


class PrismaChecklistItem(BaseModel):
    item_number: int
    section: str
    description: str
    status: str = "not_applicable"
    page_reference: Optional[str] = None
    notes: Optional[str] = None


class PrismaProtocol(BaseModel):
    title: str
    registration_number: Optional[str] = None
    registration_date: Optional[str] = None
    review_stage: str = "in_progress"
    start_date: Optional[str] = None
    expected_end_date: Optional[str] = None
    actual_end_date: Optional[str] = None
    amendments: list[str] = Field(default_factory=list)


class PrismaChecklist(BaseModel):
    protocol: PrismaProtocol
    items: list[PrismaChecklistItem] = Field(default_factory=list)
    completeness_score: float = 0.0
    
    @classmethod
    def create_default(cls) -> "PrismaChecklist":
        protocol = PrismaProtocol(
            title="How can machine-actionable Data Management Plans (maDMPs) be persisted on a blockchain to enable verifiable provenance tracking for scientific data?",
            review_stage="in_progress",
        )
        
        items = [
            # TITLE
            PrismaChecklistItem(item_number=1, section="Title", description="Identify the report as a systematic review."),
            # ABSTRACT
            PrismaChecklistItem(item_number=2, section="Abstract", description="Provide a structured summary including background, objectives, data sources, study eligibility criteria, participants, interventions, study appraisal methods, results, limitations, conclusions, registration number."),
            # RATIONALE
            PrismaChecklistItem(item_number=3, section="Rationale", description="Describe the rationale for the review in the context of existing knowledge."),
            # OBJECTIVES
            PrismaChecklistItem(item_number=4, section="Objectives", description="Provide an explicit statement of the specific research question(s) addressing maDMPs and blockchain provenance."),
            # ELIGIBILITY CRITERIA
            PrismaChecklistItem(item_number=5, section="Eligibility criteria", description="Specify inclusion/exclusion criteria including information sources, methods, eligibility criteria for studies."),
            PrismaChecklistItem(item_number=6, section="Eligibility criteria", description="Specify date range for searching (2018-present for blockchain/scientific data)."),
            PrismaChecklistItem(item_number=7, section="Eligibility criteria", description="Specify language restrictions (English)."),
            PrismaChecklistItem(item_number=8, section="Eligibility criteria", description="Specify publication status restrictions (published papers, preprints)."),
            # INFORMATION SOURCES
            PrismaChecklistItem(item_number=9, section="Information sources", description="Describe all intended information sources (WoS, ACM, IEEE, Scopus, PubMed, ArXiv)."),
            PrismaChecklistItem(item_number=10, section="Information sources", description="Specify date last searched for each source."),
            # SEARCH STRATEGY
            PrismaChecklistItem(item_number=11, section="Search strategy", description="Present full search strategies for all databases including keywords and MeSH terms."),
            PrismaChecklistItem(item_number=12, section="Search strategy", description="Specify whether search was limited to title/abstract or full-text."),
            # STUDY SELECTION PROCESS
            PrismaChecklistItem(item_number=13, section="Study selection process", description="Specify methods used to determine whether studies met inclusion criteria."),
            PrismaChecklistItem(item_number=14, section="Study selection process", description="State whether screening was single or dual (for solo PhD: specify single with validation)."),
            PrismaChecklistItem(item_number=15, section="Study selection process", description="Describe methods of data extraction (automated ML-assisted, manual, or hybrid)."),
            # STUDY CHARACTERISTICS
            PrismaChecklistItem(item_number=16, section="Study characteristics", description="Cite each included study and describe characteristics used to inform eligibility."),
            PrismaChecklistItem(item_number=17, section="Study characteristics", description="Provide citation information for each included study."),
            # RISK OF BIAS
            PrismaChecklistItem(item_number=18, section="Risk of bias", description="Describe methods used to assess risk of bias in included studies."),
            PrismaChecklistItem(item_number=19, section="Risk of bias", description="Describe methods to assess validity of screening process (e.g., ML accuracy metrics)."),
            # MEASUREMENTS
            PrismaChecklistItem(item_number=20, section="Synthesis methods", description="Describe processes for quantifying results (e.g., inclusion rates, consensus measures)."),
            PrismaChecklistItem(item_number=21, section="Synthesis methods", description="Describe methods for data synthesis (narrative, thematic, quantitative)."),
            # CONFLICT OF INTEREST
            PrismaChecklistItem(item_number=22, section="Competing interests", description="Declare any competing interests of review authors."),
            # FUNDING
            PrismaChecklistItem(item_number=23, section="Source of funding", description="Describe sources of funding or material support for the review."),
            # PROTOCOL
            PrismaChecklistItem(item_number=24, section="Protocol registration", description="Indicate where and when the review protocol was registered (PROSPERO)."),
            PrismaChecklistItem(item_number=25, section="Protocol amendments", description="Describe any amendments to information in the protocol since registration."),
            # CONFLICTS
            PrismaChecklistItem(item_number=26, section="Conflicts of interest", description="Report any conflicts of interest for each included study."),
            # REPORTING
            PrismaChecklistItem(item_number=27, section="Reporting", description="Report any issues found during conduct that were not in protocol."),
        ]
        
        return cls(protocol=protocol, items=items)


class ConvertMarkdownRequest(BaseModel):
    markdown: Optional[str] = None
    file_path: Optional[str] = None
    title: str = "Document"
    wrap_document: bool = True
    extract_mermaid: bool = True


class ConvertMarkdownResponse(BaseModel):
    latex: str
