# AI interview and parameter extraction

This document describes how the **Generate Parameter Documents** (interview chat) feature uses OpenAI, what prompts are involved, when structured parameters are created, and how limits are configured.

Implementation reference:

- `src/orchestrator/services/ai_interview.py` — prompts, completion logic, extraction, parsing
- `src/orchestrator/pages/interview_chat.py` — UI, session state, manual extraction control
- `src/orchestrator/services/interview_state.py` — persistence to `interview_state.json`

Related: [Interview session persistence](interview-session-persistence.md) (save/resume of the same conversation).

---

## Two separate LLM steps

The feature is **not** one monolithic chat completion. There are two different API calls with different roles.

| Step | When it runs | Purpose |
|------|----------------|---------|
| **Interview turn** | Each time you send a message in the chat (until completion) | Continue the conversation: one assistant reply (question or wrap-up prose). |
| **Parameter extraction** | Only when the app decides the interview should finalize, or when you use **Extract parameters from conversation now** | Take the **full** transcript (system + chat) and produce structured text for all Spec Kit phases in one shot. |

Chat messages you see (including long “### Constitution …” summaries from the assistant) are **plain text** until extraction runs. The orchestrator stores structured parameters in `interview_state.json` only after extraction succeeds (`generated_parameters` plus `interview_complete: true`).

---

## Step 1: Interview turn

### Request shape

For each user message, the app sends to the chat completions API:

1. **System message** — the interview system prompt (see below).
2. **Full conversation so far** — prior user/assistant messages (the current user message is sent as the latest user content in the same request, depending on call site; see code).
3. **No extraction prompt** in this step.

### Interview system prompt (behavioral)

The system prompt defines the interviewer persona: deep product discovery across purpose, requirements, UX, technical context, constraints, and success criteria. It instructs the model to:

- Ask **one** question at a time, probe for depth, and aim for roughly **8–12** meaningful exchanges before wrapping up.
- Map mentally to Spec Kit phases (constitution, specify, clarify, plan, tasks, analyze).
- Prefer **concrete** answers (control names, APIs, platforms, flows) because a later step will encode the transcript into phase parameters.

This text is maintained in code as `AIInterviewService.system_prompt`.

### Interview turn generation settings

| Setting | Value (default) | Notes |
|---------|-----------------|--------|
| Model | `gpt-4o` (constructor default) | Can be changed in code if you instantiate `AIInterviewService` with another model. |
| `temperature` | `0.7` | More varied, conversational follow-up questions. |
| `max_tokens` | `1500` | Cap on the **assistant reply length** for a single turn (not the whole transcript). |

If the assistant hits this cap, the reply may be cut off mid-message; increasing `max_tokens` in `conduct_interview_step` would allow longer questions or summaries per turn.

### What happens after each interview response

The app evaluates **`_should_generate_parameters`** (see below):

- If **false**: the assistant text is shown as the next message, state is saved, chat continues.
- If **true**: the app immediately runs **Step 2 (extraction)** using the conversation that includes this assistant message, then marks the interview complete and saves `generated_parameters`.

---

## When structured parameter creation runs (automatic trigger)

Automatic extraction runs only if **both** are true:

### A. Enough substantive user turns

A “meaningful” user message is one whose trimmed content length is **greater than 20 characters**. The count includes:

- All such user messages already in the history **before** the current turn, **plus**
- The **current** user message, if it also exceeds 20 characters.

Automatic extraction is allowed only when this count is **≥ 6**.

Very short replies (for example “OK” or “yes”) do not increment the count until you send a longer message.

### B. Completion signal (assistant and/or user)

**Assistant message** (latest model reply in that turn): if **any** configured substring appears in the lowercased text, it counts as “explicit intent” to move toward parameters. Examples include phrases like `spec kit command parameters`, `ready to generate`, `generate detailed`, `### constitution`, and several others. The list is intentionally broad so models are not required to say the exact words `generate parameters`.

**User message** (the message you just sent): if **any** configured substring appears in the lowercased text, it counts as the user asking to finalize. Examples include `finalize`, `generate parameters`, `proceed`, `looks good`, `spec kit parameters`, etc. The list avoids a **standalone** match on `generate` so casual phrases like “generate images” are less likely to trigger extraction after enough turns.

The automatic trigger is:

`(assistant_intent AND enough_turns) OR (user_finalize_intent AND enough_turns)`

If the model discusses phase content in chat but **never** matches these patterns (and you do not use a finalize phrase), **`interview_complete` stays false** and `generated_parameters` stays `null` until you use manual extraction.

---

## Manual extraction (UI escape hatch)

On **Generate Parameter Documents**, after **six** meaningful user turns, an expander **“Parameters not finalized automatically?”** offers **Extract parameters from conversation now**.

This calls **`extract_parameters_from_transcript`**, which:

1. Prepends the same interview **system** prompt to the saved `chat_messages`.
2. Runs **one extraction** call (`_generate_parameters`) **without** requiring the completion heuristics above.

Use this when the chat already contains enough detail (including assistant-written phase outlines) but automatic detection did not fire.

---

## Step 2: Parameter extraction

### Request shape

Extraction sends:

1. **Full conversation** — system prompt + every user/assistant message in order, including the latest assistant message when auto-triggered after a turn.
2. A final **user** message containing the **extraction prompt** (instructions to produce `CONSTITUTION:` … `ANALYZE:` blocks).

The extraction prompt instructs the model to treat the **transcript as the only source of truth**, preserve concrete decisions and lists (no thinning into generic boilerplate), place content in the appropriate phase, use `NEEDS CLARIFICATION` when something was not discussed, and emit **dense** markdown-oriented handoff text—not executive summaries.

### Required output format (parsing)

The parser looks for phase headers in the model output, including forms like `CONSTITUTION:`, `Specify:`, etc. Content for each phase is sliced from one header up to the next. If a phase is missing or too short, the code falls back to abbreviated placeholder text derived from user messages in the transcript (you generally want to avoid that by ensuring the model emits all six sections with substance).

### Extraction generation settings

| Setting | Value | Notes |
|---------|-------|--------|
| `temperature` | `0.2` | Steadier, more faithful paraphrase of the transcript. |
| `max_tokens` | `12000` | Upper bound on the **extraction** completion length. Large transcripts plus long phase text can still hit model or context limits; if output truncates, phases may be incomplete or fall back to placeholders. |

**Context window**: The entire conversation is sent again for extraction. Extremely long interviews may approach the model’s **input** token limit; there is no automatic chunking in v1.

### After extraction

- **In memory / JSON**: Each phase becomes an entry like `speckit.<phase>` with a `parameters.description` field holding the extracted prose (see `_parse_parameters`).
- **Optional file export**: **Generate Parameter Documents** on the interview page (after completion) writes `docs/spec-kit-parameters.yml` and the markdown companion via `ParameterGenerator` — that is separate from the extraction call itself.

The **Command Parameters** page reads `docs/spec-kit-parameters.yml` first if present; otherwise it loads `generated_parameters` from `.specify/orchestrator/interview_state.json`.

---

## Summary checklist for operators

1. **OpenAI**: Set `OPENAI_API_KEY` (or sidebar key) for the interview page.
2. **Automatic finish**: At least **six** substantive user replies and either assistant “intent” phrasing or your **finalize** phrasing in the **same** message you send.
3. **Stuck?** Use **Extract parameters from conversation now** after six substantive turns.
4. **Tune behavior**: Adjust prompts, phrase lists, token limits, or model name in `ai_interview.py`; keep the extraction output labels (`CONSTITUTION:` … `ANALYZE:`) compatible with `_parse_parameters` if you change the format.

---

## Version note

Phrase lists and numeric limits are **code constants**, not admin YAML. If you change behavior, update this document alongside `ai_interview.py` so operators and developers stay aligned.
