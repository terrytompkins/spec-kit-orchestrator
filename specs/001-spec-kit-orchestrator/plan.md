# Implementation Plan: Spec Kit Orchestrator

**Branch**: `001-spec-kit-orchestrator` | **Date**: 2025-12-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-spec-kit-orchestrator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Spec Kit Orchestrator is a Streamlit web application that provides a non-technical UI over the GitHub Spec Kit workflow, enabling product managers and business analysts to create and manage Spec Kit projects and artifacts without needing an IDE or terminal proficiency. The application orchestrates Spec Kit CLI commands (Option 2: one-click CLI execution) with real-time output streaming and execution metadata recording, while laying the foundation for Option 3 (guided pipeline with staleness detection). The architecture uses Streamlit's multi-page navigation, a CLI execution wrapper for command streaming, and a filesystem-based artifact discovery layer. All artifacts and metadata are stored in the repository filesystem as the source of truth, ensuring seamless handoff between the web UI and developer IDE workflows.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Streamlit (web UI framework), subprocess (CLI execution), pathlib (filesystem operations), PyYAML (YAML parsing/generation), python-dotenv (environment variable management), gitpython (optional, for git commit hash extraction)  
**Storage**: Filesystem-based (repository as source of truth). No database required. Execution metadata stored as JSON files in `.specify/orchestrator/runs/<timestamp>/`. Configuration stored in `.specify/orchestrator/config.yml` or environment variables.  
**Testing**: pytest (unit tests), pytest-mock (mocking subprocess calls), streamlit-testing (UI component testing)  
**Target Platform**: Local machine (v1). Python 3.11+ on macOS, Linux, or Windows. Runs as a single Streamlit process.  
**Project Type**: Single web application (Streamlit app)  
**Performance Goals**: 
- Command output streaming latency: <2 seconds for 95% of output lines (SC-003)
- Project discovery: <5 seconds for 50 projects (SC-005)
- UI responsiveness: no blocking during long-running commands (streaming architecture)
**Constraints**: 
- Local execution only (v1) - no multi-user concurrency concerns
- Must work with existing Spec Kit CLI (no modifications to Spec Kit)
- Secrets must not be persisted in repository files
- Path operations restricted to admin-configured base directory
**Scale/Scope**: 
- Single user per instance (local execution)
- Support for multiple projects (up to 50 in workspace directory)
- Typical workflow: 6 phases (Constitution → Specify → Clarify → Plan → Tasks → Analyze)
- Artifact sizes: typical Markdown files (10KB-500KB), execution logs (1KB-100KB per run)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Repository as Source of Truth ✅
- **Compliance**: All artifacts stored in repository filesystem at predictable locations (`.specify/`, `docs/`, `specs/`). No external database or state store.
- **Validation**: Architecture uses filesystem as sole storage mechanism. Execution metadata in `.specify/orchestrator/runs/`. Parameter documents in `docs/`.

### II. Reproducibility ✅
- **Compliance**: Execution metadata includes command, parameters, cwd, env vars (non-secret), timestamps, exit code, output logs. Stored in JSON format.
- **Validation**: Run metadata schema defined in data model section. Each execution creates timestamped directory with complete metadata.

### III. Transparency Over Magic ✅
- **Compliance**: All CLI output (stdout/stderr) streamed to UI in real-time. Execution logs preserved for review.
- **Validation**: Streaming architecture uses subprocess with real-time output capture. Logs written to files for later review.

### IV. Security and Secrets Management ✅
- **Compliance**: Secrets (GitHub tokens, API keys) stored only in environment variables. Masked in logs/UI displays.
- **Validation**: Secrets handling uses environment variables. Log sanitization filters secrets before display/write.

### V. Auditability ✅
- **Compliance**: Parameter documents in predictable locations (`docs/spec-kit-parameters.md`, `docs/spec-kit-parameters.yml`). Execution history in `.specify/orchestrator/runs/`.
- **Validation**: All execution metadata includes sufficient context (command, params, timestamps, git commit hash if available).

### VI. CLI-First Execution Model ✅
- **Compliance**: Application executes Spec Kit CLI commands (`specify init`, phase commands) rather than re-implementing Spec Kit logic.
- **Validation**: Architecture includes CLI execution wrapper that runs actual Spec Kit commands. No re-implementation of Spec Kit internals.

**Result**: All constitution principles satisfied. No violations. Proceed to implementation.

## Project Structure

### Documentation (this feature)

```text
specs/001-spec-kit-orchestrator/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── orchestrator/
│   ├── __init__.py
│   ├── app.py                    # Main Streamlit app entry point
│   ├── pages/                    # Streamlit multi-page structure
│   │   ├── __init__.py
│   │   ├── project_creation.py   # New project wizard (M1)
│   │   ├── project_selection.py  # Project discovery and selection (M0)
│   │   ├── interview_chat.py    # Parameter generation chat (M2)
│   │   ├── phase_runner.py       # Phase execution UI (M3)
│   │   └── artifact_browser.py   # Artifact viewing (M0)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── project_discovery.py  # Scan workspace for .specify/ directories
│   │   ├── cli_executor.py       # CLI execution wrapper with streaming
│   │   ├── artifact_reader.py    # Read and render artifacts
│   │   ├── parameter_generator.py # Generate parameter docs (Markdown + YAML)
│   │   ├── run_metadata.py      # Create and manage execution metadata
│   │   └── config_manager.py     # Load admin configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py            # Project entity
│   │   ├── phase_execution.py    # Phase execution entity
│   │   ├── artifact.py           # Artifact entity
│   │   └── workspace_config.py  # Workspace configuration entity
│   └── utils/
│       ├── __init__.py
│       ├── path_validation.py    # Path sanitization and allowlist checking
│       ├── secret_masker.py      # Mask secrets in logs/UI
│       └── yaml_parser.py        # Parse/generate YAML parameter docs

tests/
├── unit/
│   ├── test_path_validation.py
│   ├── test_cli_executor.py
│   ├── test_project_discovery.py
│   └── test_secret_masker.py
├── integration/
│   ├── test_project_creation_flow.py
│   ├── test_phase_execution_flow.py
│   └── test_artifact_browsing.py
└── fixtures/
    └── sample_projects/          # Test project fixtures

.specify/
└── orchestrator/
    ├── config.yml                # Admin configuration (base dir, allowed AI values)
    └── runs/                     # Execution metadata (created at runtime)
        └── <timestamp>/
            ├── metadata.json
            ├── stdout.log
            └── stderr.log

docs/
└── spec-kit-parameters.md       # Generated parameter document (Markdown)
    spec-kit-parameters.yml       # Generated parameter document (YAML)
```

**Structure Decision**: Single project structure with `src/orchestrator/` as the main package. Streamlit multi-page architecture using `pages/` directory (Streamlit's native multi-page support). Services layer for business logic, models for data entities, utils for shared utilities. Tests mirror source structure. Configuration and execution metadata stored in `.specify/orchestrator/` to align with Spec Kit conventions.

## Architecture

### Overview

The application follows a layered architecture with Streamlit as the presentation layer, service layer for business logic, and filesystem as the data persistence layer.

```
┌─────────────────────────────────────────────────────────┐
│                  Streamlit UI Layer                      │
│  (Multi-page: Project Creation, Selection, Runner)    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  Service Layer                           │
│  - Project Discovery  - CLI Executor  - Artifact Reader│
│  - Parameter Generator - Run Metadata - Config Manager│
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              Filesystem (Repository)                       │
│  - Projects (.specify/)  - Artifacts (specs/, docs/)     │
│  - Execution Metadata (.specify/orchestrator/runs/)      │
└───────────────────────────────────────────────────────────┘
```

### Components

#### 1. Streamlit UI (Multi-page)

**Technology**: Streamlit with native multi-page support via `pages/` directory.

**Pages**:
- `Home/Project Selection` (`pages/project_selection.py`): Discover and select existing projects
- `New Project` (`pages/project_creation.py`): Wizard for creating new Spec Kit projects
- `Interview Chat` (`pages/interview_chat.py`): AI chat interface for parameter generation
- `Phase Runner` (`pages/phase_runner.py`): Execute phases with streaming output
- `Artifact Browser` (`pages/artifact_browser.py`): View generated artifacts and execution logs

**Navigation**: Streamlit's native sidebar navigation (automatic from `pages/` directory).

#### 2. Backend Services

**CLI Execution Wrapper** (`services/cli_executor.py`):
- Execute `specify init` and phase commands via subprocess
- Stream stdout/stderr in real-time to Streamlit UI
- Capture exit codes and command completion status
- Write execution logs to `.specify/orchestrator/runs/<timestamp>/`
- Handle command failures gracefully with error capture

**Project Discovery** (`services/project_discovery.py`):
- Scan admin-configured base workspace directory
- Identify folders containing `.specify/` directories
- Return project list with metadata (name, path, last modified)

**Artifact Reader** (`services/artifact_reader.py`):
- Discover artifacts in predictable locations (`.specify/memory/constitution.md`, `specs/*/spec.md`, etc.)
- Render Markdown content with proper formatting
- Provide navigation between related artifacts

**Parameter Generator** (`services/parameter_generator.py`):
- Generate `docs/spec-kit-parameters.md` (human-readable copy/paste)
- Generate `docs/spec-kit-parameters.yml` (machine-readable)
- Create timestamped backups before overwriting
- Use LLM client (optional) for interview chat functionality

**Run Metadata** (`services/run_metadata.py`):
- Create execution metadata JSON files
- Record: phase name, command args, cwd, env vars (non-secret), timestamps, exit code, log paths, git commit hash, inputs hash
- Organize by timestamped directories

**Config Manager** (`services/config_manager.py`):
- Load admin configuration from `.specify/orchestrator/config.yml`
- Manage: base workspace directory, allowed `--ai` values, secrets handling settings
- Provide defaults if config missing

#### 3. CLI Execution Wrapper (Detailed)

**Implementation Approach**:
- Use Python's `subprocess.Popen` with `stdout=subprocess.PIPE, stderr=subprocess.PIPE`
- Read output line-by-line in real-time
- Stream to Streamlit using `st.empty()` containers that update incrementally
- Write simultaneously to log files for persistence
- Handle both stdout and stderr streams separately
- Capture exit code on completion

**Streaming to Streamlit**:
```python
# Pseudo-code approach
with st.empty() as output_container:
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, text=True)
    output_lines = []
    for line in iter(process.stdout.readline, ''):
        output_lines.append(line)
        output_container.code('\n'.join(output_lines))  # Incremental update
        log_file.write(line)  # Persist to file
    process.wait()
    exit_code = process.returncode
```

**Error Handling**:
- Capture stderr separately from stdout
- Display errors prominently in UI (red highlighting)
- Preserve error output in execution logs
- Return structured error information for UI display

#### 4. Artifact Discovery Layer

**Artifact Locations** (predictable paths):
- Constitution: `.specify/memory/constitution.md`
- Specs: `specs/<feature-branch>/spec.md`
- Clarifications: `specs/<feature-branch>/clarifications.md` (if exists)
- Plans: `specs/<feature-branch>/plan.md`
- Tasks: `specs/<feature-branch>/tasks.md`
- Analysis: `specs/<feature-branch>/analysis.md` (if exists)
- Execution Logs: `.specify/orchestrator/runs/<timestamp>/`

**Discovery Logic**:
- Scan project directory for known artifact patterns
- Check file existence before attempting to read
- Provide "not generated yet" messages for missing artifacts
- Link related artifacts (e.g., spec → plan → tasks)

**Rendering**:
- Use Streamlit's `st.markdown()` for Markdown rendering
- Use `st.code()` with language hints for code blocks
- Provide navigation links between related artifacts

## Data Model

### Run Metadata Schema

**File**: `.specify/orchestrator/runs/<timestamp>/metadata.json`

```json
{
  "phase_name": "constitution|specify|clarify|plan|tasks|analyze",
  "command": "specify constitution ...",
  "args": ["--arg1", "value1"],
  "working_directory": "/path/to/project",
  "environment_vars": {
    "PATH": "/usr/bin:/bin",
    "PYTHONPATH": "/opt/python"
  },
  "start_timestamp": "2025-12-29T14:30:22Z",
  "end_timestamp": "2025-12-29T14:32:15Z",
  "status": "success|failure|in_progress",
  "exit_code": 0,
  "stdout_log_path": ".specify/orchestrator/runs/20251229-143022/stdout.log",
  "stderr_log_path": ".specify/orchestrator/runs/20251229-143022/stderr.log",
  "git_commit_hash": "abc123def456...",
  "inputs_hash": "sha256:..." 
}
```

**Fields**:
- `phase_name`: Which Spec Kit phase was executed
- `command`: Full command string executed
- `args`: Command arguments (array)
- `working_directory`: CWD when command executed
- `environment_vars`: Non-secret environment variables (secrets excluded)
- `start_timestamp`: ISO 8601 timestamp when execution started
- `end_timestamp`: ISO 8601 timestamp when execution completed
- `status`: Execution status (success/failure/in_progress)
- `exit_code`: Process exit code (0 = success, non-zero = failure)
- `stdout_log_path`: Relative path to stdout log file
- `stderr_log_path`: Relative path to stderr log file
- `git_commit_hash`: Git commit hash if project is a git repo (optional)
- `inputs_hash`: SHA256 hash of inputs for staleness detection (Option 3 readiness)

### Parameter Document Schema

**Markdown Format** (`docs/spec-kit-parameters.md`):
- Human-readable copy/paste blocks for each phase
- Format: Markdown with code blocks containing command parameters
- Structure: One section per phase (Constitution, Specify, Clarify, Plan, Tasks, Analyze)

**YAML Format** (`docs/spec-kit-parameters.yml`):
```yaml
phases:
  constitution:
    command: "speckit.constitution"
    parameters:
      description: "..."
      # ... other parameters
  specify:
    command: "speckit.specify"
    parameters:
      description: "..."
      # ... other parameters
  # ... other phases
```

**Lifecycle**:
- When regenerated: Create backup `docs/spec-kit-parameters.<timestamp>.md` and `docs/spec-kit-parameters.<timestamp>.yml`
- Then overwrite main files with new content
- Backup files preserved for recovery

### Workspace Configuration Schema

**File**: `.specify/orchestrator/config.yml`

```yaml
workspace:
  base_directory: "/path/to/workspace"  # Admin-configured base directory
  
ai_agents:
  allowed_values:
    - "claude"
    - "gpt-4"
    - "gpt-3.5"
  
secrets:
  storage: "environment"  # "environment" or "secure_store" (future)
  mask_in_logs: true
```

### Entity Models (Python Classes)

**Project** (`models/project.py`):
```python
@dataclass
class Project:
    name: str
    path: Path
    init_timestamp: datetime
    current_phase_status: Dict[str, str]  # phase -> status
    artifacts: List['Artifact']
    executions: List['PhaseExecution']
```

**PhaseExecution** (`models/phase_execution.py`):
```python
@dataclass
class PhaseExecution:
    phase_name: str
    command: str
    args: List[str]
    working_directory: Path
    start_timestamp: datetime
    end_timestamp: Optional[datetime]
    exit_code: Optional[int]
    status: str
    stdout_log_path: Path
    stderr_log_path: Path
    git_commit_hash: Optional[str]
    inputs_hash: str
```

**Artifact** (`models/artifact.py`):
```python
@dataclass
class Artifact:
    artifact_type: str  # constitution, spec, clarification, plan, tasks, analysis
    file_path: Path
    generation_timestamp: datetime
    associated_execution: Optional[PhaseExecution]
    content_hash: str  # For staleness detection
```

## Execution Flow and UX

### New Project Wizard (M1)

**Flow**:
1. User navigates to "New Project" page
2. Form fields:
   - Project name (text input, required)
   - Parent directory (text input with path validation, required)
   - AI agent option (dropdown from admin config, required)
   - GitHub token (password input, optional)
   - Extra init parameters (text area, optional)
3. User clicks "Create Project"
4. System validates:
   - Path is within allowed base directory
   - Path doesn't contain directory traversal attempts
   - AI agent value is in allowed list
5. System executes `specify init` with parameters
6. Real-time output streaming:
   - Create `st.empty()` container for output
   - Stream stdout/stderr line-by-line
   - Update container incrementally
   - Show progress indicator
7. On completion:
   - If success: Show success message, link to project
   - If failure: Show error message with stderr output, allow retry
8. Create execution metadata record

**UX Details**:
- Progress spinner during execution
- Output displayed in expandable code block
- Error messages highlighted in red
- Success message with next steps

### Post-Init: Interview Chat (M2)

**Flow**:
1. After successful project creation, user sees "Generate Parameters" option
2. User clicks to start interview chat
3. Chat interface (Streamlit chat components):
   - Display welcome message explaining purpose
   - Ask questions about project/feature
   - Collect user responses
   - Generate parameter documents when complete
4. System generates:
   - `docs/spec-kit-parameters.md` (backup existing if present)
   - `docs/spec-kit-parameters.yml` (backup existing if present)
5. Show success message with links to generated documents

**UX Details**:
- Use `st.chat_message()` for chat UI
- Show typing indicator during generation
- Display generated documents in expandable sections
- Allow regeneration if user wants to update

### Phase Runner Page (M3)

**Layout**:
- Phase buttons in order: Constitution → Specify → Clarify → Plan → Tasks → Analyze
- Status indicators next to each phase (not started / in progress / completed / failed)
- Analyze button disabled until Tasks completes
- Execution log area below buttons

**Flow**:
1. User clicks phase button (e.g., "Run Constitution")
2. System checks:
   - Required artifacts exist (warn if missing)
   - Phase dependencies met (warn if out of order)
3. If warnings: Show confirmation dialog
4. User confirms (or cancels)
5. System executes phase command:
   - Disable button, show "in progress" status
   - Stream output to log area in real-time
   - Create execution metadata record
6. On completion:
   - Update status indicator (success/failure)
   - Enable next phase button (if in order)
   - Show link to generated artifacts
   - Preserve execution log for review

**UX Details**:
- Buttons disabled during execution (prevent concurrent runs)
- Real-time output streaming with auto-scroll
- Success/failure clearly indicated (green/red)
- Links to artifacts appear after successful execution
- Execution history accessible via sidebar

### Artifact Browser (M0)

**Layout**:
- List of available artifacts with timestamps
- Artifact viewer with Markdown rendering
- Navigation between related artifacts
- Execution log viewer

**Flow**:
1. User navigates to "Artifacts" page
2. System discovers artifacts in project
3. Display artifact list:
   - Artifact type and name
   - Generation timestamp
   - Status (exists / not generated)
4. User clicks artifact to view
5. System reads and renders Markdown content
6. Provide navigation links to related artifacts

**UX Details**:
- Artifact list as expandable sections
- Markdown rendered with syntax highlighting
- Code blocks with language detection
- "Not generated yet" message for missing artifacts
- Link to phase runner to generate missing artifacts

## Security and Safety

### Path Allowlist

**Implementation** (`utils/path_validation.py`):
- Admin configures base workspace directory
- All user-provided paths validated against base directory
- Use `pathlib.Path.resolve()` to resolve absolute paths
- Check that resolved path is within base directory
- Reject paths containing `..` or absolute paths outside base

**Validation Logic**:
```python
def validate_path(user_path: str, base_directory: Path) -> Path:
    resolved = Path(user_path).resolve()
    base_resolved = base_directory.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError("Path outside allowed base directory")
    return resolved
```

### CLI Argument Sanitization

**Approach**:
- Validate all user inputs before constructing command
- Escape special characters in arguments
- Use `shlex.quote()` for shell argument escaping
- Prevent command injection by using subprocess with argument list (not shell=True)

**Example**:
```python
import shlex
args = [shlex.quote(arg) for arg in user_args]
process = subprocess.Popen(['specify', 'init'] + args, ...)
```

### Secrets Handling

**Storage**:
- Secrets (GitHub tokens, API keys) stored only in environment variables
- Never written to repository files
- Never included in execution metadata JSON

**Masking in Logs/UI** (`utils/secret_masker.py`):
- Scan output for common secret patterns (tokens, keys)
- Replace with `[REDACTED]` or `***` before display/write
- Preserve secrets in environment for command execution
- Use regex patterns to detect secrets in output

**Implementation**:
```python
def mask_secrets(text: str, secrets: List[str]) -> str:
    masked = text
    for secret in secrets:
        masked = masked.replace(secret, '[REDACTED]')
    return masked
```

### Input Validation

**Validation Points**:
- Project name: Alphanumeric, hyphens, underscores only
- Directory paths: Validated against allowlist
- AI agent values: Must be in admin-configured allowed list
- Command parameters: Sanitized before execution

## Milestones

### M0: Project Discovery + Artifact Browser
**Goal**: Enable users to discover and view existing projects and artifacts.

**Deliverables**:
- Project discovery service (scan workspace for `.specify/` directories)
- Project selection UI page
- Artifact discovery and rendering
- Artifact browser UI page
- Basic navigation between pages

**Acceptance**:
- User can see list of projects in workspace
- User can select a project
- User can view artifacts (if they exist)
- Markdown renders correctly

### M1: Init Wizard + Streaming Logs
**Goal**: Enable users to create new Spec Kit projects with real-time output streaming.

**Deliverables**:
- Project creation UI form
- Path validation and allowlist checking
- CLI execution wrapper with streaming
- Real-time output display in Streamlit
- Execution metadata recording
- Error handling and user-friendly messages

**Acceptance**:
- User can create new project through UI
- Output streams in real-time (<2s latency)
- Errors displayed clearly
- Execution metadata recorded
- Project successfully initialized

### M2: Parameter Doc Generation (Chat Stub + Template Output)
**Goal**: Generate parameter documents from interview chat (or template-based generation).

**Deliverables**:
- Interview chat UI (or template-based form)
- Parameter document generator (Markdown + YAML)
- Backup creation before overwrite
- Document validation

**Acceptance**:
- User can generate parameter documents
- Both Markdown and YAML formats created
- Backups created before overwrite
- Documents contain all required phases

### M3: Phase Runner Buttons + Run Metadata
**Goal**: Enable users to run Spec Kit phases from UI with complete execution tracking.

**Deliverables**:
- Phase runner UI page with buttons
- Phase dependency checking and warnings
- CLI execution for each phase
- Execution metadata recording (complete schema)
- Artifact linking after execution
- Execution history viewer

**Acceptance**:
- User can run all phases from UI
- Output streams in real-time
- Execution metadata recorded completely
- Phase dependencies enforced (with warnings)
- Execution history accessible

### M4: Option 3 Staleness Pipeline View (Post-v1)
**Goal**: Provide pipeline view with staleness detection (deferred to post-v1).

**Deliverables**:
- Staleness detection logic (input hashing, git diff analysis)
- Pipeline view UI with status indicators
- Staleness warnings
- Dependency graph visualization

**Acceptance**:
- System detects stale artifacts
- Pipeline view shows statuses
- Warnings displayed for stale artifacts

## Detailed Implementation Steps

### Streaming Output in Streamlit

**Challenge**: Streamlit reruns entire script on each interaction. Need to stream subprocess output in real-time without blocking.

**Solution**: Use Streamlit's `st.empty()` container with incremental updates and session state for output accumulation.

**Implementation**:
```python
import subprocess
import streamlit as st
from threading import Thread
import queue

def stream_command_output(command, args, output_container, log_file):
    """Stream command output to Streamlit UI and log file."""
    process = subprocess.Popen(
        [command] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr into stdout
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True
    )
    
    output_lines = []
    for line in iter(process.stdout.readline, ''):
        output_lines.append(line.rstrip())
        # Update UI incrementally
        output_container.code('\n'.join(output_lines))
        # Write to log file
        log_file.write(line)
        log_file.flush()
    
    process.wait()
    return process.returncode, output_lines

# In UI code:
with st.empty() as output_container:
    with open(log_path, 'w') as log_file:
        exit_code, output = stream_command_output(
            'specify', ['init', '--ai', 'claude'],
            output_container,
            log_file
        )
```

**Alternative for Long-Running Commands**: Use `st.rerun()` with session state to periodically refresh output, or use Streamlit's experimental `st.status()` for better UX.

### Risks and Mitigations

#### Risk 1: Command Injection
**Risk**: User-provided input could be used to inject malicious commands.

**Mitigation**:
- Never use `shell=True` in subprocess calls
- Always use argument list format: `subprocess.Popen(['specify', 'init', arg1, arg2])`
- Validate and sanitize all user inputs
- Use `shlex.quote()` for argument escaping
- Restrict paths to allowed base directory

#### Risk 2: Path Traversal Attacks
**Risk**: User could provide paths like `../../../etc/passwd` to access files outside workspace.

**Mitigation**:
- Validate all paths against admin-configured base directory
- Use `pathlib.Path.resolve()` to resolve absolute paths
- Check that resolved path starts with base directory path
- Reject paths containing `..` sequences
- Implement path allowlist validation before any filesystem operation

#### Risk 3: Secrets Leakage
**Risk**: Secrets could be accidentally written to logs or repository files.

**Mitigation**:
- Store secrets only in environment variables
- Never include secrets in execution metadata JSON
- Mask secrets in all log output before writing
- Use regex patterns to detect and redact secrets in output
- Validate that secrets are not in any committed files (pre-commit hook)

#### Risk 4: Concurrent Execution Issues
**Risk**: User could attempt to run multiple phases simultaneously, causing conflicts.

**Mitigation**:
- Disable phase buttons during execution (prevent concurrent runs)
- Use session state to track execution status
- Show clear "in progress" indicators
- For v1 (local execution), single user eliminates most concurrency concerns

#### Risk 5: Large Output Streams
**Risk**: Very large command output could exhaust memory or block UI.

**Mitigation**:
- Stream output line-by-line (don't buffer entire output)
- Write to log files immediately (don't keep in memory)
- Limit displayed output in UI (show last N lines, provide "view full log" link)
- Use pagination for large execution logs

#### Risk 6: CLI Not Found
**Risk**: Spec Kit CLI might not be installed or not in PATH.

**Mitigation**:
- Check for CLI availability before allowing operations
- Provide clear error message with installation instructions
- Detect CLI presence on app startup
- Show warning if CLI not found

#### Risk 7: Permission Errors
**Risk**: User might not have read/write permissions for project directory.

**Mitigation**:
- Check directory permissions before operations
- Provide clear error messages explaining permission issues
- Suggest solutions (chmod, run as different user)
- Validate permissions as part of path validation

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. All principles satisfied. No complexity tracking needed.
