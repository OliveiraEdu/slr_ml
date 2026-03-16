# PRISMA 2020 Systematic Literature Review Engine

A configuration-driven systematic literature review engine that automates paper retrieval, screening, and classification following PRISMA 2020 guidelines using SciBERT for zero-shot classification.

## Features

- **Multi-source import**: BibTeX and CSV files from WoS, IEEE Xplore, ACM, and Scopus
- **arXiv integration**: Real-time API queries for preprints
- **ML-powered screening**: SciBERT zero-shot classification using PICOC criteria
- **PRISMA 2020 compliance**: Automated flow diagram generation and reporting
- **Configuration-driven**: All settings via YAML files - no hardcoded values
- **REST API**: FastAPI with OpenAPI/Swagger documentation

## Supported Sources

| Source | Input Method | Formats |
|--------|-------------|---------|
| Web of Science | User-provided file | BibTeX, CSV |
| IEEE Xplore | User-provided file | BibTeX, CSV |
| ACM Digital Library | User-provided file | BibTeX, CSV |
| Scopus | User-provided file | BibTeX, CSV |
| arXiv | API query | Real-time |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Sources

Edit `config/sources.yaml` to specify input files and arXiv queries.

### 3. Configure Classification

Edit `config/classification.yaml` to set PICOC criteria and thresholds.

### 4. Run the API

```bash
uvicorn src.api.main:app --reload
```

### 5. Access API Documentation

Open `http://localhost:8000/docs` for Swagger UI.

## Configuration

All configuration is managed through YAML files in the `config/` directory:

- `sources.yaml` - Data sources, file paths, and arXiv queries
- `classification.yaml` - PICOC labels, prompts, and classification thresholds
- `model.yaml` - SciBERT model configuration
- `prisma.yaml` - PRISMA reporting settings

## Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
│   YAML      │───▶│   Loader     │───▶│  Deduplication   │
│   Configs   │    │  (BibTeX/CSV)│    │  (DOI + Title)  │
└─────────────┘    └──────────────┘    └────────┬─────────┘
                                                │
┌─────────────┐    ┌──────────────┐            ▼
│   arXiv     │───▶│   API Client  │───▶  ┌─────────────┐
│   Query     │    │               │      │  Unified    │
└─────────────┘    └──────────────┘      │  Paper DB   │
                                          └──────┬────────┘
                                                 │
                           ┌─────────────────────┴─────────────────────┐
                           │         SCREENING STAGE (PRISMA)           │
                           │  Title/Abstract → Full-text → INCLUDED    │
                           └────────────────────────────────────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/config/load` | POST | Load YAML configs |
| `/papers/import` | POST | Import user files |
| `/papers/arxiv` | POST | Query arXiv API |
| `/papers/dedupe` | POST | Run deduplication |
| `/screening/run` | POST | Run ML screening |
| `/prisma/flow` | GET | Generate PRISMA flow data |

## License

MIT License - see LICENSE file.
