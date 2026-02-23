# Design: Orchestrator Spec Kit Agent

## 1. Overview

### 1.1 Goal

Execute Spec Kit phase workflows (constitution, specify, clarify, plan, tasks, analyze) from the orchestrator app **without bypassing Spec Kit**. The app will run its own **LLM agent** that uses the **same** command files, scripts, and templates that an IDE agent (e.g. Cursor) would use. The orchestrator agent interprets the Spec Kit command file, receives saved parameters as `$ARGUMENTS`, and performs file reads, file writes, and script execution within the project—replicating the IDE agent’s role.

### 1.2 Non-goals

- Reimplementing Spec Kit’s procedure logic in application code.
- Writing raw interview output directly into artifact files (that would bypass Spec Kit).
- Enqueuing jobs for the user to run in the IDE (no handoff / queue).
- Supporting every IDE/agent Spec Kit supports; we use the **command file content** that exists in the project (e.g. `.cursor/commands/` when the project was inited with `--ai cursor-agent`).

### 1.3 Outcome

When the user clicks “Run Constitution” (or another phase) in the Phase Runner:

1. The orchestrator loads the Spec Kit command file for that phase from the project.
2. It loads saved parameters for that phase (from `docs/spec-kit-parameters.yml` or interview state) as `$ARGUMENTS`.
3. It runs an **agent loop**: our LLM is prompted to follow the command file; the agent uses **tools** (read_file, write_file, run_script) to read/write project files and run Spec Kit scripts; we execute those tools and return results until the agent signals completion.
4. Artifacts are produced by the agent following the same procedure and using the same templates/scripts as the IDE would, so we do not bypass Spec Kit.

---

## 2. Rationale

- **Spec Kit CLI** does not expose phase subcommands (`specify constitution`, etc.); phases are designed to run inside an IDE via slash commands.
- **IDE agents** (Cursor, Claude Code, etc.) execute a **command file** (markdown instructions), use **tools** (read file, edit file, run shell), and rely on **Spec Kit’s** templates and scripts. The “logic” is in Spec Kit’s artifacts, not in the IDE.
- By giving our LLM the same command file and the same tools over the same project directory, we **reuse** Spec Kit’s procedure and assets; we only replace “who” runs the procedure (our agent instead of the IDE’s agent).

---

## 3. Architecture

### 3.1 Components

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase Runner UI                                                 │
│  (user clicks "Run Constitution" / "Run Specify" / …)            │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase Execution Controller                                      │
│  - Resolve phase (constitution | specify | clarify | plan | …)   │
│  - Load saved parameters (YAML or interview_state)               │
│  - Resolve command file path (see 4.1)                          │
│  - Invoke Orchestrator Agent                                    │
└────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Orchestrator Agent (new service)                                │
│  - Build prompt: command file + $ARGUMENTS + context           │
│  - Run agent loop with tools (read_file, write_file, run_script) │
│  - Enforce safety (path allowlist, script allowlist)            │
│  - Return success/failure and optional summary                   │
└────────────────────────────┬────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     read_file(path)   write_file(path,   run_script(path,
     (project-scoped)   content)           args)
     (project-scoped)   (project-scoped)
```

### 3.2 Data flow

1. **Inputs**: Project path, phase id, saved parameters (text for that phase), optional feature dir for spec/plan/tasks/clarify/analyze.
2. **Command file**: Read from project (e.g. `.cursor/commands/speckit.<phase>.md`). Content is passed to the LLM as the procedure to follow.
3. **$ARGUMENTS**: The saved parameter text for this phase is substituted into the prompt as the user input (replacing `$ARGUMENTS` in the command file semantics).
4. **Agent loop**: LLM responds with tool calls; we execute tools in the project directory and append results; repeat until LLM returns a final message (e.g. “Phase complete”) or we hit a safety/max-iteration limit.
5. **Outputs**: Updated artifacts in the project (e.g. `.specify/memory/constitution.md`, `specs/<feature>/spec.md`), run metadata (see 9), and a status for the UI.

---

## 4. Context and Inputs

### 4.1 Command file resolution

- Spec Kit is agent-agnostic; `specify init --ai cursor-agent` creates `.cursor/commands/`, `--ai claude` creates `.claude/commands/`, etc.
- **Strategy**: Prefer command files from a single, deterministic agent directory. Options:
  - **A)** Scan project for known agent dirs (`.cursor/commands/`, `.claude/commands/`, …) and use the first that contains `speckit.<phase>.md`. Document that we support “any one” agent’s command set.
  - **B)** Prefer `.cursor/commands/` if present, else fall back to others (or configurable “agent type” in orchestrator config).
- **Path pattern**: `{agent_commands_dir}/speckit.{phase}.md`, e.g. `.cursor/commands/speckit.constitution.md`.
- If no command file is found for the phase, the phase cannot be run by the agent; the UI should show a clear error and avoid calling the agent.

### 4.2 $ARGUMENTS (saved parameters)

- **Primary source**: `docs/spec-kit-parameters.yml` in the project. Structure (existing): `phases.<phase_id>.parameters.description` (and possibly more keys later).
- **Fallback**: `.specify/orchestrator/interview_state.json` → `generated_parameters.<phase_id>.parameters.description`.
- If no parameters are found for the phase, we can still run the agent with empty `$ARGUMENTS` (the command file may allow it) or show a warning and require the user to run the interview first or paste parameters. Design choice: allow “run with empty args” vs “require parameters for agent run.” Recommendation: allow empty; document that best results come from running the interview first.

### 4.3 Feature directory (spec, clarify, plan, tasks, analyze)

- Constitution has a single artifact: `.specify/memory/constitution.md` (no feature dir).
- Other phases write under `specs/<feature>/` (e.g. `specs/001-my-feature/spec.md`).
- **Strategy**:
  - If `specs/` exists and has at least one directory, use the **first** (e.g. alphabetically) as the feature dir for this run. Optionally allow the UI to select feature dir when there are multiple.
  - If `specs/` is empty or missing, the **specify** phase typically creates the feature (e.g. via `create-new-feature.sh`). The agent can run that script with our parameters; we may need to pass feature name/number in context or let the script derive it. Document that “Run Specify” with no existing feature may require the agent to run the create-new-feature script (with our param text as input).
- The agent’s **context** (in the prompt) should include the resolved feature dir when relevant (e.g. “Target feature directory for this run: specs/001-foo.”).

### 4.4 Project path and working directory

- All tool executions (read_file, write_file, run_script) are relative to `project_path`. The agent sees paths relative to the project root (e.g. `.specify/memory/constitution.md`). We resolve to `project_path / path` and enforce that the resolved path is under `project_path` (see Safety).

---

## 5. Tools (function calling)

The agent receives three tools (or four if we add list_dir). All paths are **relative to the project root** and are validated to stay under `project_path`.

### 5.1 read_file

- **Purpose**: Let the agent read the current constitution, templates, scripts, or other project files as specified in the command file.
- **Parameters**: `path` (string, relative to project root).
- **Implementation**: Read `project_path / path` as text (UTF-8). If path escapes project (e.g. `..`) or is not in the allowlist, return an error and do not read.
- **Return**: File contents or an error message (e.g. file not found, permission denied, path not allowed).

### 5.2 write_file

- **Purpose**: Let the agent write the updated constitution, spec, plan, or other artifacts.
- **Parameters**: `path` (string), `content` (string).
- **Implementation**: Resolve `project_path / path`; ensure it is under the project and under an **allowlist** of writable paths (e.g. `.specify/`, `specs/`). Create parent directories if needed. Write content (UTF-8). Do not allow writing outside allowlist (e.g. block `src/`, root-level files, or arbitrary paths).
- **Return**: Success or error (path not allowed, write failed).

### 5.3 run_script

- **Purpose**: Let the agent run Spec Kit’s bash (or PowerShell) scripts as the command file instructs (e.g. `create-new-feature.sh`, `setup-plan.sh`).
- **Parameters**: `script_path` (relative to project root), `args` (array of strings, optional).
- **Implementation**: Resolve `project_path / script_path`. **Allowlist**: only allow scripts under `.specify/scripts/` (e.g. `.specify/scripts/bash/*.sh`). Run the script with `cwd=project_path`, passing `args` as arguments. Capture stdout/stderr and return them to the agent. Do not run scripts outside the allowlist.
- **Return**: `{ "stdout": "...", "stderr": "...", "exit_code": n }` or an error if path not allowed or execution failed.

### 5.4 list_dir (optional)

- **Purpose**: Let the agent discover contents of `specs/`, `.specify/templates/`, etc., when the procedure says “list feature dirs” or similar.
- **Parameters**: `path` (string, relative to project root).
- **Implementation**: List entries under `project_path / path`; do not allow listing outside project or outside an allowlist (e.g. `.specify/`, `specs/`, `docs/`).
- **Return**: List of names (and optionally types) or error.

### 5.5 Safety summary

- **Path allowlist (read)**: Project root and below; optionally restrict to `.specify/`, `specs/`, `docs/`, `README.md`, etc., to avoid reading arbitrary repo code.
- **Path allowlist (write)**: Restrict to `.specify/`, `specs/` (and maybe `docs/` for orchestrator-owned files only). Block `src/`, config outside `.specify/`, etc.
- **Script allowlist**: Only `.specify/scripts/**` (e.g. `.specify/scripts/bash/*.sh`). Reject any path that escapes the project or the allowlist.
- **No arbitrary shell**: `run_script` runs a single script with args, not a free-form shell command.

---

## 6. Prompt Design

### 6.1 System prompt (fixed)

Short, stable instructions, for example:

- You are the **Orchestrator Spec Kit Agent**. You are executing a single Spec Kit phase inside a project. You have the same role as an IDE agent running a Spec Kit slash command.
- You will receive (1) the **command file** for this phase—follow its steps exactly; (2) the **user input** for this phase, which is the value of `$ARGUMENTS`; (3) the **project context** (e.g. project path, feature dir if applicable).
- Use the tools **read_file**, **write_file**, and **run_script** to perform all file and script operations. Do not invent file contents; read what exists and write only what the procedure and your reasoning produce. When the procedure says to run a script, use **run_script** with the path under `.specify/scripts/` and the required arguments.
- Paths in tools are **relative to the project root** (e.g. `.specify/memory/constitution.md`).
- When you have completed all steps in the command file, respond with a final message that includes the phrase “Phase complete” and a one-line summary. Do not make further tool calls after that.

### 6.2 User prompt (per run)

- **Command file contents**: Full text of the chosen `speckit.<phase>.md` (so the LLM sees the exact procedure).
- **$ARGUMENTS**: The saved parameter text for this phase, with a clear label, e.g. “The following is the user input for this phase (treat as $ARGUMENTS): …”.
- **Context**: Project root path (for reference), and if applicable the target feature directory (e.g. “Target feature directory for this run: specs/001-my-feature.”).
- Optional: “If the command file references files or scripts, use your tools to read/run them; they are in the project directory.”

### 6.3 Message shape

- **Messages** sent to the LLM: e.g. `[ { "role": "system", "content": system_prompt }, { "role": "user", "content": user_prompt } ]` for the first turn.
- After tool calls, append: `{ "role": "assistant", "content": null, "tool_calls": [ … ] }`, then for each tool call `{ "role": "tool", "tool_call_id": "...", "content": "..." }`, then get the next assistant message; repeat until the assistant message has no tool calls and indicates completion.

---

## 7. Agent Loop

1. **Initialize**: Build system and user prompts (command file + $ARGUMENTS + context). Set `messages = [system, user]`.
2. **Call LLM**: Request chat completion with `messages` and tool definitions (read_file, write_file, run_script [, list_dir]). Use the same OpenAI (or other) client as the interview chat; support the same model/config (e.g. gpt-4o).
3. **Process response**:
   - If the assistant message has **no tool_calls** and contains a completion phrase (e.g. “Phase complete”), exit loop and return success (and optional summary).
   - If the assistant message has **tool_calls**:
     - For each tool call: validate the tool name and parameters (path allowlists, script allowlist), execute the tool in the project directory, and build a tool result (content string or error).
     - Append the assistant message and all tool results to `messages`, then go to step 2.
4. **Limits**: Max iterations (e.g. 20–30) to avoid runaway loops. If reached, return a timeout/partial-completion status and log the last assistant message.
5. **Errors**: If a tool execution fails (e.g. path not allowed, script not found), return the error as the tool result so the agent can react. If the LLM returns invalid tool args, return a clear error and optionally retry or abort.

---

## 8. Phase Mapping and Command Files

| Phase         | Command file (example)              | Primary artifact(s)                    | Notes |
|---------------|--------------------------------------|----------------------------------------|-------|
| constitution  | `speckit.constitution.md`           | `.specify/memory/constitution.md`      | Single artifact; no feature dir. |
| specify       | `speckit.specify.md`                | `specs/<feature>/spec.md`              | May run `create-new-feature.sh`; feature dir may be created by script. |
| clarify       | `speckit.clarify.md`                | `specs/<feature>/clarifications.md`    | Feature dir required. |
| plan          | `speckit.plan.md`                   | `specs/<feature>/plan.md`              | Feature dir required; may run `setup-plan.sh`. |
| tasks         | `speckit.tasks.md`                  | `specs/<feature>/tasks.md`             | Feature dir required. |
| analyze       | `speckit.analyze.md`                 | `specs/<feature>/analysis.md`          | Feature dir required. |

- Not all projects will have every command file (e.g. older Spec Kit or minimal init). The UI or controller should only offer “Run &lt;Phase&gt;” when the corresponding command file exists (and optionally when parameters exist for that phase).

---

## 9. Integration with Existing App

### 9.1 Phase Runner

- **Current behavior**: On “Run &lt;Phase&gt;”, the app runs `specify <phase_id>` and streams output. That command is not a real Spec Kit CLI subcommand in the public CLI.
- **New behavior (when agent is enabled)**:
  1. Resolve command file for the phase; if missing, show error or fall back to “run `specify <phase_id>`” (current behavior) and document that the agent path requires the command file.
  2. Load saved parameters for the phase (YAML or interview_state); pass them as $ARGUMENTS (or empty).
  3. Resolve feature dir for spec/clarify/plan/tasks/analyze (see 4.3).
  4. Call the **Orchestrator Agent** service with: project_path, phase_id, $ARGUMENTS, feature_dir (if applicable), API key (reuse interview’s key or config).
  5. Run the agent loop; stream or show progress (e.g. “Running phase…”, “Tool: read_file …”, “Tool: write_file …”) if feasible.
  6. On success: show “Phase completed” and optional summary; refresh artifact list / status. On failure or timeout: show error and last state.
  7. **Execution metadata**: Create a run record in `.specify/orchestrator/runs/<timestamp>/` as today (phase name, command = “orchestrator-agent”, args = phase_id, timestamps, exit status). Optionally store a short log of tool calls and final outcome for debugging.

### 9.2 When to use the agent

- **Use agent**: When the project has the Spec Kit command file for that phase (and we have implemented the agent for that phase). Optionally require that the project was inited with an agent type we support (e.g. Cursor).
- **Do not use agent**: When the command file is missing, or when the user explicitly chooses “Run via CLI only” if we offer that option. Fallback can remain “run `specify <phase_id>`” for compatibility.

### 9.3 Dependencies and parameters

- Reuse **OpenAI API key** (or configured LLM) from the interview chat / app config.
- Reuse **ParameterGenerator** (or equivalent) only for **loading** parameters (YAML/interview_state); we do not call `save_parameter_documents` from the agent path.
- **RunMetadata**: Reuse for recording agent runs (phase, “orchestrator-agent”, timestamps, success/failure). Tool call log can be a separate file in the run directory (e.g. `agent_tool_calls.json` or `agent_log.txt`).

---

## 10. Error Handling and Timeouts

- **Tool errors**: Returned to the agent as tool result text; the agent can retry or report failure. We do not abort the loop on a single tool error unless we decide to (e.g. “write_file not allowed” could be fatal).
- **LLM errors**: Network, rate limit, or model errors should abort the loop and return a clear error to the UI (e.g. “Phase run failed: …”).
- **Max iterations**: After N turns (e.g. 25), stop and report “Phase run did not complete within the iteration limit.” Optionally save partial state (e.g. last messages) for debugging.
- **Timeouts**: Set a total wall-clock timeout for the entire agent run (e.g. 2–5 minutes) in addition to iteration limit.

---

## 11. Security and Safety (recap)

- **Path validation**: All tool paths are resolved as `project_path / path`. Reject if the resolved path is not under `project_path` or not under the allowlist for read/write/script.
- **Write allowlist**: Only under `.specify/`, `specs/` (and optionally `docs/` for known files). Prevents overwriting application code or config.
- **Script allowlist**: Only scripts under `.specify/scripts/` (e.g. `.specify/scripts/bash/*.sh`). No arbitrary bash -c or system commands.
- **No secrets in prompts**: Do not inject API keys or tokens into the user prompt; the agent only sees project-relative paths and $ARGUMENTS (saved parameter text).
- **Logging**: Do not log full file contents in production; log tool names and paths only, or redact content.

---

## 12. Testing Approach

- **Unit**:
  - Command file resolution: given a project path and phase, return the correct command file path or None.
  - Parameter loading: from YAML and from interview_state; fallback order.
  - Path allowlist: reject `../`, paths outside project, paths outside writable/script dirs; accept valid `.specify/` and `specs/` paths.
  - Tool execution (mocked): read_file/write_file/run_script with a temp project dir; assert allowlist behavior and file contents.
- **Integration**:
  - Run the agent for **constitution** in a test project that has `.cursor/commands/speckit.constitution.md` and a minimal constitution template; provide fixed $ARGUMENTS; assert that the constitution file is updated and no tools are called outside allowlist. Use a small/fast model or mock LLM for CI if needed.
- **Manual**: Run constitution and specify in a real Spec Kit project and compare artifact quality to running the same phase in the IDE.

---

## 13. Open Questions and Future Work

- **Agent directory preference**: Prefer `.cursor/commands/` only, or scan all known agent dirs? May depend on how often users mix agents.
- **Empty $ARGUMENTS**: Allow running with no saved parameters (agent may still do something from repo context) vs require parameters; and whether to show a warning in the UI.
- **Streaming**: Stream agent responses or tool calls to the UI for long-running phases (e.g. specify, plan).
- **Multi-feature**: When `specs/` has multiple dirs, allow user to pick feature in the UI and pass it to the agent.
- **Spec Kit upgrades**: Command file format or new steps may change with Spec Kit versions. Document that we follow “command file as written in the project”; if Spec Kit changes the procedure, the user updates the project (e.g. re-run specify init or pull template updates), and our agent will follow the new file. No separate “orchestrator version” of the procedure.

---

## 14. Summary

The orchestrator runs an **in-app LLM agent** that:

1. Receives the **Spec Kit command file** for the chosen phase and **saved parameters** as `$ARGUMENTS`.
2. Uses **tools** (read_file, write_file, run_script) to perform the same file and script operations an IDE agent would, within strict **path and script allowlists**.
3. Follows the **same procedure** (templates, scripts, propagation) as the IDE, so we **do not bypass Spec Kit**.
4. Integrates with the **Phase Runner** and **saved parameters** (YAML / interview state), with clear fallback when the command file is missing or the user prefers CLI-only.

This design is intended to be implementable later with this document as the single source of truth for the “Orchestrator Spec Kit Agent” feature.
