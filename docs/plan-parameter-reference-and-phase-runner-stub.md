# Plan: Parameter Reference Page and Phase Runner Stub

## Goal

Until the **Orchestrator Spec Kit Agent** is implemented, the app should:

1. **De-emphasize or replace** the current Phase Runner behavior (which runs `specify <phase>`, a non-existent CLI command) with guidance to run phases in the IDE.
2. **Provide a clear path**: a **markdown file** with copy/paste parameter blocks (already generated) plus a **web page** where users can review all command parameters and copy them directly into their IDE slash commands.
3. Let users **review** parameters and decide whether to re-open the interview for changes or copy from the app into the IDE.

---

## 1. Phase Runner: Stub Until Agent Exists

**Current behavior:** Phase Runner runs `specify <phase_id>` and streams output. That command is not a real Spec Kit CLI subcommand.

**New behavior:**

- **Keep** the "Phase Runner" (or "Run Phases") entry in the sidebar so the workflow (Generate Parameters → Run Phases → Browse Artifacts) still has a place.
- **Replace** the page content with a short, friendly stub:
  - Title: e.g. "Run Phases"
  - Message: In-app phase execution is planned (Orchestrator Agent). For now, run Spec Kit phases in your IDE using the slash commands (e.g. `/speckit.constitution`, `/speckit.specify`). Use the **Command Parameters** page to review and copy the parameter text for each phase, then paste it into your IDE after the slash command.
  - **Button/link**: "Open Command Parameters" → navigates to the new Command Parameters page.
  - Optional: keep the same project header / "Select Project" behavior so the page still requires a selected project and stays consistent with the rest of the app.

No removal of the page from the nav; only the content changes from "run CLI" to "here’s what to do instead."

---

## 2. New Page: Command Parameters (Parameter Reference)

**Purpose:** One place to review all interview-generated parameters and copy them into the IDE.

**Behavior:**

- **Requires a selected project** (same as other pages). If none, show "Select a project" and link to project selection.
- **Load parameters** in this order:
  1. **Primary:** `docs/spec-kit-parameters.yml` in the project (from "Generate Parameter Documents").
  2. **Fallback:** `.specify/orchestrator/interview_state.json` → `generated_parameters` (so parameters are visible even before the user has clicked "Generate Parameter Documents," as long as the interview is complete or in progress).
- If **no parameters** from either source: show a message like "No saved parameters yet. Run the **Interview Chat** to generate parameters, then return here to review and copy them."
- **Display:** One section per phase (constitution, specify, clarify, plan, tasks, analyze). For each phase that has parameters:
  - **Heading:** Phase name (e.g. "Constitution Phase").
  - **Slash command hint:** e.g. "Paste below into your IDE after: `/speckit.constitution`"
  - **Parameter content:** The `description` (or full parameters) in a copy-friendly form—e.g. a text area or a code block with a **Copy** button (Streamlit’s `st.code` plus a copy button, or a pre-filled `st.text_area` that’s read-only).
- **Link:** "Edit in Interview" or "Back to Interview Chat" so users can go back to the interview to make changes, then return to this page to copy again.
- **Short blurb** at the top: "Use these parameters with the Spec Kit slash commands in your IDE. Copy the content for each phase and paste it after the corresponding command (e.g. `/speckit.constitution`)."

**Place in nav:** Add a new sidebar page, e.g. "Command Parameters" or "Parameter Reference," with an icon (e.g. 📋). Order: e.g. after Interview Chat, before Phase Runner (so flow is Interview → Command Parameters → Run Phases (stub)).

---

## 3. Markdown File (Generated) — Optional Enhancement

The app already generates `docs/spec-kit-parameters.md` with a title and per-phase blocks. Optional improvement:

- Add one line at the top after the title: "Paste each block (or the content inside it) into your IDE after the corresponding slash command (e.g. `/speckit.constitution`)."
- No structural change to the blocks; they already suit copy/paste.

---

## 4. Navigation and Copy UX

- **Sidebar order (suggestion):** Home, Select Project, New Project, Interview Chat, **Command Parameters**, Phase Runner, Artifact Browser.
- **Copy:** Use Streamlit’s `st.code(..., language=None)` for each phase’s parameter text; users can select and copy. If we want one-click copy, we can add a "Copy" button that uses `st.session_state` and a small JS snippet or a Streamlit component; otherwise, selecting from the code block is sufficient for v1.

---

## 5. Summary

| Item | Action |
|------|--------|
| Phase Runner page | Replace content with stub: "Run phases in your IDE; use Command Parameters to copy." Link/button to Command Parameters. |
| New page | **Command Parameters**: load params from YAML or interview_state; show per-phase blocks and slash-command hint; link to Interview Chat. |
| Generated markdown | Optional: add one intro line about pasting into the IDE. |
| Nav | Add Command Parameters; keep Phase Runner as stub. |

This gives a single, clear path: interview → generate docs (optional) → open Command Parameters → review and copy into IDE → run slash commands in IDE. Phase Runner stays in the UI as the "run phases" entry point but directs users to that flow until the Orchestrator Agent is implemented.
