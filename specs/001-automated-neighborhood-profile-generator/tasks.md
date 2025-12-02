---

description: "Task list for Automated Neighborhood Profile Generator feature implementation"
---

# Tasks: Automated Neighborhood Profile Generator

**Input**: Design documents from `/specs/001-automated-neighborhood-profile-generator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directories: `src/models/`, `src/services/`, `src/cli/`, `src/lib/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, `/input`, `/output`, `/logs`, `/cache`
- [x] T002 [P] Create `src/__init__.py` to make `src` a Python package
- [x] T003 [P] Configure `pytest.ini` at the root for test discovery and markers, including `pytest-cov` and `pytest-mock` (From research.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Define Pydantic models for data structures in `src/models/neighborhood_profile.py` based on `data-model.md` (`NeighborhoodProfile`, `KeyDetails`, `NeighborhoodFacts`, `Boundaries`, `TransitAccessibility`, `CommuteTime`)
- [x] T005 Implement a CSV parser in `src/lib/csv_parser.py` to read `neighborhood-borough.csv`, handling `Neighborhood` and `Borough` columns, and validating input.
- [x] T006 Implement a Markdown template renderer in `src/lib/template_renderer.py` for `output-template.md`.
- [x] T007 Set up basic logging configuration in `src/lib/logger.py`.

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Generate a Single Neighborhood Profile (Priority: P1) 🎯 MVP

**Goal**: Provide a single neighborhood name and its borough, and have the system generate a standardized Markdown profile for it, including basic facts, transit, and key details, sourced from Wikipedia and NYC Open Data.

**Independent Test**: Can be fully tested by providing a CSV with one neighborhood and verifying the creation and content of a single `.md` file in the output directory.

### Tests for User Story 1

- [x] T008 [P] [US1] Write unit tests for `neighborhood_profile.py` Pydantic models in `tests/unit/test_models.py`.
- [x] T009 [P] [US1] Write unit tests for `csv_parser.py` in `tests/unit/test_csv_parser.py`.
- [x] T010 [P] [US1] Write unit tests for `template_renderer.py` in `tests/unit/test_template_renderer.py`.

### Implementation for User Story 1

- [x] T011 [US1] Implement `web_fetcher.py` in `src/services/web_fetcher.py` to fetch Wikipedia content using `requests`.
- [x] T012 [US1] Implement `wikipedia_parser.py` in `src/services/wikipedia_parser.py` to extract data from Wikipedia HTML using `BeautifulSoup`.
- [x] T013 [US1] Implement `data_normalizer.py` in `src/services/data_normalizer.py` to convert raw parsed data into `NeighborhoodProfile` model.
- [x] T014 [US1] Implement `profile_generator.py` in `src/services/profile_generator.py` to orchestrate data fetching, parsing, normalization, and rendering for a single profile.
- [x] T015 [US1] Write integration test for single profile generation (from CSV to Markdown output) in `tests/integration/test_single_profile.py`.
- [x] T016 [US1] Implement CLI command for single profile generation in `src/cli/main.py` using `typer`, handling input CSV path, output directory, and version metadata.

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Generate Multiple Neighborhood Profiles (Priority: P2)

**Goal**: Provide a CSV file containing multiple neighborhood names and their boroughs, and have the system generate a standardized Markdown profile for each, handling errors gracefully for individual profiles.

**Independent Test**: Can be fully tested by providing a CSV with multiple neighborhoods and verifying that a corresponding `.md` file is created for each valid entry, and that error logging occurs for any failed entries, without stopping the process for other neighborhoods.

### Implementation for User Story 2

- [x] T017 [US2] Modify `profile_generator.py` to handle processing multiple profiles from a list of neighborhoods, ensuring graceful error handling.
- [x] T018 [US2] Update CLI command in `src/cli/main.py` to support batch processing and error reporting for multiple profiles.
- [x] T019 [US2] Write integration test for multiple profile generation with error handling in `tests/integration/test_batch_profile.py`.

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T020 [P] Implement caching mechanism for fetched web content in `src/lib/cache_manager.py` within the `/cache` directory.
- [x] T021 [P] Implement NYC Open Data API fetching and parsing in `src/services/nyc_open_data_fetcher.py` and `src/services/nyc_open_data_parser.py`.
- [x] T022 [P] Integrate NYC Open Data fetching/parsing into `data_normalizer.py` for supplementing/cross-validating.
- [x] T023 [P] Refactor code for maintainability and extensibility across the project.
- [x] T024 [P] Review and enhance logging for better traceability (source URLs, warnings, errors) throughout the application.
- [x] T025 [P] Update `README.md` and `quickstart.md` with comprehensive usage instructions for the implemented CLI.

---

## Phase 6: Generation Log Implementation

**Purpose**: Add a JSON log to track generated profiles and support incremental updates.

- [x] T026 Implement `generation_log.py` in `src/lib/` to manage reading, writing, and querying the JSON log file.
- [x] T027 Update `NeighborhoodProfile` model in `src/models/neighborhood_profile.py` to include a unique identifier (e.g., a combination of neighborhood and borough).
- [x] T028 Update `ProfileGenerator` in `src/services/profile_generator.py` to interact with `generation_log.py`, check for existing records, and log new ones.
- [x] T029 Update `main.py` in `src/cli/` to add new CLI flags (`--force-regenerate`, `--update-since`, `--log-file`) and logic for record management.
- [x] T030 Write integration tests for generation log functionality in `tests/integration/test_generation_log.py`.

---

## Phase 7: Pytest Troubleshooting

**Purpose**: Resolve errors encountered during test execution.

- [ ] T031 Fix the `SyntaxError: unterminated triple-quoted string literal` in `src/services/wikipedia_parser.py`.
- [ ] T032 Fix the `AttributeError: module 'pytest' has no attribute 'pytest'` in `tests/unit/test_template_renderer.py`.
- [ ] T033 Run tests to confirm all errors are resolved.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete (P1 and P2)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on User Story 1 for core profile generation logic.

### Within Each User Story

- Tests MUST be written and FAIL before implementation.
- Models before services.
- Services before CLI integration.
- Core implementation before integration.
- Story complete before moving to next priority.

### Parallel Opportunities

- All Setup tasks (T001-T003) can run in parallel where marked [P].
- Unit tests within a user story can run in parallel (T008-T010).
- Different development streams can work on different services/parsers once core models and libraries are stable.
- Polish tasks (T020-T025) are largely independent and can be parallelized.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2 (assuming US1 core logic is stable enough to build upon)
   - Developer C: Works on Polish tasks (e.g., caching, Open Data integration)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
