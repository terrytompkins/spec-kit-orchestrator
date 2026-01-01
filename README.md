# Spec Kit Orchestrator

A Streamlit web application that provides a non-technical UI over the GitHub Spec Kit workflow, enabling product managers and business analysts to create and manage Spec Kit projects and artifacts without needing an IDE or terminal proficiency.

## Overview

Spec Kit Orchestrator bridges the gap between business needs and technical execution by providing a user-friendly web interface for running Spec Kit workflows. The application orchestrates Spec Kit CLI commands with real-time output streaming and execution metadata recording, making Spec Kit accessible to non-technical users while maintaining full compatibility with developer workflows.

### Key Features

- **Project Creation**: Create new Spec Kit projects through a guided web form without using a terminal
- **Parameter Generation**: Generate Spec Kit command parameter documents through an interview-style interface (template-based in v1)
- **Phase Execution**: Run Spec Kit phases (Constitution → Specify → Clarify → Plan → Tasks → Analyze) directly from the UI with real-time output streaming
- **Artifact Browsing**: View and review generated artifacts (constitutions, specs, plans, tasks, etc.) with proper Markdown rendering
- **Project Discovery**: Discover and work with existing Spec Kit projects in a configured workspace directory
- **Execution History**: Complete audit trail of all phase executions with metadata, logs, and timestamps

## Requirements

- **Python**: 3.11 or higher
- **Spec Kit CLI**: Must be installed and available in PATH (see [Spec Kit documentation](https://github.com/spec-kit/spec-kit) for installation)
- **Operating System**: macOS, Linux, or Windows

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd spec-kit-orchestrator
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Spec Kit CLI is installed**:
   ```bash
   specify --version
   ```
   If not installed, follow the [Spec Kit installation instructions](https://github.com/spec-kit/spec-kit).

## Configuration

### Admin Configuration

Create a configuration file at `.specify/orchestrator/config.yml` **in the orchestrator application directory** (not in the projects you create):

```yaml
workspace:
  base_directory: "/path/to/workspace"  # Base directory for project discovery

ai_agents:
  allowed_values:
    - "claude"
    - "gpt-4"
    - "gpt-3.5"

secrets:
  storage: "environment"  # "environment" or "secure_store" (future)
  mask_in_logs: true
```

**Important Notes**:
- This config file is for the **orchestrator tool itself**, located at: `<orchestrator-repo-root>/.specify/orchestrator/config.yml`
- The `base_directory` must be an absolute path. All user-provided project paths will be validated against this base directory to prevent directory traversal attacks.
- Projects created through the orchestrator will have their own `.specify/` directories (created by `specify init`), but those are separate from this orchestrator configuration.

### Environment Variables

Secrets (GitHub tokens, API keys) should be stored in environment variables, not in configuration files:

```bash
export GITHUB_TOKEN="your-token-here"
export OPENAI_API_KEY="your-key-here"  # If using OpenAI-based agents
```

## Usage

### Starting the Application

```bash
streamlit run src/orchestrator/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Workflow

1. **Create a New Project**:
   - Navigate to "New Project" page
   - Fill in project name, parent directory (within configured base directory), AI agent option, and optional GitHub token
   - Click "Create Project" and watch real-time output streaming
   - Project is initialized with `.specify/` directory structure

2. **Generate Parameters** (Optional):
   - Navigate to "Interview Chat" page
   - Answer questions about your project/feature
   - System generates `docs/spec-kit-parameters.md` and `docs/spec-kit-parameters.yml`

3. **Run Spec Kit Phases**:
   - Navigate to "Phase Runner" page
   - Click buttons to run phases in order: Constitution → Specify → Clarify → Plan → Tasks → Analyze
   - Watch real-time output streaming
   - View generated artifacts and execution logs

4. **Browse Artifacts**:
   - Navigate to "Artifacts" page
   - View generated artifacts with proper Markdown rendering
   - Review execution history and logs

5. **Discover Existing Projects**:
   - Navigate to "Project Selection" page
   - Browse projects in your workspace directory
   - Select a project to work with

## Project Structure

```
spec-kit-orchestrator/
├── src/
│   └── orchestrator/
│       ├── app.py                    # Main Streamlit app entry point
│       ├── pages/                    # Streamlit multi-page structure
│       │   ├── project_creation.py   # New project wizard
│       │   ├── project_selection.py  # Project discovery and selection
│       │   ├── interview_chat.py     # Parameter generation chat
│       │   ├── phase_runner.py       # Phase execution UI
│       │   └── artifact_browser.py  # Artifact viewing
│       ├── services/                 # Business logic layer
│       │   ├── project_discovery.py
│       │   ├── cli_executor.py
│       │   ├── artifact_reader.py
│       │   ├── parameter_generator.py
│       │   ├── run_metadata.py
│       │   └── config_manager.py
│       ├── models/                   # Data entities
│       │   ├── project.py
│       │   ├── phase_execution.py
│       │   ├── artifact.py
│       │   └── workspace_config.py
│       └── utils/                    # Shared utilities
│           ├── path_validation.py
│           ├── secret_masker.py
│           └── yaml_parser.py
├── tests/
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── fixtures/                     # Test fixtures
├── docs/                             # Generated parameter documents
├── .specify/
│   └── orchestrator/
│       ├── config.yml                # Admin configuration
│       └── runs/                     # Execution metadata (created at runtime)
└── specs/                            # Spec Kit artifacts for this project
    └── 001-spec-kit-orchestrator/
        ├── spec.md
        ├── plan.md
        └── tasks.md
```

## Architecture

The application follows a layered architecture:

- **Presentation Layer**: Streamlit multi-page UI
- **Service Layer**: Business logic (CLI execution, project discovery, artifact reading, etc.)
- **Data Layer**: Filesystem-based storage (repository as source of truth)

All artifacts and execution metadata are stored in the repository filesystem, ensuring seamless handoff between the web UI and developer IDE workflows.

## Development

### Running Tests

```bash
pytest
```

### Code Quality

The project follows Python best practices and includes:
- Type hints where applicable
- Comprehensive error handling
- Input validation and sanitization
- Security best practices (path validation, secret masking)

### Implementation Status

This project is currently in the specification and planning phase. See `specs/001-spec-kit-orchestrator/` for:
- **spec.md**: Feature specification with user stories and requirements
- **plan.md**: Implementation plan with architecture and technical details
- **tasks.md**: Detailed implementation tasks organized by milestone

## Key Principles

This project adheres to the following principles (see `.specify/memory/constitution.md`):

1. **Repository as Source of Truth**: All artifacts stored in predictable, version-controlled locations
2. **Reproducibility**: Complete execution metadata recorded for every phase run
3. **Transparency Over Magic**: All CLI output streamed in real-time, no hidden operations
4. **Security and Secrets Management**: Secrets never persisted in repository files
5. **Auditability**: Parameter documents and execution history easily reviewable
6. **CLI-First Execution Model**: Orchestrates Spec Kit CLI rather than re-implementing logic

## Limitations (v1)

- **Local execution only**: Each user runs the app on their own machine (no shared server)
- **No GitHub PR creation**: PR creation functionality deferred to post-v1
- **Template-based parameter generation**: Full LLM-powered chat may be deferred to post-v1
- **Option 3 features deferred**: Pipeline view and staleness detection UI deferred to post-v1 (architecture readiness implemented)

## Troubleshooting

### Spec Kit CLI Not Found

If you see an error that the Spec Kit CLI is not installed:
1. Verify `specify` command is in your PATH
2. Install Spec Kit following the [official documentation](https://github.com/spec-kit/spec-kit)
3. Restart the Streamlit application

### Permission Errors

If you encounter permission errors:
- Ensure the configured `base_directory` is accessible
- Check that you have read/write permissions for project directories
- Verify path validation is working correctly

### Path Validation Errors

If project creation fails with path validation errors:
- Ensure the project path is within the configured `base_directory`
- Check that the path doesn't contain directory traversal attempts (`../`)
- Verify the path is absolute or relative to the base directory

## Contributing

This is an internal tool (at least for v1). For contributions:
1. Review the specification in `specs/001-spec-kit-orchestrator/spec.md`
2. Check the implementation plan in `specs/001-spec-kit-orchestrator/plan.md`
3. Follow the task breakdown in `specs/001-spec-kit-orchestrator/tasks.md`
4. Ensure all changes comply with the project constitution (`.specify/memory/constitution.md`)

## License

[Add license information here]

## Related Projects

- [Spec Kit](https://github.com/spec-kit/spec-kit): The underlying CLI tool that this orchestrator manages

---

**Status**: Specification and Planning Phase  
**Last Updated**: 2025-12-29

