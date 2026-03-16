# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
