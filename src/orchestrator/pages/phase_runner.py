"""Phase runner page — stub until Orchestrator Agent is implemented."""

import sys
from pathlib import Path

# Add parent directory to path for imports when running as Streamlit page
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

# Note: render_navigation_sidebar() is called in app.py, so we don't call it here
# to avoid duplication


def main():
    """Main phase runner page (stub)."""
    st.title("🚀 Run Spec Kit Phases")

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

    st.markdown(
        "**In-app phase execution is planned** (Orchestrator Spec Kit Agent). "
        "For now, run Spec Kit phases in your IDE using the slash commands "
        "(e.g. `/speckit.constitution`, `/speckit.specify`)."
    )
    st.markdown(
        "Use the **Command Parameters** page to review and copy the parameter text for each phase, "
        "then paste it into your IDE after the slash command."
    )
    st.markdown("---")
    if st.button("📋 Open Command Parameters", type="primary"):
        st.switch_page("pages/command_parameters.py")


main()

