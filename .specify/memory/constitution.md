<!--
Sync Impact Report:
Version change: (none) → 1.0.0
Modified principles: (none - initial creation)
Added sections:
  - Phase Model (new section describing Spec Kit workflow phases)
  - Quality Attributes (new section)
  - User Needs (new section)
Removed sections: (none)
Templates requiring updates:
  ✅ plan-template.md - Constitution Check section will reference new principles
  ✅ spec-template.md - No changes needed (principles don't affect spec structure)
  ✅ tasks-template.md - No changes needed (principles don't affect task structure)
Follow-up TODOs: (none)
-->

# Spec Kit Orchestrator Constitution

## Core Principles

### I. Repository as Source of Truth

The repository filesystem is the authoritative source for all Spec Kit artifacts and execution metadata. All generated artifacts MUST be stored in predictable, version-controlled locations within the repository. The application MUST NOT maintain a separate database or external state store for artifacts. This ensures developers can open the repository in any IDE and see the complete project state, enabling seamless handoff between the web UI and developer workflows.

### II. Reproducibility

Every Spec Kit phase execution MUST record complete execution metadata including: command executed, all parameters, working directory, environment variables used (non-secret values only), start/end timestamps, exit code, and output logs. This metadata MUST be persisted to `.specify/orchestrator/runs/<timestamp>/` in a structured format (JSON). The system MUST enable re-running any phase with identical parameters to produce deterministic results. Rationale: enables debugging, audit trails, and confidence in artifact generation.

### III. Transparency Over Magic

The application MUST display all CLI command output (stdout and stderr) to users in real-time via streaming. Users MUST be able to review command diffs and execution logs. No operations should be hidden or abstracted away in a way that prevents users from understanding what the system is doing. Rationale: builds trust with non-technical users and enables troubleshooting without requiring developer intervention.

### IV. Security and Secrets Management

The application MUST NOT persist secrets (GitHub tokens, LLM API keys) in repository files. Secrets MUST only be stored in environment variables or a secure secrets store. When displaying logs or metadata, secrets MUST be masked or redacted. If GitHub integration is implemented, the application MUST request only the minimum permissions required (least privilege). Rationale: prevents accidental exposure of sensitive credentials in version control.

### V. Auditability

All parameter documents and execution history MUST be easily reviewable. Parameter documents MUST be stored in predictable locations (e.g., `docs/spec-kit-parameters.md`). Execution metadata MUST include sufficient context to understand what was run, when, and why. This enables compliance reviews, debugging, and knowledge transfer.

### VI. CLI-First Execution Model

The application MUST drive Spec Kit workflows by executing the Spec Kit CLI (e.g., `specify init`, phase commands) rather than re-implementing Spec Kit's internal generation logic, templates, or agent prompts. The application acts as an orchestrator and UI layer, not a replacement for Spec Kit's core functionality. Rationale: ensures compatibility with Spec Kit updates and maintains consistency with developer workflows.

## Phase Model

Spec Kit Orchestrator follows the standard Spec Kit phase workflow:

1. **Constitution**: Establishes project principles and governance rules
2. **Specify**: Creates feature specifications from user requirements
3. **Clarify**: Resolves ambiguities in specifications (typically run immediately after Specify)
4. **Plan**: Generates implementation plans with technical context and design artifacts
5. **Tasks**: Breaks plans into actionable, prioritized implementation tasks
6. **Analyze**: Performs post-tasks verification and gap analysis

Analyze serves as a verification step that runs after Tasks to ensure completeness and consistency across all artifacts. The application MUST support running phases in this order and SHOULD warn users if they attempt to run phases out of sequence (e.g., running Plan before Specify).

## Quality Attributes

### Reliability and Determinism

CLI execution MUST be reliable and deterministic. The application MUST handle command failures gracefully, capture exit codes, and surface errors clearly to users. Command execution MUST be idempotent where possible (re-running the same phase with identical inputs should produce identical outputs).

### User Experience

The application MUST provide a good user experience for non-technical users (PMs and BAs). This includes: guided forms with sensible defaults, clear error messages, progress indicators for long-running operations, and intuitive navigation. The application MUST NOT require terminal proficiency or IDE knowledge.

### Error Reporting

All errors (stderr output, command failures, validation errors) MUST be clearly surfaced to users. Error messages MUST be actionable and avoid technical jargon where possible. The application MUST log errors for debugging while presenting user-friendly messages in the UI.

### Safe Defaults

The application MUST use safe defaults for filesystem paths and command arguments. Path operations MUST be restricted to allowed base directories to prevent directory traversal attacks. Input validation MUST be performed on all user-provided parameters before executing commands.

## User Needs

### Primary Users

- **Product Managers / Business Analysts**: Need guided intake workflows, artifact review capabilities, ability to rerun phases, and handoff mechanisms (PRs or exported files) to engineering teams
- **Engineers**: Need to open the repository in an IDE and see clean artifacts plus execution logs; optionally review/approve PRs created by the orchestrator
- **Administrators**: Need to configure base workspace directory, allowed `--ai` values for `specify init`, and secrets handling mechanisms

## Non-Goals

The following are explicitly out of scope:

- Re-implementing Spec Kit's internal generation logic, templates, or agent prompts
- Replacing developers' IDE workflows (developers should still be able to open the repo in Cursor and continue normally)
- Providing a general-purpose Git hosting product (minimal GitHub integration only if needed)
- Multi-tenant SaaS deployment (this is an internal tool, at least for v1)

## Governance

This constitution supersedes all other development practices and guidelines. All implementation work MUST comply with these principles.

### Amendment Procedure

Amendments to this constitution require:
1. Documentation of the proposed change and rationale
2. Review and approval (process to be defined by project maintainers)
3. Version increment according to semantic versioning rules
4. Update of this document with new version and amendment date
5. Propagation of changes to dependent templates and documentation

### Versioning Policy

Constitution versions follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Backward incompatible governance/principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording improvements, typo fixes, non-semantic refinements

### Compliance Review

All pull requests and code reviews MUST verify compliance with constitution principles. The "Constitution Check" section in implementation plans MUST be evaluated before proceeding with implementation. Violations of principles MUST be justified in the plan's "Complexity Tracking" section or resolved before implementation proceeds.

**Version**: 1.0.0 | **Ratified**: 2025-12-29 | **Last Amended**: 2025-12-29
