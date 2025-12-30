# Spec Kit Orchestrator — Spec Kit Command Parameters (Copy/Paste)

Repo name: **spec-kit-orchestrator**  
Implementation target: **Streamlit web app**  
Execution model: **Option 2 (One-click CLI execution)** with a path to **Option 3 (Guided pipeline / state machine UI)**

This document is meant to be used **inside Cursor**: copy the parameter blocks into the corresponding **Spec Kit slash commands**.

---

## 0) Working assumptions to bake into the artifacts

- The app helps non-technical users create and run Spec Kit phases without using an IDE.
- The app **drives the Spec Kit CLI** (e.g., runs `specify init`, and later runs phase generation commands) rather than re-implementing Spec Kit logic.
- The app provides:
  - Project creation UI (runs `specify init` with selected `--ai`, optional GitHub token, and extra params)
  - Guided “interview chat” to produce phase parameters
  - One-click buttons to run phases and **stream CLI output** into the UI
  - Artifact browser for generated Markdown files
- Project discovery is based on the presence of a `.specify/` directory in a workspace folder.

---

## 1) `/speckit.constitution` parameters

> Paste into: **/speckit.constitution**

**Context / Prompt (copy/paste):**
```text
Create a project constitution for “Spec Kit Orchestrator”, a Streamlit web application that provides a non-technical UI over the GitHub Spec Kit workflow.

Purpose:
- Enable product managers and business analysts to create and manage Spec Kit projects and artifacts without needing an IDE (e.g., Cursor) or terminal proficiency.
- Provide “Option 2” behavior first: run Spec Kit phases via CLI from the web UI with streaming output, while recording execution metadata.
- Set the foundation for “Option 3”: a guided pipeline UI that understands phase ordering and staleness (e.g., “Plan is stale because Spec changed”).

Non-goals:
- Re-implement Spec Kit’s internal generation logic, templates, or agent prompts.
- Replace developers’ IDE workflows; developers should still be able to open the repo in Cursor and continue normally.
- Provide a general-purpose Git hosting product. (We will integrate with GitHub minimally if needed.)
- Multi-tenant SaaS. This is an internal tool (at least for v1).

Key principles / guardrails:
- Treat the repository as the source of truth. Store artifacts in the repo in predictable locations.
- Make operations reproducible: every phase run should record command, parameters, timestamps, and output logs.
- Prefer transparency over magic: show command output and diffs so users trust the system.
- Security: do not persist secrets (GitHub tokens, LLM keys) in repo files; only in environment variables or secure secrets store.
- Least privilege: if GitHub integration is used, request only the permissions required.
- Auditability: parameter documents and execution history should be easy to review.

Primary users and needs:
- PM/BA: guided intake, artifact review, rerun phases, handoff to engineering via PR or exported files.
- Engineer: open repo in IDE and see clean artifacts + execution logs; optionally review/approve PRs.
- Admin: configure base workspace directory, allowed `--ai` values, and secrets handling.

Quality attributes:
- Reliable and deterministic behavior for CLI execution.
- Good UX for non-technical users.
- Clear error reporting (stderr surfaced).
- Safe defaults, especially around filesystem paths and command arguments.

Include a short “phase model” section describing Constitution → Specify → Clarify → Plan → Tasks → Analyze as the expected flow, with Analyze as a post-tasks verification step.
```

---

## 2) `/speckit.specify` parameters

> Paste into: **/speckit.specify**

**Context / Prompt (copy/paste):**
```text
Create a product/feature specification for “Spec Kit Orchestrator”, a Streamlit web app that orchestrates GitHub Spec Kit workflows for non-technical users.

Core feature set (Option 2 baseline):
1) Create new Spec Kit project
   - User chooses: project name, parent directory, AI agent option (valid values for `specify init --ai`), optional GitHub token, and optional extra init parameters.
   - App runs `specify init` and streams stdout/stderr to the UI.
2) Interview chat to generate phase parameters
   - After init success, app provides an AI chat that interviews user about the project/feature they want.
   - Outcome is a “Spec Kit command parameter document” written to the repo.
   - This document is a single markdown file in a `docs/` directory containing copy/paste blocks for each Spec Kit phase.
3) Run phases from the UI (CLI-driven)
   - UI shows buttons to run phases and streams output:
     - Constitution
     - Specify
     - Clarify (always run immediately after Specify per team convention)
     - Plan
     - Tasks
     - Analyze (run after Tasks as a final check)
   - Each run produces/updates the expected Spec Kit artifacts in the repo.
   - Each run writes execution metadata + logs under a predictable folder (e.g., `.specify/orchestrator/runs/`).
4) Browse artifacts
   - UI can browse and render key artifacts: constitution, specs, clarifications, plan, tasks, analysis output, and run logs.

Option 3 readiness (not necessarily implemented in v1):
- Model phase dependencies and staleness: warn if downstream artifacts are stale because upstream changed.
- Provide a pipeline view with statuses (not started / generated / stale / failed).

Functional requirements:
- Workspace discovery: list folders containing `.specify/` under a configured base directory.
- Safe path handling: prevent directory traversal; restrict to allowed base dir.
- Streaming output: show command logs live and keep them for later viewing.
- Input validation: validate init args and phase parameter doc generation.
- Non-technical UX: guided forms with sensible defaults.

Non-functional requirements:
- Security: secrets are not written to repo; tokens are masked in logs where possible.
- Observability: structured run metadata (timestamps, status, commands, git commit hash if applicable).
- Portability: local run on a developer machine first; containerization later.

Deliverables:
- A clear set of user stories and acceptance criteria that map to the UI flows above.
- Include edge cases: init failures, invalid directory, missing `.specify`, CLI not installed, permission errors, token missing, and rerun behavior.
```

---

## 3) `/speckit.clarify` parameters

> Paste into: **/speckit.clarify**  
> (Per your convention: run **immediately after** `/speckit.specify`.)

**Context / Prompt (copy/paste):**
```text
Clarify ambiguous requirements for “Spec Kit Orchestrator” based on the specification.

Focus clarifications on:
- The exact set of `specify init --ai` allowed values we want to support in the UI (and where they come from).
- Whether GitHub integration is required in v1 (PR creation) or deferred.
- Where the “command parameter document” lives and its lifecycle (overwrite vs versioned files).
- Whether the interview chat generates:
  a) only copy/paste parameter blocks, or
  b) also structured machine-readable data for automatic execution.
- How we will handle multiple features within a single repo (one parameter doc per feature?).
- How to represent and detect “staleness” for Option 3 (hashing inputs, git diffs, timestamps).
- Execution environment: local machine only, or a shared server (permissions, sandboxing).
- Error-handling UX expectations for non-technical users.

Output:
- A concise list of clarifying questions and recommended default decisions suitable for rapid implementation.
```

---

## 4) `/speckit.plan` parameters

> Paste into: **/speckit.plan**

**Context / Prompt (copy/paste):**
```text
Create an implementation plan for “Spec Kit Orchestrator” (Streamlit app), starting with Option 2 (one-click CLI execution) and paving the way to Option 3 (guided pipeline + staleness).

Plan should include:
Architecture
- Streamlit UI (multi-page or tabs)
- Backend services within app (filesystem, command runner, optional LLM client)
- CLI execution wrapper that:
  - runs `specify init` and phase commands
  - streams stdout/stderr
  - captures exit codes
  - writes run logs + metadata (JSON) to `.specify/orchestrator/runs/<timestamp>/`
- Artifact discovery layer:
  - lists key generated files and renders Markdown

Data model
- “Command parameter document” stored in `docs/spec-kit-parameters.md` (single markdown file for copy/paste).
- ALSO define (for Option 2 automation and Option 3 readiness) a parallel machine-readable file (e.g., `docs/spec-kit-parameters.yml`) that mirrors the same content.
  - The UI may generate both from the same chat interview.
- Run metadata schema:
  - phase name, command args, cwd, env vars used (non-secret), start/end timestamps, status, exit code, stdout/stderr paths, git commit hash if available, and an “inputs hash” for staleness.

Execution flow and UX
- New Project wizard (init + log streaming)
- Post-init: “Interview chat” to generate parameters
- Phase run page:
  - shows buttons for phases in the team order:
    Constitution → Specify → Clarify → Plan → Tasks → Analyze
  - Analyze is only enabled after Tasks by default
  - Each button run shows live logs and then links to produced artifacts

Security and safety
- Path allowlist to base directory
- Validate and sanitize CLI args
- Secrets handling (do not write tokens to repo)

Milestones
- M0: project discovery + artifact browser
- M1: init wizard + streaming logs
- M2: parameter doc generation (chat stub + template output)
- M3: phase runner buttons + run metadata
- M4: (later) Option 3 staleness pipeline view

Deliverables:
- A clear folder structure for the app repo
- Detailed steps, including how to implement streaming output in Streamlit (incremental UI updates)
- Risks and mitigations for running shell commands from a web UI
```

---

## 5) `/speckit.tasks` parameters

> Paste into: **/speckit.tasks**

**Context / Prompt (copy/paste):**
```text
Generate implementation tasks for “Spec Kit Orchestrator” (Streamlit app) based on the plan.

Organize tasks by milestone and include:
- Repo scaffolding (Python project layout, requirements, local run docs)
- Project discovery module
- Artifact browser (render markdown, list files under `.specify`)
- CLI execution wrapper:
  - run command
  - stream logs
  - capture metadata
  - write logs to `.specify/orchestrator/runs/`
- Init wizard UI:
  - form fields: project name, parent directory, --ai selection, optional --github-token, extra params
  - safe validation + allowlist
  - run `specify init` and stream output
- Parameter doc generator:
  - create `docs/spec-kit-parameters.md` containing copy/paste blocks for phases
  - (optionally) also create `docs/spec-kit-parameters.yml` from the same content
- Phase runner UI:
  - buttons for Constitution/Specify/Clarify/Plan/Tasks/Analyze
  - enforce ordering and dependencies (soft enforcement in v1; warn if out of order)
  - show outputs and link to artifacts

Include test tasks:
- unit tests for path validation, project discovery, and run metadata generation
- “smoke test” checklist for running init + one phase end-to-end

Include explicit acceptance checks for each milestone.

Output tasks in a way that maps cleanly to GitHub issues (titles + descriptions + acceptance).
```

---

## 6) `/speckit.analyze` parameters

> Paste into: **/speckit.analyze**  
> (Per your convention: run **after** `/speckit.tasks` as a final check.)

**Context / Prompt (copy/paste):**
```text
Analyze the current Spec Kit artifacts for “Spec Kit Orchestrator” end-to-end (constitution through tasks).

Goals:
- Check for gaps, contradictions, and missing non-functional requirements.
- Ensure the Option 2 baseline is fully covered and Option 3 readiness is explicitly planned.
- Verify phase ordering matches team convention:
  Constitution → Specify → Clarify → Plan → Tasks → Analyze
- Validate that the “parameter document” concept is consistent:
  - single markdown doc for copy/paste
  - optional parallel machine-readable form for automation/staleness

Output:
- A concise list of findings, prioritized (high/medium/low)
- Concrete fixes: what to add/change in which artifact
- Any recommended defaults to reduce ambiguity
```

---

## Appendix: Why YAML is attractive for machine-readable parameters (explanation)

You asked why YAML was suggested for the parameter document format.

For *humans*, your **single markdown copy/paste document** is perfect.

For *automation* (Option 2 button runs) and *staleness detection* (Option 3), it helps to also have a machine-readable representation of the same intent. YAML is often a good choice because:

- **Human-editable**: PMs/BAs can edit it if needed without JSON punctuation fatigue.
- **Friendly to hierarchical data**: command parameters naturally nest (phases → fields → lists).
- **Easy to validate**: you can define a JSON Schema and validate YAML after parsing.
- **Diff-friendly**: git diffs on YAML tend to be readable.
- **Common in tooling**: many CLI/config workflows already use YAML.

That said, JSON is also totally fine. The key is: keep one canonical structure and generate the markdown “copy/paste” doc from it (or vice-versa) so they don’t drift.
