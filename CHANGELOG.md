# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-03-20

### Phase 1: ML-Assisted Screening (Complete)

#### Added
- **Confidence Calibration**: New `ConfidenceBand` enum (high/medium/low) with threshold-based classification
- **Enhanced Classifier**: Multi-level keyword matching with:
  - Required keywords (50% weight)
  - Relevant keywords (35% weight)  
  - Exclusion keywords (15% penalty)
  - Compound phrase boosting (for "machine-actionable", "data management plan")
  - Keyword frequency scoring
- **New Screening Enums**: 
  - `ConfidenceBand` - high/medium/low for confidence tiers
  - `ScreeningMethod` - ml/manual/hybrid tracking
  - `ScreeningDecision` - include/exclude/uncertain/pending
  - `ScreeningPhase` - title_abstract/full_text stages
- **Manual Review Queue**: `GET /screening/queue/uncertain` - Papers needing manual review
- **Screening Statistics**: `GET /screening/statistics` - PRISMA-ready statistics
- **Manual Review Update**: `POST /screening/review` - Update decisions manually

#### Updated
- **ScreeningResult Schema**: Added fields for confidence_band, screened_by, exclusion_category, notes
- **Classification Config**: Enhanced with 3-level keyword strategy
- **PRISMA Config**: Domain-specific exclusion reasons for maDMP/blockchain research

#### Domain Configuration
Updated `config/classification.yaml` with maDMP/blockchain keywords:
- **Required**: machine-actionable, maDMP, data management plan, blockchain, distributed ledger
- **Relevant**: provenance, FAIR, metadata, scientific data, IPFS
- **Exclusion**: supply chain, business process, DMP tool

### Phase 2: PRISMA 2020 Compliance (Complete)

#### Added
- **PRISMA 2020 Checklist Schema**: Full 27-item checklist with models:
  - `PrismaChecklistItem` - Individual checklist items
  - `PrismaProtocol` - Protocol metadata (title, registration, dates)
  - `PrismaChecklist` - Complete checklist container
- **Checklist Endpoints**:
  - `GET /prisma/checklist` - Get full PRISMA 2020 checklist
  - `PUT /prisma/protocol` - Update protocol information
  - `PUT /prisma/checklist/item` - Update individual item status
  - `GET /prisma/checklist/report` - Get checklist grouped by section with completeness score
  - `POST /prisma/report/full` - Generate complete PRISMA report with checklist
- **Makefile Updates**: Added commands for Docker deployment and API testing

### Phase 3: Two-Stage Screening Workflow (Complete)

#### Added
- **Full-Text Schema Extensions**:
  - `FullTextSource` enum (DOI, ArXiv, Manual, Unavailable, Flagged)
  - `Paper.full_text_source`, `full_text_path`, `flagged_reason`
  - `ScreeningResult.stage_1_decision`, `stage_2_decision`, `full_text_retrieved`
- **Two-Stage Screening Endpoints**:
  - `GET /screening/progression` - Paper flow through stages
  - `GET /screening/queue/stage2` - Papers eligible for Stage 2
  - `POST /screening/stage2` - Run Stage 2 (full-text) screening
- **Full-Text Management Endpoints**:
  - `GET /papers/retrievable` - Papers eligible for FT retrieval
  - `GET /papers/flagged` - Papers flagged for no DOI
  - `POST /papers/flag/{id}` - Flag paper for no DOI
  - `GET /papers/{id}/fulltext` - Get paper's full-text
  - `POST /papers/{id}/fulltext` - Attach full-text content
  - `GET /papers/progress/fulltext` - FT retrieval progress
- **DOI Flagging Logic**: Papers without DOI are flagged and excluded from Stage 2 (except ArXiv)
- **Local Storage**: Full-text stored in `outputs/fulltext/`
- **PRISMA Flow Updates**: Added `flagged_no_doi`, `arxiv_preprints`, `full_text_retrieved`

### Phase 4: Data Extraction & Synthesis (Complete)

#### Added
- **Enhanced Extraction Schema**: `ExtractionData` model with 35+ fields for maDMP/blockchain research:
  - Blockchain: platform, type, consensus mechanism, smart contract language
  - Data Management: maDMP standard, metadata schema, FAIR compliance
  - Provenance: model, approach, verification mechanism
  - Storage: integration type, partitioning, encryption
  - Access Control: permission model, mechanism
- **Synthesis Generator**: `SynthesisGenerator` class with comprehensive analysis:
  - `_analyze_blockchains()` - Platform and consensus analysis
  - `_analyze_platforms()` - Technology distribution
  - `_analyze_approaches()` - Research approach breakdown
  - `_analyze_evaluations()` - Evaluation method analysis
  - `_identify_gaps()` - Research gap detection
  - `_identify_trends()` - Trend identification
- **Synthesis Endpoints**:
  - `GET /prisma/extraction/template` - Get maDMP extraction form template
  - `GET /prisma/synthesis` - Get synthesis statistics
  - `GET /prisma/synthesis/platforms` - Platform analysis
  - `GET /prisma/synthesis/distributions` - Distribution statistics
  - `GET /prisma/synthesis/gaps` - Research gaps identification
  - `POST /prisma/synthesis/report` - Generate synthesis report
- **Quality Assessment Endpoints**:
  - `POST /prisma/quality/assess` - Run quality assessment
  - `GET /prisma/quality/{paper_id}` - Get quality for paper
  - `PUT /prisma/quality/{paper_id}` - Update quality assessment
- **MMAT Quality Scoring**: Configurable criteria in `config/extraction.yaml`

### Bug Fixes
- Fixed `classifier` undefined error in `POST /screening/stage2` endpoint

### New Endpoints
- `POST /screening/review/batch` - Batch update multiple paper decisions
- `GET /prisma/extraction/export` - Export extraction data as CSV
- `GET /prisma/quality/export` - Export quality assessment as CSV
- `GET /prisma/quality/{paper_id}` - Get quality for specific paper
- `PUT /prisma/quality/{paper_id}` - Update quality assessment
- `POST /prisma/quality/assess` - Run quality assessment

### Improvements
- Auto-config loading on startup (no manual `/config/load` needed)
- API version updated to 0.5.0

### Data Source Downloads (Complete)

#### Added
- **URL Downloader**: `src/connectors/url_downloader.py` for downloading from remote URLs
- **Data Source Configuration**: `config/data_sources.yaml` with GitHub repository URLs
- **Download Endpoints**:
  - `GET /papers/sources` - List configured data sources
  - `POST /papers/download` - Download a file from URL
  - `POST /papers/download-all` - Download all enabled sources
  - `POST /papers/import-from-url` - Download and import in one step
- **Makefile Commands**: `make sources`, `make download-all`, `make download-and-import`

## [0.4.0] - 2026-03-20

### Refactored
- **Split API into Routers**: `src/api/main.py` (882 lines) split into modular routers:
  - `routers/papers.py` - Paper import/export endpoints
  - `routers/screening.py` - ML screening workflow
  - `routers/prisma.py` - PRISMA reporting
  - `routers/enrichment.py` - DOI metadata enrichment
  - `routers/config.py` - Configuration management
  - `routers/converters.py` - Document format conversion
- **Extracted Shared Utilities**: Created `src/utils/text_utils.py` with shared functions:
  - `clean_text()` - Text whitespace normalization
  - `clean_bibtex_text()` - BibTeX field cleaning
  - `clean_doi()` / `normalize_doi()` - DOI normalization
  - `generate_paper_id()` / `generate_bibtex_id()` - Paper ID generation
- **Added Proper Logging**: Replaced debug print statements with `logging` module
- **Improved Error Handling**: Better exception handling in health check endpoint

### Fixed
- **CSV Loader Bug**: Fixed duplicate separator in author parsing (`[";", ";"]` -> `[";", ","]`)
- **Dead Code Removed**: Removed unreachable code from `src/converters/md_to_latex.py` (lines 215-283)

### Added
- **Test Suite**: Comprehensive pytest tests in `tests/`:
  - `test_text_utils.py` - Text utility function tests
  - `test_loaders.py` - BibTeX and CSV loader tests
  - `test_converters.py` - Markdown to LaTeX converter tests
  - `test_connectors.py` - DOI and ArXiv connector tests
- **Configuration**: `tests/conftest.py` with pytest setup

## [0.3.0] - 2026-03-18

### Added
- **DOI Enrichment**: CrossRef and DataCite API integration for citation counts, references, and metadata
- **Markdown to LaTeX Converter**: Script to convert PRISMA reports to LaTeX for publication
- **ROADMAP.md**: Future enhancements and planned features
- **Makefile**: Docker deployment commands for easier management

### New API Endpoints
- `POST /papers/enrich` - Enrich papers with DOI metadata
- `GET /papers/enrich/{paper_id}` - Enrich single paper

### New Scripts
- `scripts/md_to_latex.py` - Markdown to LaTeX converter
- `config/convert.yaml` - Converter configuration

### Fixes
- PyTorch/SciBERT integration for accurate classification
- Graceful fallback to keyword-based classification when ML unavailable

## [0.2.0] - 2026-03-17

### Added
- **Health Check Enhancement**: `/health` endpoint now checks both API and ml-worker services
- **PRISMA 2020 Full Report Generation**: Complete markdown report with all sections
- **Study Data Extraction**: Automatic extraction of research focus, blockchain platform, storage integration, permission model
- **Quality Assessment (MMAT)**: Automatic quality scoring using Mixed Methods Appraisal Tool criteria
- **Docker Support**: ml-worker container with health endpoint on port 8001

### New API Endpoints
- `POST /prisma/extract` - Run extraction and quality assessment on included studies
- `GET /prisma/report` - Generate full PRISMA 2020 markdown report
- `GET /prisma/extraction` - Get extraction data
- `GET /prisma/quality` - Get quality assessment data

### New Configuration
- `config/extraction.yaml` - Extraction keywords and MMAT criteria (configurable)

### Implementation
- `src/pipeline/extraction.py`:
  - `ExtractionExtractor` class for automatic study characteristic extraction
  - `QualityAssessor` class for MMAT-based quality assessment
- `src/pipeline/prisma_generator.py`:
  - `generate_markdown_report()` method with full PRISMA 2020 sections
  - Mermaid flowchart generation

### Verified Working
- Full pipeline tested: 8,934 papers imported, 5,736 after dedup, 1,161 included
- Report generated with all sections: Flow diagram, Methods, Study Characteristics, Quality Assessment, Included Studies

## [0.1.0] - 2026-03-16

### Added
- Initial project setup with semantic versioning
- Git initialization with main branch
- Basic project structure following Python best practices
- README.md with comprehensive documentation
- CHANGELOG.md following Keep a Changelog format
- CONTRIBUTING.md with contribution guidelines
- LICENSE (MIT)
- .gitignore for Python projects
- Configuration system:
  - `config/sources.yaml` - Data sources configuration
  - `config/classification.yaml` - PICOC classification settings
  - `config/prisma.yaml` - PRISMA 2020 reporting settings
- `requirements.txt` with all dependencies
- Package structure with version module

### Implementation
- **Data Models** (`src/models/schemas.py`):
  - Pydantic models for Paper, ScreeningResult, PrismaFlowData
  - SourceName, FileFormat enums
  - Configuration models (SourcesConfig, ClassificationConfig, PrismaConfig)

- **Configuration Loader** (`src/models/config_loader.py`):
  - YAML-based configuration system
  - Lazy loading of config files
  - Factory functions for easy access

- **Loaders**:
  - `src/loaders/bibtex_loader.py` - BibTeX file parser (WoS, ACM)
  - `src/loaders/csv_loader.py` - CSV file parser (Scopus, IEEE)

- **Connectors**:
  - `src/connectors/arxiv_connector.py` - arXiv API client

- **ML Pipeline**:
  - `src/ml/classifier.py` - SciBERT zero-shot classifier with lazy loading
  - PICOC criteria classification support
  - Relevance scoring with confidence metrics

- **Screening Pipeline**:
  - `src/pipeline/screening.py` - PRISMA-compliant screening workflow
  - `src/pipeline/deduplication.py` - DOI and title-based deduplication
  - `src/pipeline/prisma_generator.py` - PRISMA 2020 flow diagram generator

- **API Layer**:
  - `src/api/main.py` - FastAPI application with OpenAPI/Swagger docs
  - REST endpoints for all pipeline stages
  - CORS enabled for cross-origin requests

### Verified Working
- Loaded 1501 papers from test files (WoS: 500, ACM: 734, IEEE: 257, Scopus: 10)
- Deduplication: 449 unique papers after removing 549 duplicates
- PRISMA flow diagram generation working
- API endpoints functional at http://localhost:8000
- Swagger docs at http://localhost:8000/docs
