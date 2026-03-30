# Interview Session Persistence

The Spec Kit Orchestrator can save and resume the **parameter-document interview** so you can continue on another computer or after restarting the app.

**See also:** [AI interview and parameter extraction](ai-interview-and-parameter-extraction.md) — how interview vs extraction prompts work, completion triggers, token limits, and manual extraction.

## How it works

- **Auto-save**: After every exchange in the AI interview (each question and answer), the session is written to a file in the project.
- **Resume**: When you open the interview page for a project that has a saved session, the app shows **Saved session found** with two options:
  - **Resume** — Load the conversation and continue where you left off.
  - **Start new** — Clear the saved session and begin a new interview.
- **State stored**: The file holds the full conversation, whether the interview is complete, and (if complete) the generated parameters. It does **not** store your API key; you’ll enter that again on a new machine or in a new session if needed.

## Where the state is stored

State is saved in the **project** directory (the Spec Kit project you created or selected), not in the orchestrator app directory:

- **Path**: `<project-root>/.specify/orchestrator/interview_state.json`
- **Contents**: JSON with `version`, `chat_messages`, `interview_complete`, `generated_parameters`, and `saved_at`.

Because this file lives inside the project, you can commit it to the project’s git repo and push/pull to move the session between machines.

## Resuming on another computer

1. On the computer where you were working: push your project repo (including the saved interview state) to GitHub (or your remote).
2. On the other computer: clone or pull the project repo so that `.specify/orchestrator/interview_state.json` is present.
3. Open the orchestrator app, select that project, and go to **Generate Parameter Documents**.
4. When you see **Saved session found**, click **Resume** to load the conversation and continue.

## Recommendation: do not ignore `interview_state.json`

To resume the interview on another computer (or after a fresh clone), the state file must be part of the repo.

- **In the project repo** (the Spec Kit project you create/select), **do not** add `.specify/orchestrator/interview_state.json` to `.gitignore` if you want to sync the interview across machines.
- If your project’s `.gitignore` ignores all of `.specify/` or all of `.specify/orchestrator/`, the state file will not be committed. To allow resume across computers, either:
  - Stop ignoring `.specify/orchestrator/`, or
  - Ignore only specific subpaths (for example `.specify/orchestrator/runs/` for run logs) and leave `interview_state.json` tracked.

Example: to keep run logs out of the repo but keep interview state in, you could have:

```gitignore
# Optional: ignore phase run logs but keep interview state
.specify/orchestrator/runs/
```

and **not** ignore `.specify/orchestrator/interview_state.json`.

## Privacy and security

- The state file contains the full interview text (your answers and the AI’s questions). Don’t commit it if the project repo is public and the conversation is sensitive.
- The file does **not** contain your OpenAI API key; you must enter it again (or use `.env`) on each machine.

## Starting a new interview

- From the **Saved session found** banner: click **Start new** to discard the saved session and start a new interview (the file is overwritten with an empty session).
- After an interview is complete: use **Start New Interview** to clear the current session and start over; the saved state file is also updated so you won’t be prompted to resume that completed interview later.
