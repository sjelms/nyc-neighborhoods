# nyc-neighborhoods Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-02

## Active Technologies

- Python 3.11 + requests, beautifulsoup4, pandas, pydantic, typer (001-automated-neighborhood-profile-generator)
- pytest, pytest-cov, pytest-mock (001-automated-neighborhood-profile-generator)

## Project Structure

```text
src/
tests/
```

## Current Focus: Pytest Troubleshooting

We are currently in Phase 7: Pytest Troubleshooting. The goal is to resolve errors encountered during test execution.

**Key Issues:**
- `SyntaxError: unterminated triple-quoted string literal` in `src/services/wikipedia_parser.py`
- `AttributeError: module 'pytest' has no attribute 'pytest'` in `tests/unit/test_template_renderer.py`

**Next Steps:**
1. Fix the syntax error in `wikipedia_parser.py`.
2. Correct the typo in `test_template_renderer.py`.
3. Re-run tests to confirm all errors are resolved.

## Commands

cd src
.venv/bin/python -m pytest
ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes

- 001-automated-neighborhood-profile-generator: Added Python 3.11 + requests, beautifulsoup4, pandas, pydantic, typer
- 001-automated-neighborhood-profile-generator: Added pytest, pytest-cov, pytest-mock

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->