"""Command Parameters page: review and copy interview-generated parameters for IDE slash commands."""

import sys
from pathlib import Path

# Add parent directory to path for imports when running as Streamlit page
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from orchestrator.utils.yaml_parser import load_yaml
from orchestrator.services import interview_state as interview_state_service

# Phase display order and slash command names
PHASES = [
    ("constitution", "Constitution", "speckit.constitution"),
    ("specify", "Specify", "speckit.specify"),
    ("clarify", "Clarify", "speckit.clarify"),
    ("plan", "Plan", "speckit.plan"),
    ("tasks", "Tasks", "speckit.tasks"),
    ("analyze", "Analyze", "speckit.analyze"),
]


def load_parameters(project_path: Path) -> tuple[dict | None, str]:
    """
    Load parameters from docs/spec-kit-parameters.yml or interview_state.json.

    Returns:
        (parameters_dict, source) where source is "yaml" | "interview" | None.
        parameters_dict is phase_id -> { "command": ..., "parameters": { ... } }.
    """
    yaml_path = project_path / "docs" / "spec-kit-parameters.yml"
    if yaml_path.exists():
        try:
            data = load_yaml(yaml_path)
            phases = data.get("phases") or {}
            if phases:
                return phases, "yaml"
        except Exception:
            pass

    state = interview_state_service.load(project_path)
    if state:
        gen = state.get("generated_parameters")
        if gen and isinstance(gen, dict):
            return gen, "interview"

    return None, ""


def format_parameter_content(phase_data: dict) -> str:
    """Format phase parameters as plain text for copy (description or full params)."""
    params = phase_data.get("parameters") or {}
    if not params:
        return ""
    parts = []
    for key, value in params.items():
        if isinstance(value, str):
            if "\n" in value:
                parts.append(f"{key}:\n{value}")
            else:
                parts.append(f"{key}: {value}")
        else:
            parts.append(f"{key}: {value}")
    return "\n\n".join(parts)


def main():
    """Command Parameters page."""
    st.title("📋 Command Parameters")

    if st.session_state.get("selected_project"):
        st.info(f"📂 **Current Project**: {st.session_state.selected_project}")
        if st.session_state.get("project_path"):
            st.caption(f"Path: `{st.session_state.project_path}`")
        st.markdown("---")

    if "project_path" not in st.session_state or not st.session_state.project_path:
        st.warning("⚠️ No project selected. Please select a project first.")
        if st.button("📁 Select Project"):
            st.switch_page("pages/project_selection.py")
        return

    project_path = Path(st.session_state.project_path)
    if not project_path.exists():
        st.error(f"❌ Project path does not exist: {project_path}")
        return

    parameters, source = load_parameters(project_path)

    if not parameters:
        st.info(
            "No saved parameters yet. Run the **Interview Chat** to generate parameters, "
            "then return here to review and copy them into your IDE."
        )
        if st.button("💬 Open Interview Chat"):
            st.switch_page("pages/interview_chat.py")
        return

    if source == "yaml":
        st.caption("Loaded from **docs/spec-kit-parameters.yml** (generated parameter documents).")
    else:
        st.caption("Loaded from **saved interview state** (not yet saved to docs). Click **Generate Parameter Documents** in Interview Chat to write docs/spec-kit-parameters.yml.")

    st.markdown(
        "Use these parameters with the Spec Kit slash commands in your IDE. "
        "Copy the content for each phase and paste it **after** the corresponding slash command "
        "(e.g. `/speckit.constitution`)."
    )
    st.markdown("---")

    for phase_id, phase_name, slash_cmd in PHASES:
        if phase_id not in parameters:
            continue
        phase_data = parameters[phase_id]
        content = format_parameter_content(phase_data)
        if not content.strip():
            continue

        with st.expander(f"**{phase_name}** — `/speckit.{phase_id}`", expanded=(phase_id == "constitution")):
            st.markdown(f"**Paste below into your IDE after:** `/{slash_cmd}`")
            st.code(content, language=None)

    st.markdown("---")
    st.markdown("**Want to change something?** Re-run the interview, then return here to copy the updated parameters.")
    if st.button("💬 Edit in Interview Chat"):
        st.switch_page("pages/interview_chat.py")


main()
