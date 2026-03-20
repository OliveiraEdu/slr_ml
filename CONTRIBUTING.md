# Contributing to PRISMA SLR Engine

Contributions are welcome! Please follow these guidelines:

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public functions

## Testing

Run tests with:
```bash
pytest                    # All tests
make test                 # Unit tests only
make test-integration     # Integration tests (requires running API)
make verify-api          # Verify API is accessible
make smoke-test          # Comprehensive smoke test (7 endpoints)
```

## Commit Messages

Follow Conventional Commits:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `refactor:` for code refactoring
- `test:` for tests
