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

## Current Focus: Data Source Hardening (Phase 8)

Following a comprehensive code audit, all identified issues have been resolved. The project is now ready to proceed with **Phase 8: Data Source Hardening**. The primary goal is to improve the reliability and precision of data extraction, particularly from Wikipedia.

## Next Steps

1.  **Implement REST API Fallback:** Use the Wikipedia REST API for page summaries as a more stable alternative to HTML parsing.
2.  **Improve Infobox Parsing:** Make infobox parsing more robust to handle variations in structure and content.
3.  **Broaden Content Extraction:** Relax parsing rules to capture summary and transit information from more varied page layouts.
4.  **Normalize Rendered Output:** Strip artifacts and non-breaking spaces from the final Markdown output.

## Commands

cd src
.venv/bin/python -m pytest
ruff check .

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes

- **Code Audit Fixes (December 2025):**
  - **Data Model Consistency:** Aligned data types for `population`, `area`, `population_density`, and `generation_date` across the Pydantic models, `data-model.md`, and JSON schemas.
  - **Code Portability:** Replaced all absolute, user-specific file paths in logs and source code with relative paths to ensure the project is portable.
  - **Code Quality:**
    - Refactored `src/cli/main.py` to move a helper function to the module level and remove a confusing logger alias.
    - Added missing `json` imports to prevent `NameError` in scripts.
    - Made the NYC Open Data dataset ID configurable and improved query precision for more accurate data matching.
- 001-automated-neighborhood-profile-generator: Added Python 3.11 + requests, beautifulsoup4, pandas, pydantic, typer
- 001-automated-neighborhood-profile-generator: Added pytest, pytest-cov, pytest-mock

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->