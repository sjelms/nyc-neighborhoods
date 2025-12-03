# Tasks: LLM Pipeline Fix & Refactor

**Source Plan**: [plan.md](plan.md)

---

This task list is generated based on the implementation plan. Tasks are organized into phases.

## Phase 1: Diagnosis & Immediate Bug Fix

- [ ] T001 Run script with `--log-level DEBUG` to capture the raw LLM response for analysis.
- [ ] T002 Analyze debug logs and modify `src/services/llm_helper.py` to correctly parse the LLM response into a valid JSON object.

## Phase 2: Architectural Refactoring

- [ ] T003 Create cache subdirectories: `cache/html/` and `cache/llm/`.
- [ ] T004 [P] Refactor `src/lib/cache_manager.py` to support descriptive filenames and save to specified subdirectories instead of using hashes.
- [ ] T005 [P] Update `src/services/web_fetcher.py` to use the refactored `CacheManager` for caching HTML content with descriptive names.
- [ ] T006 [P] Modify `src/lib/generation_log.py` to add the `llm_cache_path` field to the log entry data structure.
- [ ] T007 Modify `src/services/llm_helper.py` to save successfully parsed LLM responses to the `cache/llm/` directory with a descriptive, timestamped filename.
- [ ] T008 Modify `src/services/profile_generator.py` and `src/services/llm_helper.py` to orchestrate the new caching workflow, ensuring the LLM cache is checked before making a live API call.

## Phase 3: Verification

- [ ] T009 Verify the full pipeline by running with `--force-regenerate` and confirming that enriched profiles are created and all caching/logging mechanisms work as designed.
- [ ] T010 Verify the LLM cache hits by re-running the script *without* `--force-regenerate` and confirming in the logs that no new API calls are made.
