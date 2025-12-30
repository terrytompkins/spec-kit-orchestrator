# Feature Specification: Spec Kit Orchestrator

**Feature Branch**: `001-spec-kit-orchestrator`  
**Created**: 2025-12-29  
**Status**: Draft  
**Input**: User description: "Create a product/feature specification for Spec Kit Orchestrator, a Streamlit web app that orchestrates GitHub Spec Kit workflows for non-technical users."

## Clarifications

### Session 2025-12-29

- Q: What is the execution environment for the Streamlit app - local machine only, shared server, or hybrid? → A: Local machine only (v1). Each user runs the app on their own machine. No multi-user concerns, simpler permissions, no sandboxing needed.

- Q: Where do the allowed values for `specify init --ai` come from? → A: Admin-configured list. Administrator configures allowed values in workspace settings. Flexible, aligns with FR-014, and allows restriction to approved AI providers without hardcoding.

- Q: What is the lifecycle of the parameter document - overwrite or versioned? → A: Overwrite with backup. Always overwrite `docs/spec-kit-parameters.md`, but create a timestamped backup (e.g., `docs/spec-kit-parameters.2025-12-29-143022.md`) before overwriting. Simple, single source of truth, with safety net.

- Q: Does the interview chat generate only copy/paste blocks or also structured machine-readable data? → A: Both formats. Always generate both `docs/spec-kit-parameters.md` (human-readable copy/paste) and `docs/spec-kit-parameters.yml` (machine-readable) with the same content. Supports both human use and automation for Option 2/3 features.

- Q: Is GitHub PR creation required in v1 or deferred? → A: Deferred to post-v1. v1 focuses on CLI orchestration only. GitHub token is optional for `specify init` if Spec Kit requires it, but no PR creation functionality. Users export files or manually create PRs. PR creation adds GitHub API integration complexity that can be added later.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Initialize Spec Kit Project (Priority: P1)

A product manager wants to start a new Spec Kit project without using an IDE or terminal. They access the Streamlit web application, provide project details through a guided form, and the system initializes the project by running the Spec Kit CLI.

**Why this priority**: This is the foundational capability that enables all other workflows. Without project creation, users cannot proceed with any Spec Kit operations. It establishes the core value proposition of enabling non-technical users to work with Spec Kit.

**Independent Test**: Can be fully tested by creating a new project through the UI, verifying that `specify init` runs successfully, and confirming that the `.specify/` directory structure is created in the expected location. This delivers immediate value by enabling project setup without technical prerequisites.

**Acceptance Scenarios**:

1. **Given** the user is on the project creation page, **When** they provide a valid project name, parent directory, AI agent option, and optional GitHub token, **Then** the system runs `specify init` with the provided parameters and streams the output to the UI, and the project is successfully initialized with a `.specify/` directory.

2. **Given** the user provides an invalid directory path, **When** they attempt to create a project, **Then** the system displays a clear error message explaining the issue and prevents directory traversal attacks.

3. **Given** the Spec Kit CLI is not installed, **When** the user attempts to create a project, **Then** the system displays a user-friendly error message with instructions on how to install the CLI.

4. **Given** the `specify init` command fails (e.g., permission error, disk full), **When** the command executes, **Then** the system captures and displays the error output (stderr) in a user-friendly format, and no partial project state is left behind.

---

### User Story 2 - Generate Phase Parameters via Interview Chat (Priority: P2)

After successfully initializing a project, a business analyst needs to define what they want to build. They engage with an AI chat interface that interviews them about their project or feature, and the system generates a Spec Kit command parameter document that can be used to run Spec Kit phases.

**Why this priority**: This enables users to define their requirements without needing to understand Spec Kit command syntax. It bridges the gap between business needs and technical execution, making the tool accessible to non-technical users.

**Independent Test**: Can be fully tested by initializing a project, engaging with the interview chat, and verifying that a parameter document is created in `docs/spec-kit-parameters.md` with copy/paste blocks for each Spec Kit phase. This delivers value by automating the creation of phase parameters that would otherwise require technical knowledge.

**Acceptance Scenarios**:

1. **Given** a project has been successfully initialized, **When** the user engages with the interview chat and answers questions about their feature, **Then** the system generates complete parameter documents in both `docs/spec-kit-parameters.md` (containing copy/paste blocks for Constitution, Specify, Clarify, Plan, Tasks, and Analyze phases) and `docs/spec-kit-parameters.yml` (containing the same content in machine-readable YAML format).

2. **Given** the user provides incomplete or ambiguous answers during the interview, **When** the chat generates parameters, **Then** the system flags unclear areas with placeholders or requests clarification before finalizing the document.

3. **Given** a parameter document already exists, **When** the user runs the interview chat again, **Then** the system creates a timestamped backup of the existing document (e.g., `docs/spec-kit-parameters.2025-12-29-143022.md`) and then overwrites `docs/spec-kit-parameters.md` with the new content, clearly indicating that a backup was created.

---

### User Story 3 - Run Spec Kit Phases from UI with Streaming Output (Priority: P1)

A product manager wants to execute Spec Kit phases (Constitution, Specify, Clarify, Plan, Tasks, Analyze) directly from the web UI without using a terminal. They click buttons to run phases, see real-time output streaming, and the system records execution metadata for auditability.

**Why this priority**: This is the core execution capability that enables users to generate Spec Kit artifacts. Without this, users would still need to use the terminal, defeating the purpose of the orchestrator. This story delivers the primary value of making Spec Kit accessible to non-technical users.

**Independent Test**: Can be fully tested by running each phase individually from the UI, verifying that command output streams in real-time, artifacts are generated in expected locations, and execution metadata is recorded in `.specify/orchestrator/runs/<timestamp>/`. This delivers immediate value by enabling artifact generation without terminal access.

**Acceptance Scenarios**:

1. **Given** a project is initialized and parameter documents exist, **When** the user clicks the "Run Constitution" button, **Then** the system executes the Spec Kit constitution command, streams stdout/stderr output in real-time to the UI, generates the constitution artifact, and records execution metadata including command, parameters, timestamps, exit code, and output logs.

2. **Given** the user runs phases in the correct order (Constitution → Specify → Clarify → Plan → Tasks → Analyze), **When** each phase completes, **Then** the system enables the next phase button and shows the status of each phase (not started / in progress / completed / failed).

3. **Given** the user attempts to run a phase out of order (e.g., Plan before Specify), **When** they click the phase button, **Then** the system displays a warning message explaining the recommended order but allows the operation to proceed if the user confirms.

4. **Given** a phase execution fails (non-zero exit code), **When** the command completes, **Then** the system clearly highlights the error in the UI, preserves the error output in the execution log, and allows the user to review and retry the operation.

5. **Given** the user reruns a previously completed phase, **When** the phase executes again, **Then** the system creates a new execution record with a new timestamp, preserving the previous execution history for auditability.

---

### User Story 4 - Browse and Review Generated Artifacts (Priority: P2)

A business analyst wants to review the artifacts generated by Spec Kit phases (constitution, specs, clarifications, plan, tasks, analysis output) and execution logs without leaving the web UI or opening files in an IDE.

**Why this priority**: Enables users to review and validate the outputs of Spec Kit phases, which is essential for quality assurance and handoff to engineering teams (via exported files or manual PR creation; automated PR creation deferred to post-v1). While less critical than execution, artifact review is necessary for a complete workflow.

**Independent Test**: Can be fully tested by running at least one phase, then navigating to the artifact browser and verifying that generated artifacts are listed, can be viewed with proper Markdown rendering, and execution logs are accessible. This delivers value by enabling artifact review without requiring file system access or IDE knowledge.

**Acceptance Scenarios**:

1. **Given** at least one Spec Kit phase has been executed, **When** the user navigates to the artifact browser, **Then** the system displays a list of available artifacts (constitution, specs, clarifications, plan, tasks, analysis output) with their generation timestamps and status indicators.

2. **Given** the user selects an artifact to view, **When** they click on it, **Then** the system renders the Markdown content in a readable format with proper formatting, syntax highlighting for code blocks, and navigation between related artifacts.

3. **Given** the user wants to review execution history, **When** they navigate to the run logs section, **Then** the system displays a chronological list of all phase executions with timestamps, phase names, status (success/failure), and links to detailed logs.

4. **Given** an artifact file does not exist (e.g., phase not run yet), **When** the user attempts to view it, **Then** the system displays a clear message indicating the artifact has not been generated yet and suggests which phase needs to be run.

---

### User Story 5 - Discover and Select Existing Projects (Priority: P2)

An administrator or returning user wants to work with an existing Spec Kit project. They need to discover projects by browsing a configured workspace directory and select a project to work with.

**Why this priority**: Enables users to work with multiple projects and return to previously created projects. While not required for the initial MVP, this capability is essential for practical day-to-day use of the tool.

**Independent Test**: Can be fully tested by configuring a base workspace directory containing multiple folders with `.specify/` directories, then verifying that the UI lists these projects and allows selection. This delivers value by enabling multi-project workflows and project persistence.

**Acceptance Scenarios**:

1. **Given** a base workspace directory is configured and contains multiple folders with `.specify/` directories, **When** the user navigates to the project selection page, **Then** the system displays a list of discovered projects with their names, paths, and last modified timestamps.

2. **Given** the user selects a project from the list, **When** they confirm the selection, **Then** the system loads the project context and displays the project's current state (which phases have been run, artifact status, etc.).

3. **Given** a folder in the workspace directory does not contain a `.specify/` directory, **When** the system scans for projects, **Then** the folder is excluded from the project list.

4. **Given** the user attempts to access a project that no longer exists or has been moved, **When** they select it, **Then** the system displays an error message and refreshes the project list.

---

### Edge Cases

- **Init failures**: What happens when `specify init` fails due to permission errors, disk space issues, or invalid parameters? System must capture and display errors clearly, and not leave partial project state.

- **Invalid directory paths**: How does the system handle directory traversal attempts (e.g., `../../../etc/passwd`)? System must validate and restrict paths to allowed base directory.

- **Missing `.specify/` directory**: What happens when a user selects a project folder that doesn't contain `.specify/`? System must detect this and either initialize it or show an error.

- **CLI not installed**: What happens when the Spec Kit CLI (`specify` command) is not found in PATH? System must detect this and provide clear installation instructions.

- **Permission errors**: What happens when the user doesn't have read/write permissions for the project directory? System must display a clear error message explaining the permission issue.

- **Token missing or invalid**: What happens when a GitHub token is required but missing or invalid? System must handle this gracefully, either allowing the operation to proceed without GitHub integration or clearly indicating what functionality is unavailable.

- **Rerun behavior**: What happens when a user reruns a phase that has already been executed? System must create a new execution record, preserve previous history, and handle cases where artifacts are overwritten vs. versioned.

- **Concurrent execution**: What happens if a user attempts to run multiple phases simultaneously? For v1 (local machine execution per FR-019), concurrent execution is not a concern as only one user instance runs per machine. If shared server deployment is added post-v1, the system must either prevent concurrent execution or handle it safely with proper locking and state management.

- **Large output streams**: What happens when a phase generates very large output (e.g., thousands of lines)? System must handle streaming efficiently without blocking the UI or exhausting memory.

- **Network interruptions**: What happens if the user's connection is interrupted during a long-running phase execution? System should preserve partial execution logs and allow resumption or retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a web-based UI (Streamlit) that allows users to create new Spec Kit projects without using a terminal or IDE.

- **FR-002**: System MUST execute `specify init` command with user-provided parameters (project name, parent directory, AI agent option, optional GitHub token for Spec Kit initialization if required, optional extra parameters) and stream stdout/stderr output to the UI in real-time. Note: GitHub PR creation functionality is deferred to post-v1; v1 focuses on CLI orchestration only.

- **FR-003**: System MUST validate all user inputs before executing commands, including path validation to prevent directory traversal attacks and restriction to allowed base directories.

- **FR-004**: System MUST provide an AI chat interface that interviews users about their project/feature and generates Spec Kit command parameter documents in both formats: `docs/spec-kit-parameters.md` (human-readable copy/paste blocks) and `docs/spec-kit-parameters.yml` (machine-readable YAML with the same content for automation). Note: For v1, the interface may use a template-based form or guided questionnaire approach; full LLM-powered chat integration may be deferred to post-v1. The key requirement is generating both document formats regardless of the input method.

- **FR-005**: System MUST provide UI buttons to run each Spec Kit phase (Constitution, Specify, Clarify, Plan, Tasks, Analyze) with real-time output streaming.

- **FR-006**: System MUST record execution metadata for every phase run, including: command executed, all parameters, working directory, environment variables (non-secret), start/end timestamps, exit code, and output logs, stored in `.specify/orchestrator/runs/<timestamp>/` in structured format (JSON).

- **FR-007**: System MUST provide an artifact browser that lists and renders key artifacts (constitution, specs, clarifications, plan, tasks, analysis output) with proper Markdown formatting.

- **FR-008**: System MUST discover projects by scanning a configured base workspace directory for folders containing `.specify/` directories.

- **FR-009**: System MUST display execution history and run logs, allowing users to review previous phase executions with timestamps, status, and detailed logs.

- **FR-010**: System MUST handle errors gracefully, displaying user-friendly error messages for common failure scenarios (CLI not installed, permission errors, invalid paths, command failures).

- **FR-011**: System MUST warn users when attempting to run phases out of recommended order (e.g., Plan before Specify) while still allowing the operation if confirmed.

- **FR-012**: System MUST mask or redact secrets (GitHub tokens, API keys) in logs and UI displays while preserving them in environment variables for command execution.

- **FR-013**: System MUST support rerunning phases, creating new execution records for each run while preserving previous execution history.

- **FR-014**: System MUST allow administrators to configure: base workspace directory, allowed `--ai` values for `specify init` (as a list of valid options presented in the UI dropdown), and secrets handling mechanisms. The UI MUST validate user-selected AI agent values against the admin-configured list before executing `specify init`.

- **FR-015**: System MUST detect and handle cases where Spec Kit CLI is not installed, displaying clear installation instructions.

- **FR-016**: System MUST validate that required artifacts exist before allowing dependent phases to run (e.g., warn if Plan is run before Specify completes).

- **FR-017**: System MUST provide sensible defaults for all user inputs (e.g., default AI agent option, default project structure).

- **FR-018**: System MUST support Option 3 readiness features: model phase dependencies and staleness detection (warn if downstream artifacts are stale because upstream changed), and provide a pipeline view with statuses (not started / generated / stale / failed). **Architecture requirements for v1** (must be implemented to enable future Option 3 features): inputs hash calculation for each phase execution (SHA256 hash of command parameters and inputs), phase dependency modeling in data structures, and content hash storage for artifacts. **Full implementation deferred to post-v1**: pipeline view UI, staleness detection logic, and automatic staleness warnings. The architecture must be designed to support these features without requiring major refactoring.

- **FR-019**: System MUST be designed for local machine execution (v1). The Streamlit app runs on each user's local machine. No multi-user concurrency, sandboxing, or shared server permission management is required for v1.

### Key Entities *(include if feature involves data)*

- **Project**: Represents a Spec Kit project instance. Key attributes: project name, parent directory path, initialization timestamp, current phase status, associated artifacts, execution history. Relationships: has many Phase Executions, has many Artifacts.

- **Phase Execution**: Represents a single run of a Spec Kit phase. Key attributes: phase name (Constitution/Specify/Clarify/Plan/Tasks/Analyze), command executed, parameters used, working directory, start/end timestamps, exit code, status (success/failure/in-progress), output log paths, git commit hash (if available), inputs hash for staleness detection. Relationships: belongs to one Project.

- **Artifact**: Represents a generated Spec Kit artifact file. Key attributes: artifact type (constitution/spec/clarification/plan/tasks/analysis), file path, generation timestamp, associated phase execution, content hash for staleness detection. Relationships: belongs to one Project, generated by one Phase Execution.

- **Parameter Document**: Represents the Spec Kit command parameter documents generated by the interview chat. Key attributes: markdown file path (`docs/spec-kit-parameters.md`), YAML file path (`docs/spec-kit-parameters.yml`), generation timestamp, content (copy/paste blocks in Markdown, structured data in YAML for each phase). Both formats contain the same content - Markdown for human copy/paste, YAML for machine-readable automation. Lifecycle: when regenerated, both existing documents are backed up with timestamp suffix before overwriting. Relationships: belongs to one Project.

- **Workspace Configuration**: Represents administrator-configured settings. Key attributes: base workspace directory path, allowed AI agent values, secrets storage mechanism, path allowlist rules. Relationships: applies to all Projects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Non-technical users (PMs/BAs) can create a new Spec Kit project and run at least one phase (Constitution) successfully without using a terminal or IDE, with 90% success rate on first attempt.

- **SC-002**: Users can complete the full Spec Kit workflow (Constitution → Specify → Clarify → Plan → Tasks → Analyze) through the web UI in under 30 minutes for a typical feature specification.

- **SC-003**: Command output streams to the UI with less than 2 seconds latency between command output and UI display for 95% of output lines.

- **SC-004**: System successfully records execution metadata for 100% of phase runs, enabling full auditability and reproducibility.

- **SC-005**: Users can discover and select existing projects from a workspace directory containing up to 50 projects in under 5 seconds.

- **SC-006**: Artifact browser successfully renders Markdown content for all artifact types (constitution, specs, clarifications, plan, tasks, analysis) with proper formatting in 100% of cases.

- **SC-007**: System handles and clearly displays errors for common failure scenarios (CLI not installed, permission errors, invalid paths, command failures) with actionable error messages in 100% of cases.

- **SC-008**: System prevents directory traversal attacks and restricts path operations to allowed base directories with 100% validation coverage.

- **SC-009**: Secrets (GitHub tokens, API keys) are never persisted in repository files and are masked in logs/UI displays in 100% of cases.

- **SC-010**: Users can rerun any phase and access complete execution history for auditability, with all historical runs preserved and accessible.
