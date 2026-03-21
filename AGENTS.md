# AGENTS.md - Agent Coding Guidelines

This file provides guidelines for AI agents working in this repository.

## Build, Lint, and Test Commands

### Running the API

```bash
# Start API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# With auto-reload
uvicorn src.api.main:app --reload
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_text_utils.py

# Run specific test function
pytest tests/test_loaders.py::TestBibtexLoader::test_load_bibtex_single_entry

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Type checking (mypy)
mypy src/

# Format code (black)
black src/

# Sort imports (isort)
isort src/
```

---

## Code Style Guidelines

### General Principles

- Keep code concise and focused
- Avoid unnecessary comments (let code explain itself)
- Use descriptive variable/function names
- Follow Single Responsibility Principle

### Imports

- Use absolute imports: `from src.models.schemas import Paper`
- Group imports: standard library → third-party → local
- Sort alphabetically within groups
- Do NOT use wildcard imports (`from x import *`)

### Type Hints

- Always use type hints for function parameters and return values
- Use `Optional[X]` instead of `X | None` for compatibility
- Example:
  ```python
  def process_papers(papers: list[Paper], limit: int = 10) -> dict[str, int]:
      ...
  ```

### Naming Conventions

- **Files**: snake_case (e.g., `prisma_generator.py`)
- **Classes**: PascalCase (e.g., `PrismaGenerator`)
- **Functions/variables**: snake_case (e.g., `generate_flow_data`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `MAX_PAPERS`)
- **Private members**: prefix with underscore (e.g., `_internal_method`)

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Example:
  ```python
  if not papers:
      raise ValueError("No papers provided for screening")
  ```

### Pydantic Models

- Use `BaseModel` for request/response schemas
- Use `Field` for validation and descriptions
- Example:
  ```python
  class ScreeningRequest(BaseModel):
      papers: Optional[list[Paper]] = None
      threshold: float = Field(default=0.5, ge=0.0, le=1.0)
  ```

### FastAPI Endpoints

- Always define request models using Pydantic
- Use `HTTPException` for error responses
- Add docstrings to endpoints
- Example:
  ```python
  @app.post("/papers/import")
  async def import_papers(request: ImportRequest):
      """Import papers from a file."""
      ...
  ```

### Configuration

- All settings go in YAML files under `config/`
- No hardcoded values in source code
- Use ConfigLoader for loading config

### API State Management

- Use the global `app_state` dict for in-memory state
- Initialize all keys in the app_state definition
- Example:
  ```python
  app_state = {
      "papers": [],
      "results": [],
      "config_loaded": False,
      ...
  }
  ```

---

## Project Structure

```
slr_ml/
├── src/
│   ├── api/              # FastAPI application
│   │   └── routers/      # API route modules
│   │       ├── papers.py          # Paper import/export endpoints
│   │       ├── screening.py       # ML screening workflow
│   │       ├── prisma.py          # PRISMA reporting
│   │       ├── enrichment.py      # DOI enrichment
│   │       ├── config.py          # Configuration management
│   │       ├── converters.py      # Format conversion
│   │       ├── advanced.py        # Dual screening, sensitivity, RoB
│   │       └── fulltext.py        # Full-text retrieval
│   ├── ml/               # ML classifiers
│   ├── pipeline/         # Processing pipelines
│   │   ├── dual_screening.py      # Dual screening + Cohen's Kappa
│   │   ├── sensitivity_analysis.py # Threshold sensitivity + bias
│   │   ├── risk_of_bias.py        # RoB 2.0, ROBINS-T
│   │   ├── completeness.py        # PRISMA 2020 completeness
│   │   ├── provenance.py          # Screening decision audit
│   │   ├── fulltext_retriever.py  # DOI/arXiv PDF retrieval
│   │   └── extraction.py          # Data extraction
│   ├── loaders/          # File loaders (BibTeX, CSV)
│   ├── connectors/       # External APIs (DOI, ArXiv)
│   ├── converters/      # Document converters (MD to LaTeX)
│   ├── models/           # Schemas and config
│   └── utils/            # Shared utilities
├── config/               # YAML configuration files
├── inputs/               # Input papers
├── outputs/              # Generated reports
├── scripts/              # Utility scripts
│   └── export_review_queue.py  # CSV export/import for manual review
├── tests/                # Test files
└── docs/                 # Documentation
```

---

## Adding New Features

1. Create config options in YAML if behavior needs to be configurable
2. Add Pydantic models in `src/models/schemas.py`
3. Implement logic in appropriate `src/` subdirectory
4. Add API endpoints in the appropriate router module under `src/api/routers/`
5. Add tests in `tests/`
6. Update CHANGELOG.md

---

## Commit Message Format

Follow Conventional Commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `refactor:` code refactoring
- `test:` adding tests
- `chore:` maintenance

Example: `feat: Add PRISMA 2020 full report generation`
