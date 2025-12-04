# Tasks: LLM Pipeline Fix & Refactor

**Source Plan**: [plan.md](plan.md)

---

## Progress & Current Status

This task list tracks the implementation of the LLM Pipeline Fix & Refactor. As of **2025-12-03**, the following progress has been made:

### Phase 1: Diagnosis & Immediate Bug Fix (Completed)

*   **Initial Problem**: The LLM pipeline was failing to produce enriched Markdown output, despite being integrated.
*   **Root Causes & Fixes**:
    *   **API Parameter Inconsistencies**: The OpenAI API was rejecting calls due to unsupported `max_tokens` and `temperature` parameters. This was resolved by implementing a robust retry mechanism in `src/services/llm_helper.py` to test various token parameters and by removing the `temperature` parameter entirely.
    *   **Empty LLM Response**: The initial `gpt-5-mini` model was returning empty content, even for successful API calls. This was diagnosed through debug logging and fixed by upgrading the default model to `gpt-5.1-2025-11-13` in `src/cli/main.py` and `src/services/llm_helper.py`.
    *   **Brittle Template Rendering**: The `TemplateRenderer` in `src/lib/template_renderer.py` contained a series of fragile string replacements and greedy regular expressions, causing LLM-enriched data to not appear in the final Markdown output and, in a subsequent iteration, deleting entire sections. This was resolved by rewriting the `render` method with more precise and non-greedy regex patterns, as well as fixing an accidental indentation error that broke the method entirely.
    *   **ZIP Code Merging Issue**: The `DataNormalizer` was incorrectly merging ZIP code lists when the scraper returned comma-separated strings, leading to duplicate entries. This was fixed in `src/services/data_normalizer.py` by implementing a smarter merge logic that flattens and deduplicates list items.
*   **Outcome**: The core data pipeline is now fully functional. The LLM is consistently returning valid, rich JSON, which is being correctly merged and rendered into the Markdown output files.

### Phase 2: Architectural Refactoring (In Progress)

*   **Current Goal**: Enhance caching and logging mechanisms for robustness, debuggability, and cost-efficiency.
*   **Completed Tasks**:
    *   **T003**: Created new `cache/html/` and `cache/llm/` subdirectories.
    *   **T004**: Refactored `src/lib/cache_manager.py` to be a generic file storage utility, supporting descriptive filenames and subdirectories, and delegating expiry management to callers.
    *   **T005**: Updated `src/services/web_fetcher.py` to use the refactored `CacheManager`, managing its own cache expiry and content wrapping.
    *   **T006**: Confirmed `src/lib/generation_log.py` is flexible enough to accept the new `llm_cache_path` field without modification.
    *   **T007**: Modified `src/services/llm_helper.py` to save successfully parsed LLM responses to `cache/llm/` with descriptive, timestamped filenames, and to return the cache path.
*   **Next Up**: **T008**: Orchestration Logic for LLM cache.

---

# Tasks: LLM Pipeline Fix & Refactor

**Source Plan**: [plan.md](plan.md)

---

This task list is generated based on the implementation plan. Tasks are organized into phases.

## Phase 1: Diagnosis & Immediate Bug Fix

- [x] T001 Run script with `--log-level DEBUG` to capture the raw LLM response for analysis.
- [x] T002 Analyze debug logs and modify `src/services/llm_helper.py` to correctly parse the LLM response into a valid JSON object.

## Phase 2: Architectural Refactoring

- [x] T003 Create cache subdirectories: `cache/html/` and `cache/llm/`.
- [x] T004 [P] Refactor `src/lib/cache_manager.py` to support descriptive filenames and save to specified subdirectories instead of using hashes.
- [x] T005 [P] Update `src/services/web_fetcher.py` to use the refactored `CacheManager` for caching HTML content with descriptive names.
- [x] T006 [P] Modify `src/lib/generation_log.py` to add the `llm_cache_path` field to the log entry data structure.
- [x] T007 Modify `src/services/llm_helper.py` to save successfully parsed LLM responses to the `cache/llm/` directory with a descriptive, timestamped filename.
- [ ] T008 Modify `src/services/profile_generator.py` and `src/services/llm_helper.py` to orchestrate the new caching workflow, ensuring the LLM cache is checked before making a live API call.

## Phase 3: Verification

- [ ] T009 Verify the full pipeline by running with `--force-regenerate` and confirming that enriched profiles are created and all caching/logging mechanisms work as designed.
- [ ] T010 Verify the LLM cache hits by re-running the script *without* `--force-regenerate` and confirming in the logs that no new API calls are made.
