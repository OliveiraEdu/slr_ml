# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
