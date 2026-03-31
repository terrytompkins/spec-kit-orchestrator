# Phase Parameters Integration — Outline

## How Spec Kit actually works

### CLI vs IDE

- The **Spec Kit CLI** (`specify`) only exposes: **`init`**, **`check`**, **`version`**, and **`extension`** (with subcommands). There are **no** subcommands like `specify constitution`, `specify specify`, or `specify plan`.
- The **phase workflow** (constitution → specify → clarify → plan → tasks → analyze) is designed for the **IDE/agent**: the user runs **slash commands** (e.g. `/speckit.constitution`, `/speckit.specify`) inside an AI agent (Cursor, Claude Code, etc.). The agent reads a command file (e.g. `.cursor/commands/speckit.constitution.md`) and the **user input** is the text after the command (`$ARGUMENTS`). The agent then writes the artifact (e.g. `.specify/memory/constitution.md`).

So today:

- **Interview** → produces parameter text per phase and we save it to `docs/spec-kit-parameters.md` and `docs/spec-kit-parameters.yml`.
- **Phase runner** → runs `specify <phase>` (e.g. `specify constitution`). That is **not** a supported CLI command in the public Spec Kit repo; it may fail or behave differently depending on environment.
- **Parameters are not applied** when running phases; they are only stored for reference.

---

## How parameters could be applied

Because the CLI does not accept phase parameters, the practical way to “apply” saved parameters in the orchestrator is to **write the parameter content to the artifact files** that Spec Kit (and the slash commands) expect. That way, when the user runs a phase from the orchestrator, the interview output becomes the actual artifact content.

### 1. Source of parameters

- **Primary**: `docs/spec-kit-parameters.yml` (written when the user clicks “Generate Parameter Documents” after the interview).
- **Fallback**: If that file is missing, we could optionally load from `.specify/orchestrator/interview_state.json` → `generated_parameters` (same shape).

### 2. Artifact paths (already in the app)

| Phase         | Artifact path(s)              |
|---------------|-------------------------------|
| constitution  | `.specify/memory/constitution.md` |
| specify       | `specs/<feature>/spec.md`     |
| clarify       | `specs/<feature>/clarifications.md` |
| plan          | `specs/<feature>/plan.md`     |
| tasks         | `specs/<feature>/tasks.md`    |
| analyze       | `specs/<feature>/analysis.md` |

For **constitution**, the path is fixed. For **spec / clarify / plan / tasks / analyze**, we need a **feature directory** under `specs/`. Options:

- Use the **first existing** `specs/*` directory (e.g. `specs/001-my-feature`).
- If none exists, create one (e.g. `specs/001-default` or use project name) so we have a place to write.

### 3. Parameter shape (from interview / YAML)

From `parameter_generator` and `ai_interview`, each phase has:

```yaml
phases:
  constitution:
    command: speckit.constitution
    parameters:
      description: "<long markdown text>"
  specify:
    command: speckit.specify
    parameters:
      description: "<long markdown text>"
  # ... same for clarify, plan, tasks, analyze
```

So for each phase we have at least `parameters.description` (the main body text). We write that (or the full structured content, if we add more fields later) into the corresponding artifact file.

### 4. Proposed flow in the phase runner

For each phase (constitution, specify, clarify, plan, tasks, analyze):

1. **Load parameters**  
   Read `docs/spec-kit-parameters.yml` (and optionally interview_state) for the current project. If no parameters for this phase, skip the “apply” step (current behavior: just run the command).

2. **Resolve artifact path**  
   - Constitution: `project_path / ".specify" / "memory" / "constitution.md"`.  
   - Other phases: pick or create a feature dir under `specs/`, then e.g. `specs/<feature>/spec.md`, `plan.md`, etc.

3. **Write parameter content to artifact**  
   Create parent dirs if needed. Write the phase’s `parameters.description` (or the content we decide to store) to the artifact file. Optionally create a small backup or “last applied” marker if we want to support “re-run without overwriting” later.

4. **Run the phase command**  
   Keep existing logic: run `specify <phase_id>` in the project directory.  
   - If the CLI in the user’s environment supports it, it may do extra work.  
   - If not, we have still **applied** the parameters by writing the artifact, so the repo is in the right state and the user (or the IDE slash command) can use it.

5. **UI**  
   - If we wrote from parameters: show a short message like “Parameters from interview applied to `<path>`; phase command executed.”  
   - If no parameters: current message only (e.g. “Phase completed” or command output).

### 5. When parameters don’t exist

- If there is no `docs/spec-kit-parameters.yml` (and no interview_state with parameters), do **not** write any file; only run `specify <phase>` as today. No change in behavior.

### 6. Edge cases

- **Constitution**: Single file; straightforward.
- **Feature dir**: If there are multiple `specs/*` dirs, we need a rule (e.g. use the first one, or the one matching current branch name if we ever support that). For v1, “first existing or create `001-default`” is enough.
- **Overwrite**: We are explicitly overwriting the artifact with the saved parameters when the user clicks “Run &lt;Phase&gt;”. We could add a confirmation (“Overwrite existing constitution?”) if the file already exists and we’re about to apply parameters; optional for v1.
- **Encoding / format**: Write UTF-8; preserve newlines. Our interview output is already plain text / markdown.

---

## Implementation checklist (high level)

1. **Load saved parameters**
   - Add a small helper (e.g. in a service) that, given `project_path`, returns the current parameters dict: from `docs/spec-kit-parameters.yml`, and optionally from `.specify/orchestrator/interview_state.json` if YAML is missing.

2. **Resolve artifact path**
   - Constitution: fixed path.  
   - Other phases: helper that returns `specs/<feature>/<file>` (first existing feature dir or a default one we create).

3. **Apply parameters before running phase**
   - In the phase runner, when the user clicks “Run &lt;Phase&gt;”:
     - If we have parameters for that phase, write `parameters.description` (or the chosen content) to the artifact path, then run `specify <phase_id>` as today.
     - If we don’t have parameters, run `specify <phase_id>` only.

4. **UI**
   - Optional: show in the phase runner that “Saved parameters will be applied” when `docs/spec-kit-parameters.yml` (or equivalent) exists for that phase. After run, “Parameters applied to …” when we wrote a file.

5. **Tests**
   - Unit tests: load YAML and optional interview_state; path resolution (constitution + one feature dir).  
   - Integration-style: run phase with parameters and assert artifact file content and that the phase command was executed.

---

## Summary

- **Spec Kit CLI** does not accept phase parameters; phases are driven by **slash commands in the IDE** with `$ARGUMENTS`.
- **Straightforward integration**: when the user runs a phase in the orchestrator, **load saved parameters** (YAML or interview_state), **write the parameter text to the known artifact path** for that phase, then **run the existing phase command** (`specify <phase>`). That way the interview output is “applied” regardless of whether the CLI supports that phase subcommand.
- **Constitution** is a single file; **other phases** need a feature dir under `specs/` (use first existing or create a default). No new CLI contract is required; we only read/write files and keep the current phase runner command as-is.

If you want to proceed, the next step is to implement the “load parameters → resolve path → write artifact → run command” flow in the phase runner and the small helper service/utilities above.
