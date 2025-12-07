# Tasks: LLM Pipeline Fix & Refactor

**Source Plan**: [plan.md](plan.md)

---

## Progress & Current Status

This task list tracks the implementation of the LLM Pipeline Fix & Refactor. As of **2025-12-06**, the following progress has been made:

### Phase 1: Diagnosis & Immediate Bug Fix (Completed)
*   The initial LLM pipeline was failing to produce enriched Markdown output. This was traced to multiple issues including API parameters, model responses, template rendering, and data normalization, which have all been fixed.

### Phase 2: Architectural Refactoring (Completed)
*   The caching architecture was refactored to be more robust and debuggable, with separate caches for HTML and LLM responses.

### Phase 3: Verification (Completed)
*   The caching mechanism has been verified to work as expected, preventing redundant API calls.

### Phase 4: Bugfix - Transit Data Extraction (Failed)
*   Multiple attempts to fix a bug where transit data was not being extracted failed. The root cause was identified as a corrupted `wikipedia_parser.py` file, which was repeatedly broken during attempts to fix it. This approach was flawed.

### Phase 5: Final Parser & LLM Integration (In Progress)
*   **New Approach**: Per user feedback, the project is returning to the original plan. The `WikipediaParser` is now responsible *only* for extracting the raw text content. The `LLMHelper` is now responsible for taking this large block of unstructured text and extracting all the required details based on a robust new prompt.
*   **Next Up**: **T019**: Verify the final output.

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
- [x] T008 Modify `src/services/profile_generator.py` and `src/services/llm_helper.py` to orchestrate the new caching workflow, ensuring the LLM cache is checked before making a live API call.

## Phase 3: Verification

- [x] T009 Verify the full pipeline by running with `--force-regenerate` and confirming that enriched profiles are created and all caching/logging mechanisms work as designed.
- [x] T010 Verify the LLM cache hits by re-running the script *without* `--force-regenerate` and confirming in the logs that no new API calls are made.

## Phase 4: Bugfix - Transit Data Extraction

- [failed] T011 Re-implement `wikipedia_parser.py` with the correct structure and all necessary helper methods (`_get_section_text`, `_parse_infobox`, `_clean_infobox_value`, `_extract_adjacent_neighborhoods`). Reason: Parser corruption and incorrect text extraction logic.
- [failed] T012 Run the script with `--force-regenerate` and `--log-level DEBUG` to confirm the parser no longer crashes and that `transportation_text` is correctly passed to the LLM. Reason: `page_text` was consistently empty.
- [failed] T013 Verify that the final `Astoria_Queens.md` output file now contains the correct transit information. Reason: `page_text` was consistently empty.

## Phase 5: Final Parser & LLM Integration

- [x] T014 Fix `wikipedia_parser.py` to correctly and robustly extract the full, cleaned page text from the HTML, without attempting to parse specific sections like 'Transportation'.
- [x] T015 Update the `llm_helper.py` system prompt to be robust enough to extract all required fields (including transit details) from the full `page_text`.
- [failed] T016 Run the script and verify that the `Astoria_Queens.md` file is generated with all fields, including the complete `Transit & Accessibility` section, correctly populated. Reason: `page_text` passed to LLM was empty.
- [x] T017 Deep dive into `wikipedia_parser.py` to conclusively diagnose why `parser_output.get_text()` (or `parser_output.children` iteration) is not extracting the full content, leading to an empty `page_text`. Diagnosis: Initial `BeautifulSoup` usage was flawed, only capturing coordinates.
- [x] T018 Implement the definitive fix in `wikipedia_parser.py` for robust full-page text extraction using manual iteration over children and careful coordinate skipping.
- [ ] T019 Run the full pipeline with `--force-regenerate` and verify that `Astoria_Queens.md` is fully and correctly populated with all required data, including `Transit & Accessibility`.

## Phase 6: Wikipedia-first deterministic scrape, LLM as gap-filler (New)

- [x] T020 Capture lessons-learned from the LLM-first approach in `plan.md` (documented failures and anti-patterns).
- [x] T021 Enhance `WikipediaParser` to extract infobox metrics (population, population density, area, ZIP codes) plus heuristics for boundaries/adjacent areas and transit tokens from both sections and inline text.
- [x] T022 Add fixture-based tests using `cache/html/9bbcb6b6c18e86476af39c9f34bd6830.html` to assert non-empty population/area/ZIP/transit outputs from the parser.
- [x] T023 Update `DataNormalizer` to merge scraped fields first, then call the LLM only for missing/weak values; add warnings when the LLM fills gaps.
- [x] T024 Tighten `LLMHelper` prompt/merge path to respect scraped values (no overwrites unless empty) and ensure the LLM cache path is recorded when enrichment happens.
- [ ] T025 Run the pipeline on a small set (Astoria and one other) with `--force-regenerate`, confirm Markdown sections are populated from scrape+LLM, and backfill `generation_log.json` with useful warnings/LLM cache refs.

## Archive Tasks
### Phase 1: Diagnosis & Immediate Bug Fix 
*   **Initial Problem**: The LLM pipeline was failing to produce enriched Markdown output, despite being integrated.
*   **Root Causes & Fixes**:
    *   **API Parameter Inconsistencies**: The OpenAI API was rejecting calls due to unsupported `max_tokens` and `temperature` parameters. This was resolved by implementing a robust retry mechanism in `src/services/llm_helper.py` to test various token parameters and by removing the `temperature` parameter entirely.
    *   **Empty LLM Response**: The initial `gpt-5-mini` model was returning empty content, even for successful API calls. This was diagnosed through debug logging and fixed by upgrading the default model to `gpt-5.1-2025-11-13` in `src/cli/main.py` and `src/services/llm_helper.py`.
    *   **Brittle Template Rendering**: The `TemplateRenderer` in `src/lib/template_renderer.py` contained a series of fragile string replacements and greedy regular expressions, causing LLM-enriched data to not appear in the final Markdown output and, in a subsequent iteration, deleting entire sections. This was resolved by rewriting the `render` method with more precise and non-greedy regex patterns, as well as fixing an accidental indentation error that broke the method entirely.
    *   **ZIP Code Merging Issue**: The `DataNormalizer` was incorrectly merging ZIP code lists when the scraper returned comma-separated strings, leading to duplicate entries. This was fixed in `src/services/data_normalizer.py` by implementing a smarter merge logic that flattens and deduplicates list items.
*   **Outcome**: The core data pipeline is now fully functional. The LLM is consistently returning valid, rich JSON, which is being correctly merged and rendered into the Markdown output files.

### Phase 2: Architectural Refactoring (Completed)
*   **Goal**: Enhance caching and logging mechanisms for robustness, debuggability, and cost-efficiency.
*   **Completed Tasks**:
    *   **T003 - T005**: Created tiered cache directories and refactored `CacheManager` and `WebFetcher` to use them effectively.
    *   **T006 - T007**: Modified `LLMHelper` to save responses to the new LLM cache directory.
    *   **T008**: Implemented self-contained caching logic in `LLMHelper` to check for a valid cache entry before making an API call.
    
    ### Phase 3: Verification (Completed)
    *   **T009 - T010**: Verified that the full pipeline runs, populates the cache on the first run, and correctly reads from the cache on subsequent runs, preventing redundant API calls.
    
    ### Phase 4: Bugfix - Transit Data Extraction (In Progress)
    *   **Problem**: Despite multiple attempts at prompt engineering and parser adjustments, the `transit_accessibility` fields (subways, buses, stations) are not being populated in the final Markdown output.
    *   **Diagnosis**: The `wikipedia_parser.py` file has been corrupted through a series of failed `replace` operations, leading to a silent crash in the `parse` method before the transportation section is ever processed. The error logs about not finding the section were a symptom of this deeper structural problem.
    *   **Next Up**: **T012**: Run the script with debug logging to confirm the reconstructed parser works correctly.
    - [x] T011 Re-implement `wikipedia_parser.py` with the correct structure and all necessary helper methods (`_get_section_text`, `_parse_infobox`, `_clean_infobox_value`, `_extract_adjacent_neighborhoods`).
    - [ ] T012 Run the script with `--force-regenerate` and `--log-level DEBUG` to confirm the parser no longer crashes and that `transportation_text` is correctly passed to the LLM.
    - [ ] T013 Verify that the final `Astoria_Queens.md` output file now contains the correct transit information.
