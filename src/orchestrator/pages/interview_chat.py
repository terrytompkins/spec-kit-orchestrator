"""Interview chat page for generating parameter documents."""

import streamlit as st
from pathlib import Path

from ..services.parameter_generator import ParameterGenerator


def main():
    """Main interview chat page."""
    st.title("💬 Generate Parameter Documents")
    
    # Check if project is selected
    if 'project_path' not in st.session_state or not st.session_state.project_path:
        st.warning("⚠️ No project selected. Please select a project first.")
        if st.button("📁 Select Project"):
            st.switch_page("pages/project_selection.py")
        return
    
    project_path = Path(st.session_state.project_path)
    
    if not project_path.exists():
        st.error(f"❌ Project path does not exist: {project_path}")
        return
    
    generator = ParameterGenerator(project_path)
    
    st.info("""
    **Parameter Document Generation**
    
    This interface helps you generate Spec Kit command parameter documents.
    
    For v1, you can fill out a template form. Full LLM-powered chat integration may be added in a future version.
    """)
    
    # Template-based form (v1 approach)
    with st.form("parameter_form"):
        st.subheader("Project Information")
        
        project_description = st.text_area(
            "Project/Feature Description",
            placeholder="Describe what you want to build...",
            height=100
        )
        
        st.subheader("Phase Parameters")
        
        # Collect parameters for each phase
        parameters = {}
        
        for phase_id, phase_name, phase_desc in [
            ('constitution', 'Constitution', 'Project principles and governance'),
            ('specify', 'Specify', 'Feature specification details'),
            ('clarify', 'Clarify', 'Clarification questions'),
            ('plan', 'Plan', 'Implementation planning context'),
            ('tasks', 'Tasks', 'Task breakdown requirements'),
            ('analyze', 'Analyze', 'Analysis focus areas')
        ]:
            with st.expander(f"{phase_name} Phase Parameters", expanded=(phase_id == 'constitution')):
                phase_params = {}
                
                # Common parameter: description
                phase_params['description'] = st.text_area(
                    f"{phase_name} Description",
                    placeholder=f"Parameters for {phase_name} phase...",
                    key=f"{phase_id}_desc",
                    height=80
                )
                
                # Store parameters
                parameters[phase_id] = {
                    'command': f'speckit.{phase_id}',
                    'parameters': phase_params
                }
        
        submitted = st.form_submit_button("Generate Parameter Documents", type="primary")
    
    if submitted:
        if not project_description:
            st.warning("⚠️ Please provide a project description.")
            return
        
        # Validate parameters
        is_valid, missing = generator.validate_parameters(parameters)
        if not is_valid:
            st.warning(f"⚠️ Missing parameters for phases: {', '.join(missing)}")
            st.info("You can leave phases empty if you'll fill them in later, but all phases should have at least a description.")
        
        # Generate documents
        with st.spinner("Generating parameter documents..."):
            try:
                markdown_path, yaml_path, backup_md, backup_yml = generator.save_parameter_documents(
                    parameters,
                    create_backups=True
                )
                
                st.success("✅ Parameter documents generated successfully!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Markdown**: `{markdown_path.relative_to(project_path)}`")
                with col2:
                    st.markdown(f"**YAML**: `{yaml_path.relative_to(project_path)}`")
                
                if backup_md or backup_yml:
                    st.info("📦 Backups created for existing files (if any)")
                    if backup_md:
                        st.caption(f"Backup: `{backup_md.relative_to(project_path)}`")
                    if backup_yml:
                        st.caption(f"Backup: `{backup_yml.relative_to(project_path)}`")
                
                # Show preview
                with st.expander("Preview Markdown Document"):
                    content = markdown_path.read_text(encoding='utf-8')
                    st.markdown(content)
                
                st.markdown("### Next Steps")
                st.markdown("""
                1. Review the generated parameter documents
                2. Navigate to **Phase Runner** to execute Spec Kit phases
                3. Use the parameter documents as reference when running phases
                """)
            
            except Exception as e:
                st.error(f"❌ Error generating documents: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    main()

