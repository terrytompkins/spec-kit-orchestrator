# Design: Integrating Spec Kit Commands Into Spec Kit Orchestrator

## 1. Purpose

This document captures practical ways for the locally running Spec Kit Orchestrator web app to invoke or replicate Spec Kit command behavior inside the selected project.

It covers three options:

1. Run an in-app orchestrator agent that executes the installed Spec Kit command files.
2. Shell out from the app to an external AI coding agent CLI.
3. Use a future native `specify` phase runner if Spec Kit exposes one.

It also answers a key implementation question:

> Are the Spec Kit templates alone sufficient to replicate the behavior of the Spec Kit slash commands?

Short answer: no. For faithful behavior, templates are only one part of the runtime contract.

## 2. Answer To The Immediate Question

### 2.1 Conclusion

The Spec Kit templates are not sufficient on their own to reproduce the slash-command behavior of `/speckit.clarify`, `/speckit.analyze`, `/speckit.implement`, and the other phase commands.

To replicate the command behavior accurately, an integration needs at least:

- The installed agent command file for the phase, such as `.cursor/commands/speckit.plan.md`
- The `.specify/scripts/` scripts that the command file expects to run
- The `.specify/templates/` templates that the command file reads from or writes against
- An agent runtime capable of following the command instructions, reading files, writing files, and invoking scripts

### 2.2 Why Templates Alone Are Not Enough

In this local project, the installed command files explicitly depend on scripts:

- `.cursor/commands/speckit.specify.md` runs `.specify/scripts/bash/create-new-feature.sh --json ...`
- `.cursor/commands/speckit.clarify.md` runs `.specify/scripts/bash/check-prerequisites.sh --json --paths-only`
- `.cursor/commands/speckit.analyze.md` runs `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
- `.cursor/commands/speckit.plan.md` runs `.specify/scripts/bash/setup-plan.sh --json` and later `.specify/scripts/bash/update-agent-context.sh cursor-agent`

The templates are also part of the workflow, but they are downstream assets rather than the full procedure:

- `.specify/templates/plan-template.md` is copied by `setup-plan.sh`
- `.specify/templates/spec-template.md` is loaded by `/speckit.specify`
- The command files define the execution order, validation logic, stop conditions, and when scripts or templates should be used

That means the effective behavior lives across four layers:

1. Integration-installed command files
2. Spec Kit scripts
3. Spec Kit templates
4. The AI agent that interprets the command file and uses tools

If the orchestrator only reads templates, it can imitate output shape, but it cannot faithfully reproduce:

- feature directory and branch creation
- prerequisite resolution
- feature-path discovery
- plan bootstrapping
- agent-context updates
- the exact decision flow defined in the command markdown

### 2.3 What This Means For Option 1

Option 1 is still viable, but it must execute the command file as the primary source of truth and allow that command file to invoke scripts and use templates. A templates-only implementation would be a partial reimplementation, not a faithful Spec Kit execution.

## 3. Context From This Repository

The current orchestrator app already frames phase execution as a future feature.

- The README describes phase execution as a core capability.
- `src/orchestrator/pages/phase_runner.py` is currently a stub that tells users to run slash commands in the IDE.
- `src/orchestrator/services/cli_executor.py` already provides subprocess execution with streamed output.
- `src/orchestrator/models/phase_execution.py` already models phase runs and metadata.

The local project also contains a real installed integration:

- `.cursor/commands/speckit.specify.md`
- `.cursor/commands/speckit.clarify.md`
- `.cursor/commands/speckit.plan.md`
- `.cursor/commands/speckit.tasks.md`
- `.cursor/commands/speckit.analyze.md`
- `.cursor/commands/speckit.implement.md`

This is useful because it means the orchestrator can inspect actual command files rather than guessing how Spec Kit behaves.

## 4. Option 1: In-App Orchestrator Agent

### 4.1 Summary

The web app runs its own LLM-backed agent loop. Instead of calling a developer's IDE agent, the orchestrator loads the installed Spec Kit command file for the selected phase, injects the generated phase arguments, and lets the in-app agent execute the workflow using controlled tools.

### 4.2 How It Would Work

1. User selects a project and phase in the app.
2. The app loads the phase input from `docs/spec-kit-parameters.yml` or the saved interview state.
3. The app resolves the installed command file for the active integration, for example `.cursor/commands/speckit.plan.md`.
4. The app starts an agent loop with:
   - the command file contents
   - the phase input as `$ARGUMENTS`
   - project context such as root path and current feature directory
5. The agent can call controlled tools such as:
   - read file
   - write file
   - list directory
   - run allowed `.specify/scripts/...` scripts
6. The app streams activity and records the run as execution metadata.

### 4.3 Why This Is The Best Fit

This fits the current orchestrator architecture best because the app already has most of the required building blocks:

- AI service infrastructure for interview and parameter generation
- project path validation
- artifact reading services
- streamed command output patterns
- execution metadata models

This approach also keeps the app self-contained. The user would not need Cursor, Claude Code, or another agent CLI installed on the server running the app.

### 4.4 Required Capabilities

To be faithful to Spec Kit, the orchestrator agent must support more than file generation. It must support:

- command-file interpretation
- script execution under `.specify/scripts/`
- reading and writing Spec Kit artifacts
- interactive stop points when a command expects user clarification
- strict project-root sandboxing

### 4.5 Strengths

- Best user experience inside the app
- No hard dependency on an external IDE or agent CLI
- Full control over logging, validation, and UI
- Can preserve Spec Kit behavior closely if command files and scripts are treated as source of truth

### 4.6 Weaknesses

- Highest implementation complexity
- Requires building a safe agent loop and tool sandbox
- Must track Spec Kit integration changes over time
- Interactive commands like `/speckit.clarify` need multi-turn state management inside the app

### 4.7 Recommended Scope For A First Version

A practical first slice would be:

1. Support `specify`, `plan`, and `analyze` first.
2. Restrict script execution to `.specify/scripts/bash/*.sh` on Linux/macOS.
3. Use the installed integration command files from the active project.
4. Record each tool call and final summary as run metadata.

## 5. Option 2: Shell Out To An External Agent CLI

### 5.1 Summary

The app invokes an external AI coding agent CLI in a subprocess and asks it to run the installed Spec Kit command in the selected project.

Possible examples depend on the agent available in the environment, for example a Copilot, Claude, or other supported CLI.

### 5.2 How It Would Work

1. User clicks a phase in the app.
2. The app resolves the active project and command file.
3. The app launches a supported agent CLI with the command file content and phase arguments.
4. The external agent reads and edits files in the project.
5. The app streams stdout and stderr back to the UI using the existing CLI executor.

### 5.3 Why It Is Attractive

This is simpler than building an in-app agent loop because the coding agent already knows how to interpret command files, manage context, and perform edits.

It also aligns naturally with the existing `CLIExecutor` service.

### 5.4 Main Problems

This approach shifts critical runtime dependencies outside the app:

- the target agent CLI must be installed
- the CLI must be authenticated
- the invocation syntax will be agent-specific
- behavior will vary between CLIs
- server-side hosting becomes harder because the app machine must also be an agent machine

It is also harder to provide a stable, supported product experience when the actual execution engine is an external user tool.

### 5.5 Strengths

- Fastest path to a working prototype
- Reuses existing `CLIExecutor`
- Lets the external agent do the heavy lifting

### 5.6 Weaknesses

- Operationally fragile
- Highly dependent on a specific agent CLI and its auth/session state
- Less predictable across environments
- Harder to make portable for non-technical users

### 5.7 Best Use

This is the best short-term prototype path if the goal is to validate the UX quickly on a developer-controlled machine.

## 6. Option 3: Native `specify` Phase Execution If Spec Kit Adds It

### 6.1 Summary

If Spec Kit eventually exposes a true CLI phase runner, the app should prefer that over agent simulation.

For example, if a future version of Spec Kit provided phase commands such as a `specify run` or equivalent non-agent workflow, the orchestrator could call those commands directly.

### 6.2 How It Would Work

1. User selects a phase.
2. The app maps that phase to a real `specify` CLI command.
3. The app invokes the command with `CLIExecutor`.
4. The app streams output and records results.

### 6.3 Why This Would Be Ideal

This would make the app a thin orchestration layer over an official Spec Kit interface rather than a partial runtime host.

It would remove most of the ambiguity around:

- command semantics
- script invocation
- integration-specific command file formats
- prompt evolution across Spec Kit releases

### 6.4 Strengths

- Lowest long-term maintenance burden
- Most aligned with the official product boundary
- Easiest to reason about and support

### 6.5 Weaknesses

- Not available today based on current public Spec Kit behavior
- Timing and shape depend on upstream Spec Kit evolution

### 6.6 Best Use

Treat this as the preferred long-term architecture if the upstream project adds a supported non-agent phase-execution interface.

## 7. Comparison

| Option | Core Idea | Implementation Cost | Runtime Dependency | Fidelity To Current Spec Kit | Product Stability |
|--------|-----------|---------------------|--------------------|------------------------------|-------------------|
| 1 | In-app agent executes installed command files | High | App-hosted LLM + local scripts | High if command files and scripts are honored | High once built |
| 2 | App shells out to external agent CLI | Medium | External agent CLI | High but agent-specific | Medium to low |
| 3 | App calls official Spec Kit phase CLI | Low to medium | Official `specify` CLI only | Highest | Highest |

## 8. Recommendation

### 8.1 Near-Term Recommendation

The best product-direction choice is Option 1.

Reasoning:

- It matches the orchestrator's goal of giving non-technical users a local web UI.
- It avoids requiring an IDE or agent CLI on the machine hosting the app.
- It can preserve current Spec Kit behavior if the app treats command files, scripts, and templates as runtime inputs rather than reimplementing them.

### 8.2 Prototype Recommendation

If the team wants a fast proof of concept before building the full agent loop, Option 2 is the fastest practical bridge.

### 8.3 Long-Term Recommendation

If upstream Spec Kit introduces an official non-agent execution surface, the app should strongly consider migrating toward Option 3.

## 9. Practical Design Rules For Any Option

Regardless of which option is chosen, the app should follow these rules:

1. Treat the installed Spec Kit integration artifacts as part of the runtime contract.
2. Prefer the active integration's command files over hardcoded assumptions.
3. Allow only sandboxed script execution under `.specify/scripts/`.
4. Keep all paths scoped to the selected project root.
5. Record per-phase execution logs and metadata.
6. Preserve interactive pauses for workflows like clarify rather than forcing one-shot execution.

## 10. Decision Summary

- Templates alone are not enough.
- A faithful solution must account for command files, scripts, templates, and agent behavior together.
- Option 1 is the best overall design for this app.
- Option 2 is the best quick prototype.
- Option 3 is the best future state if Spec Kit exposes an official CLI for phase execution.