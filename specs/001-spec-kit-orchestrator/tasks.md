# Tasks: Spec Kit Orchestrator

**Input**: Design documents from `/specs/001-spec-kit-orchestrator/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Unit tests and smoke tests included as requested.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow plan.md structure: `src/orchestrator/` for main package

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan in `src/orchestrator/` with subdirectories: `pages/`, `services/`, `models/`, `utils/`
- [ ] T002 Create `requirements.txt` with dependencies: streamlit, pyyaml, python-dotenv, gitpython (optional), pytest, pytest-mock
- [ ] T003 [P] Create `README.md` with project description, setup instructions, and local run documentation
- [ ] T004 [P] Create `src/orchestrator/__init__.py` and `src/orchestrator/pages/__init__.py` and `src/orchestrator/services/__init__.py` and `src/orchestrator/models/__init__.py` and `src/orchestrator/utils/__init__.py`
- [ ] T005 [P] Create `tests/` directory structure: `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- [ ] T006 [P] Create `pytest.ini` configuration file for test discovery
- [ ] T007 Create `.specify/orchestrator/` directory structure for config and runs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create `src/orchestrator/utils/path_validation.py` with path allowlist validation and directory traversal prevention
- [ ] T009 [P] Create `src/orchestrator/utils/secret_masker.py` with secret masking logic for logs and UI displays
- [ ] T010 [P] Create `src/orchestrator/utils/yaml_parser.py` with YAML parsing and generation utilities
- [ ] T011 Create `src/orchestrator/services/config_manager.py` to load admin configuration from `.specify/orchestrator/config.yml`
- [ ] T012 Create `src/orchestrator/services/cli_executor.py` with CLI execution wrapper that streams stdout/stderr and captures exit codes
- [ ] T013 Create `src/orchestrator/services/run_metadata.py` to create and manage execution metadata JSON files in `.specify/orchestrator/runs/<timestamp>/`
- [ ] T014 Create `src/orchestrator/models/project.py` with Project entity dataclass
- [ ] T015 [P] Create `src/orchestrator/models/phase_execution.py` with PhaseExecution entity dataclass
- [ ] T016 [P] Create `src/orchestrator/models/artifact.py` with Artifact entity dataclass
- [ ] T017 [P] Create `src/orchestrator/models/workspace_config.py` with WorkspaceConfiguration entity dataclass
- [ ] T018 Create `src/orchestrator/app.py` as main Streamlit app entry point with basic navigation setup

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create and Initialize Spec Kit Project (Priority: P1) 🎯 MVP

**Goal**: Enable users to create new Spec Kit projects through a web UI with real-time output streaming

**Independent Test**: Create a new project through the UI, verify `specify init` runs successfully, confirm `.specify/` directory structure is created in expected location

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T019 [P] [US1] Unit test for path validation in `tests/unit/test_path_validation.py` (valid paths, directory traversal attempts, allowlist checking)
- [ ] T020 [P] [US1] Unit test for CLI executor in `tests/unit/test_cli_executor.py` (command execution, output streaming, exit code capture)
- [ ] T021 [P] [US1] Integration test for project creation flow in `tests/integration/test_project_creation_flow.py` (end-to-end: form submission → CLI execution → project initialization)

### Implementation for User Story 1

- [ ] T022 [US1] Implement project creation form UI in `src/orchestrator/pages/project_creation.py` with fields: project name, parent directory, AI agent dropdown, optional GitHub token, extra params
- [ ] T023 [US1] Add path validation to project creation form using `src/orchestrator/utils/path_validation.py` (validate against admin-configured base directory, prevent directory traversal)
- [ ] T024 [US1] Add AI agent value validation in `src/orchestrator/pages/project_creation.py` (check against admin-configured allowed values)
- [ ] T025 [US1] Implement `specify init` command execution in `src/orchestrator/pages/project_creation.py` using `src/orchestrator/services/cli_executor.py`
- [ ] T026 [US1] Implement real-time output streaming in `src/orchestrator/pages/project_creation.py` using Streamlit's `st.empty()` container with incremental updates
- [ ] T027 [US1] Add error handling in `src/orchestrator/pages/project_creation.py` for CLI not found, permission errors, invalid paths, command failures with user-friendly messages
- [ ] T028 [US1] Create execution metadata record in `src/orchestrator/pages/project_creation.py` using `src/orchestrator/services/run_metadata.py` after `specify init` completes
- [ ] T029 [US1] Add success/failure UI feedback in `src/orchestrator/pages/project_creation.py` (success message with project link, error display with retry option)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can create new Spec Kit projects through the UI.

---

## Phase 4: User Story 3 - Run Spec Kit Phases from UI with Streaming Output (Priority: P1)

**Goal**: Enable users to execute Spec Kit phases (Constitution, Specify, Clarify, Plan, Tasks, Analyze) directly from the web UI with real-time output streaming and execution metadata recording

**Independent Test**: Run each phase individually from the UI, verify command output streams in real-time, artifacts are generated in expected locations, execution metadata is recorded in `.specify/orchestrator/runs/<timestamp>/`

### Tests for User Story 3

- [ ] T030 [P] [US3] Unit test for run metadata generation in `tests/unit/test_run_metadata.py` (metadata JSON structure, timestamp formatting, log file paths)
- [ ] T031 [P] [US3] Unit test for phase dependency checking in `tests/unit/test_phase_dependencies.py` (detect missing artifacts, warn on out-of-order execution)
- [ ] T032 [P] [US3] Integration test for phase execution flow in `tests/integration/test_phase_execution_flow.py` (end-to-end: button click → command execution → artifact generation → metadata recording)

### Implementation for User Story 3

- [ ] T033 [US3] Implement phase runner UI page in `src/orchestrator/pages/phase_runner.py` with buttons for Constitution, Specify, Clarify, Plan, Tasks, Analyze phases
- [ ] T034 [US3] Add phase status indicators in `src/orchestrator/pages/phase_runner.py` (not started / in progress / completed / failed) for each phase
- [ ] T035 [US3] Implement phase dependency checking in `src/orchestrator/pages/phase_runner.py` (check required artifacts exist, warn if running out of order)
- [ ] T036 [US3] Add confirmation dialog in `src/orchestrator/pages/phase_runner.py` when user attempts to run phase out of order (warn but allow if confirmed)
- [ ] T037 [US3] Implement phase command execution in `src/orchestrator/pages/phase_runner.py` using `src/orchestrator/services/cli_executor.py` for each phase
- [ ] T038 [US3] Implement real-time output streaming in `src/orchestrator/pages/phase_runner.py` for phase execution (stream stdout/stderr to UI)
- [ ] T039 [US3] Create execution metadata record in `src/orchestrator/pages/phase_runner.py` using `src/orchestrator/services/run_metadata.py` after each phase completes
- [ ] T040 [US3] Add artifact linking in `src/orchestrator/pages/phase_runner.py` (show links to generated artifacts after successful execution)
- [ ] T041 [US3] Implement rerun capability in `src/orchestrator/pages/phase_runner.py` (create new execution record with new timestamp, preserve previous history)
- [ ] T042 [US3] Add error handling in `src/orchestrator/pages/phase_runner.py` (highlight errors in UI, preserve error output in execution log, allow retry)
- [ ] T043 [US3] Disable Analyze button until Tasks completes in `src/orchestrator/pages/phase_runner.py` (enforce phase ordering)

**Checkpoint**: At this point, User Stories 1 AND 3 should both work independently. Users can create projects and run Spec Kit phases from the UI.

---

## Phase 5: User Story 2 - Generate Phase Parameters via Interview Chat (Priority: P2)

**Goal**: Enable users to generate Spec Kit command parameter documents through an AI chat interface that interviews them about their project/feature

**Independent Test**: Initialize a project, engage with the interview chat, verify parameter documents are created in `docs/spec-kit-parameters.md` and `docs/spec-kit-parameters.yml` with copy/paste blocks for each Spec Kit phase

### Tests for User Story 2

- [ ] T044 [P] [US2] Unit test for parameter document generation in `tests/unit/test_parameter_generator.py` (Markdown format, YAML format, backup creation)
- [ ] T045 [P] [US2] Integration test for interview chat flow in `tests/integration/test_interview_chat_flow.py` (end-to-end: chat interaction → document generation → file creation)

### Implementation for User Story 2

- [ ] T046 [US2] Implement interview chat UI in `src/orchestrator/pages/interview_chat.py` using Streamlit chat components (`st.chat_message()`)
- [ ] T047 [US2] Create parameter document generator service in `src/orchestrator/services/parameter_generator.py` to generate both Markdown and YAML formats
- [ ] T048 [US2] Implement backup creation in `src/orchestrator/services/parameter_generator.py` (create timestamped backup before overwriting existing documents)
- [ ] T049 [US2] Add parameter document validation in `src/orchestrator/services/parameter_generator.py` (ensure all phases included, validate YAML structure)
- [ ] T050 [US2] Integrate parameter generator with interview chat in `src/orchestrator/pages/interview_chat.py` (generate documents after chat completion)
- [ ] T051 [US2] Add document preview in `src/orchestrator/pages/interview_chat.py` (show generated documents in expandable sections)
- [ ] T052 [US2] Add regeneration capability in `src/orchestrator/pages/interview_chat.py` (allow user to regenerate parameters if needed)

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently. Users can create projects, generate parameters, and run phases.

---

## Phase 6: User Story 4 - Browse and Review Generated Artifacts (Priority: P2)

**Goal**: Enable users to review artifacts generated by Spec Kit phases and execution logs without leaving the web UI

**Independent Test**: Run at least one phase, navigate to artifact browser, verify artifacts are listed, can be viewed with proper Markdown rendering, execution logs are accessible

### Tests for User Story 4

- [ ] T053 [P] [US4] Unit test for artifact discovery in `tests/unit/test_artifact_reader.py` (discover artifacts in predictable locations, handle missing artifacts)
- [ ] T054 [P] [US4] Integration test for artifact browsing flow in `tests/integration/test_artifact_browsing.py` (end-to-end: artifact discovery → rendering → navigation)

### Implementation for User Story 4

- [ ] T055 [US4] Create artifact reader service in `src/orchestrator/services/artifact_reader.py` to discover artifacts in predictable locations (`.specify/memory/constitution.md`, `specs/*/spec.md`, etc.)
- [ ] T056 [US4] Implement artifact browser UI page in `src/orchestrator/pages/artifact_browser.py` with artifact list (type, name, timestamp, status)
- [ ] T057 [US4] Add Markdown rendering in `src/orchestrator/pages/artifact_browser.py` using Streamlit's `st.markdown()` with proper formatting and syntax highlighting
- [ ] T058 [US4] Implement artifact navigation in `src/orchestrator/pages/artifact_browser.py` (links between related artifacts: spec → plan → tasks)
- [ ] T059 [US4] Add execution log viewer in `src/orchestrator/pages/artifact_browser.py` (display chronological list of phase executions with timestamps, status, links to detailed logs)
- [ ] T060 [US4] Add "not generated yet" messaging in `src/orchestrator/pages/artifact_browser.py` (clear message for missing artifacts, suggest which phase needs to be run)
- [ ] T061 [US4] Implement log file reading in `src/orchestrator/services/artifact_reader.py` (read stdout/stderr logs from execution metadata directories)

**Checkpoint**: At this point, User Stories 1, 2, 3, AND 4 should all work independently. Users can create projects, generate parameters, run phases, and browse artifacts.

---

## Phase 7: User Story 5 - Discover and Select Existing Projects (Priority: P2)

**Goal**: Enable users to discover and work with existing Spec Kit projects by browsing a configured workspace directory

**Independent Test**: Configure a base workspace directory containing multiple folders with `.specify/` directories, verify UI lists these projects and allows selection

### Tests for User Story 5

- [ ] T062 [P] [US5] Unit test for project discovery in `tests/unit/test_project_discovery.py` (scan workspace, identify `.specify/` directories, exclude invalid folders)
- [ ] T063 [P] [US5] Integration test for project selection flow in `tests/integration/test_project_selection_flow.py` (end-to-end: discovery → selection → project context loading)

### Implementation for User Story 5

- [ ] T064 [US5] Implement project discovery service in `src/orchestrator/services/project_discovery.py` to scan admin-configured base workspace directory for folders containing `.specify/` directories
- [ ] T065 [US5] Create project selection UI page in `src/orchestrator/pages/project_selection.py` with project list (name, path, last modified timestamp)
- [ ] T066 [US5] Add project selection handling in `src/orchestrator/pages/project_selection.py` (load project context, display current state: phases run, artifact status)
- [ ] T067 [US5] Implement project validation in `src/orchestrator/services/project_discovery.py` (check project still exists, refresh list if moved/deleted)
- [ ] T068 [US5] Add project state loading in `src/orchestrator/services/project_discovery.py` (determine which phases have been run, artifact status)
- [ ] T069 [US5] Integrate project selection with main app navigation in `src/orchestrator/app.py` (set selected project in session state, navigate to project-specific pages)

**Checkpoint**: At this point, all User Stories (1-5) should work independently. Users can discover projects, create new ones, generate parameters, run phases, and browse artifacts.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T070 [P] Create admin configuration template file `.specify/orchestrator/config.yml.example` with example configuration
- [ ] T071 [P] Add comprehensive error messages throughout all UI pages (user-friendly, actionable, non-technical language)
- [ ] T072 [P] Implement git commit hash extraction in `src/orchestrator/services/run_metadata.py` using gitpython (optional, if git repo)
- [ ] T073 [P] Add inputs hash calculation in `src/orchestrator/services/run_metadata.py` for Option 3 staleness detection readiness (SHA256 hash of inputs)
- [ ] T074 [P] Add secret masking in all log outputs using `src/orchestrator/utils/secret_masker.py` (mask GitHub tokens, API keys in stdout/stderr logs)
- [ ] T075 [P] Create smoke test checklist in `docs/smoke-test-checklist.md` for running init + one phase end-to-end
- [ ] T076 [P] Add documentation updates in `README.md` (usage examples, configuration guide, troubleshooting)
- [ ] T077 Code cleanup and refactoring (remove duplicate code, improve error handling consistency)
- [ ] T078 Performance optimization (ensure streaming doesn't block UI, optimize project discovery for large workspaces)
- [ ] T079 Security hardening (review all path operations, validate all user inputs, audit secret handling)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed) OR sequentially in priority order (P1 → P2)
  - Recommended order: US1 (P1) → US3 (P1) → US2 (P2) → US4 (P2) → US5 (P2)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Depends on US1 for project creation, but can be tested independently with existing projects
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 for project initialization, but can be tested independently
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Depends on US3 for artifact generation, but can be tested independently with existing artifacts
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - Independent, can work with any existing projects

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Services before UI pages
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003-T007)
- All Foundational tasks marked [P] can run in parallel (T009-T010, T015-T017)
- Once Foundational phase completes, user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Services within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for path validation in tests/unit/test_path_validation.py"
Task: "Unit test for CLI executor in tests/unit/test_cli_executor.py"
Task: "Integration test for project creation flow in tests/integration/test_project_creation_flow.py"

# Launch foundational services in parallel (if not already done):
Task: "Create path validation utility in src/orchestrator/utils/path_validation.py"
Task: "Create CLI executor service in src/orchestrator/services/cli_executor.py"
Task: "Create run metadata service in src/orchestrator/services/run_metadata.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Create Projects)
4. Complete Phase 4: User Story 3 (Run Phases)
5. **STOP and VALIDATE**: Test User Stories 1 and 3 independently
6. Deploy/demo if ready

**MVP delivers**: Users can create Spec Kit projects and run phases from the UI - core value proposition.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Basic MVP)
3. Add User Story 3 → Test independently → Deploy/Demo (Full MVP)
4. Add User Story 2 → Test independently → Deploy/Demo (Parameter Generation)
5. Add User Story 4 → Test independently → Deploy/Demo (Artifact Review)
6. Add User Story 5 → Test independently → Deploy/Demo (Multi-Project Support)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Project Creation)
   - Developer B: User Story 3 (Phase Runner) - can work with existing projects
   - Developer C: User Story 2 (Parameter Generation) - can work after US1
3. Stories complete and integrate independently
4. Developer D: User Stories 4 and 5 (Artifact Browser, Project Discovery)

---

## Milestone Acceptance Criteria

### M0: Project Discovery + Artifact Browser
**Acceptance**: 
- ✅ User can see list of projects in workspace directory
- ✅ User can select a project and load its context
- ✅ User can view artifacts (if they exist) with proper Markdown rendering
- ✅ User can view execution logs

**Tasks**: T055-T061 (US4), T064-T069 (US5)

### M1: Init Wizard + Streaming Logs
**Acceptance**:
- ✅ User can create new project through UI form
- ✅ Output streams in real-time (<2s latency for 95% of lines)
- ✅ Errors displayed clearly with user-friendly messages
- ✅ Execution metadata recorded
- ✅ Project successfully initialized with `.specify/` directory

**Tasks**: T022-T029 (US1)

### M2: Parameter Doc Generation
**Acceptance**:
- ✅ User can generate parameter documents through interview chat (or template form)
- ✅ Both Markdown and YAML formats created
- ✅ Backups created before overwrite
- ✅ Documents contain all required phases (Constitution, Specify, Clarify, Plan, Tasks, Analyze)

**Tasks**: T046-T052 (US2)

### M3: Phase Runner Buttons + Run Metadata
**Acceptance**:
- ✅ User can run all phases from UI buttons
- ✅ Output streams in real-time
- ✅ Execution metadata recorded completely (phase name, command, args, cwd, env vars, timestamps, exit code, log paths, git commit hash, inputs hash)
- ✅ Phase dependencies enforced (warnings for out-of-order execution)
- ✅ Execution history accessible
- ✅ Artifacts linked after successful execution

**Tasks**: T033-T043 (US3)

### M4: Option 3 Staleness Pipeline View (Post-v1)
**Acceptance**: Deferred to post-v1

---

## Smoke Test Checklist

**Purpose**: Validate end-to-end functionality after implementation

**Location**: `docs/smoke-test-checklist.md`

**Steps**:
1. [ ] Start Streamlit app: `streamlit run src/orchestrator/app.py`
2. [ ] Navigate to "New Project" page
3. [ ] Create new project:
   - Enter project name
   - Select parent directory (within allowed base)
   - Select AI agent from dropdown
   - Click "Create Project"
4. [ ] Verify:
   - [ ] Output streams in real-time
   - [ ] Success message displayed
   - [ ] `.specify/` directory created
   - [ ] Execution metadata recorded in `.specify/orchestrator/runs/`
5. [ ] Navigate to "Phase Runner" page
6. [ ] Run Constitution phase:
   - [ ] Click "Run Constitution" button
   - [ ] Verify output streams in real-time
   - [ ] Verify execution metadata recorded
   - [ ] Verify artifact generated (`.specify/memory/constitution.md`)
7. [ ] Navigate to "Artifacts" page
8. [ ] Verify:
   - [ ] Constitution artifact listed
   - [ ] Artifact can be viewed with proper Markdown rendering
   - [ ] Execution log accessible

**Expected Result**: All steps complete successfully, demonstrating core workflow functionality.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Total tasks: 79 (T001-T079)
- Tasks by story: US1 (10 tasks), US2 (7 tasks), US3 (14 tasks), US4 (7 tasks), US5 (6 tasks), Setup (7 tasks), Foundational (11 tasks), Polish (10 tasks), Tests (8 tasks)

