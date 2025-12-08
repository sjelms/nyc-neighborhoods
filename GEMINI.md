# nyc-neighborhoods Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-03

## Active Technologies

- Python 3.11 + requests, beautifulsoup4, pandas, pydantic, typer (001-automated-neighborhood-profile-generator)
- pytest, pytest-cov, pytest-mock (001-automated-neighborhood-profile-generator)
- **openai, python-dotenv (002-helper-llm-feature)**

## Project Structure

```text
src/
tests/
cache/ # Added for caching web content and LLM responses
```

## Current Focus: LLM Pipeline Implementation & Refactoring (002-helper-llm-feature)

The project is currently focused on enhancing data extraction and enrichment through LLM integration. This involves resolving initial implementation bugs and refactoring the caching and logging architecture for robustness and debuggability.

## Next Steps

As per `specs/002-helper-llm-feature/tasks.md`:
- **T008**: Orchestration Logic for LLM cache.
- **T009**: Full Pipeline Verification (final run with all architectural changes).
- **T010**: Cache-Hit Verification (confirming LLM cache is effective).

## Commands

```bash
cd src
.venv/bin/python -m pytest
ruff check .
# To generate profiles with LLM assistance (use --log-level DEBUG for detailed debugging)
python3 -m src.cli.main generate-profiles --force-regenerate
```

## Code Style

Python 3.11: Follow standard conventions

## Recent Changes

- **LLM Pipeline Fix & Refactor (December 2025 - 002-helper-llm-feature):**
  - **Initial LLM Integration & Bug Fixing:**
    - **Resolved API Parameter Issues:** Fixed `LLMHelper` to correctly handle `max_tokens` and `temperature` parameters, preventing `400 Bad Request` errors and ensuring LLM calls succeed.
    - **Upgraded LLM Model:** Switched default model from `gpt-5-mini` (which returned empty responses) to `gpt-5.1-2025-11-13` for reliable JSON output.
    - **Fixed Brittle Template Rendering:** Rewrote `TemplateRenderer.render` using robust regex patterns to correctly populate all LLM-enriched data into Markdown files, resolving issues where sections were missing or unpopulated. Corrected an indentation error that previously broke the `render` method entirely.
    - **Corrected ZIP Code Merging:** Improved `DataNormalizer`'s logic to correctly parse and merge ZIP code lists, preventing duplication and formatting errors.
  - **Architectural Refactoring (In Progress):**
    - **Created Tiered Cache Directories:** Established `cache/html/` and `cache/llm/` for organized caching.
    - **Refactored CacheManager:** Transformed `src/lib/cache_manager.py` into a generic file storage utility, delegating expiry and metadata management to callers. Added `delete` method and updated `clear_all` for subdirectory handling.
    - **Refactored WebFetcher:** Updated `src/services/web_fetcher.py` to use the new `CacheManager`, implementing descriptive filenames and managing its own content wrapping and expiry for fetched HTML and JSON.
    - **Implemented LLM Response Caching:** Modified `src/services/llm_helper.py` to save successfully parsed LLM responses to `cache/llm/` with descriptive, timestamped filenames, and to return the cache path for logging.
- **Code Audit Fixes (December 2025 - 001-automated-neighborhood-profile-generator):**
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
