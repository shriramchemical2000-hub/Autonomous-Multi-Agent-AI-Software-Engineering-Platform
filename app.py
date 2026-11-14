"""ForgeAI — human-supervised AI software engineering workspace."""
from __future__ import annotations

import io
import zipfile

import streamlit as st

from forgeai.agents.contracts import AgentContext
from forgeai.agents.requirements_analyst import AgentExecutionError
from forgeai.agents.software_architect import AgentExecutionError as ArchitectExecutionError
from forgeai.agents.uiux_designer import AgentExecutionError as UIUXExecutionError
from forgeai.agents.code_generator import AgentExecutionError as CodeGenExecutionError
from forgeai.agents.qa_engineer import AgentExecutionError as QAExecutionError
from forgeai.agents.code_reviewer import AgentExecutionError as ReviewExecutionError
from forgeai.config import get_settings
from forgeai.database import (
    add_project_event,
    create_project,
    get_latest_project_artifact,
    initialize_database,
    list_project_events,
    list_projects,
    review_project_artifact,
    save_project_artifact,
)
from forgeai.providers.base import ModelProviderError
from forgeai.providers.gemini import GeminiProvider
from forgeai.orchestration.workflow import build_forge_workflow
from forgeai.execution.docker_runner import DockerTestRunner, docker_runner_enabled
from forgeai.delivery import ARTIFACT_TYPES, build_delivery_archive, build_delivery_report

settings = get_settings()
initialize_database(settings.database_path)

st.set_page_config(
    page_title="ForgeAI | AI Software Engineering",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1450px; }
      .hero { padding: 1.6rem 1.8rem; border: 1px solid rgba(128,128,128,.25);
              border-radius: 16px; background: linear-gradient(115deg,
              rgba(74,115,180,.13), rgba(100,80,160,.06)); margin-bottom: 1.2rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .13em; font-size: .72rem;
                 font-weight: 700; opacity: .7; }
      .muted { opacity: .72; }
      .phase { border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
               padding: 1rem; min-height: 118px; }
    </style>
    """,
    unsafe_allow_html=True,
)

projects = list_projects(settings.database_path)

with st.sidebar:
    st.markdown("## ⚙️ ForgeAI")
    st.caption("Autonomous Multi-Agent Software Engineering")
    page = st.radio(
        "Workspace",
        ["Overview", "Product Studio", "Delivery Center", "Agent Command Center", "Project Memory", "Settings"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("PHASE 10 · DELIVERY & RELEASE")
    st.caption("Seven executable specialists are coordinated through approval-gated LangGraph stages.")


def render_requirements(document: dict) -> None:
    """Render the complete validated requirements artifact, not just its summary."""
    st.subheader(document["product_name"])
    st.markdown("**Problem statement**")
    st.write(document["problem_statement"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Target users**")
        for item in document["target_users"]:
            st.markdown(f"- {item}")
        st.markdown("**Included in scope**")
        for item in document["scope_in"]:
            st.markdown(f"- {item}")
    with right:
        st.markdown("**Outside scope**")
        for item in document["scope_out"]:
            st.markdown(f"- {item}")
        st.markdown("**Assumptions to confirm**")
        for item in document["assumptions"]:
            st.markdown(f"- {item}")
    st.divider()
    st.markdown("### Functional requirements")
    if document["functional_requirements"]:
        for item in document["functional_requirements"]:
            with st.expander(
                f"{item['requirement_id']} · {item['title']} · {item['priority'].upper()}",
                expanded=True,
            ):
                st.write(item["description"])
                st.markdown("**Acceptance criteria**")
                for criterion in item["acceptance_criteria"]:
                    st.markdown(f"- {criterion}")
    else:
        st.info("No functional requirements were returned. Review the brief and open questions.")
    st.markdown("### User stories")
    if document["user_stories"]:
        for story in document["user_stories"]:
            with st.expander(f"{story['story_id']} · As a {story['persona']}", expanded=True):
                st.write(f"As a {story['persona']}, I want to {story['action']}, so that {story['benefit']}")
                st.markdown("**Acceptance criteria**")
                for criterion in story["acceptance_criteria"]:
                    st.markdown(f"- {criterion}")
                st.caption("Related requirements: " + (", ".join(story["related_requirement_ids"]) or "Not linked"))
    else:
        st.info("No user stories were returned.")
    st.markdown("### Non-functional requirements")
    for item in document["non_functional_requirements"]:
        st.markdown(f"- {item}")
    st.markdown("### Open questions")
    if document["open_questions"]:
        for item in document["open_questions"]:
            st.markdown(f"- {item}")
    else:
        st.success("No open questions were identified by the analyst.")


if page == "Overview":
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">AI SOFTWARE ENGINEERING PLATFORM</div>
          <h1 style="margin:.45rem 0">From product brief to engineered software.</h1>
          <p class="muted">A human-supervised workspace for coordinated AI engineering,
          traceable decisions, implementation, testing, and delivery.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Projects created", len(projects))
    c2.metric("Specialist roles designed", "9")
    c3.metric("Executable specialists", "7")
    st.subheader("Engineering workflow")
    stages = [
        ("01 · Discover", "Convert the product idea into structured requirements."),
        ("02 · Architect", "Define system boundaries, data, APIs, and design decisions."),
        ("03 · Build", "Generate implementation tasks and controlled code artifacts."),
        ("04 · Validate", "Run tests, inspect defects, and review code quality."),
        ("05 · Approve & deliver", "Keep people in control of consequential decisions."),
    ]
    cols = st.columns(len(stages))
    for col, (heading, description) in zip(cols, stages):
        with col:
            st.markdown(
                f'<div class="phase"><b>{heading}</b><p class="muted">{description}</p></div>',
                unsafe_allow_html=True,
            )
    st.subheader("Recent projects")
    if projects:
        st.dataframe(
            [{"ID": p["id"], "Project": p["name"], "Status": p["status"], "Created": p["created_at"]}
             for p in projects[:8]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No projects yet. Open Product Studio to create your first engineering workspace.")

elif page == "Product Studio":
    st.title("Product Studio")
    st.write("Move a product from requirements through architecture and experience design into a reviewable source-code bundle. Every downstream stage is approval-gated.")
    with st.form("new_project_form", clear_on_submit=True):
        name = st.text_input("Project name", placeholder="e.g. Hospital Appointment Platform")
        brief = st.text_area(
            "Product brief", height=180,
            placeholder="Describe the problem, target users, key capabilities, constraints, and desired outcome...",
        )
        submitted = st.form_submit_button("Create project workspace", type="primary")
    if submitted:
        if not name.strip():
            st.error("Enter a project name before continuing.")
        elif not brief.strip():
            st.error("Add a product brief so the analyst has enough context.")
        else:
            project_id = create_project(settings.database_path, name, brief)
            st.success(f"Project workspace created — ID {project_id}.")
            st.rerun()

    st.divider()
    st.subheader("Requirements Analyst")
    selected = None
    if not projects:
        st.info("Create a project workspace above to enable requirements generation.")
    else:
        selected = st.selectbox(
            "Select a project",
            projects,
            format_func=lambda p: f"#{p['id']} · {p['name']}",
            key="requirements_project",
        )
        st.caption("The analyst uses the saved project brief and returns a structured specification. Generation requires a Gemini API key.")
        if not settings.has_model_api_key:
            st.warning("Gemini API key not configured. Add GEMINI_API_KEY to your environment variables or a local .env file to enable generation. No key is needed to browse the app.")
        if st.button("Generate requirements", type="primary", disabled=not settings.has_model_api_key):
            with st.spinner("Requirements Analyst is preparing and validating the specification..."):
                try:
                    context = AgentContext(project_id=selected["id"], user_request=selected["brief"])
                    workflow = build_forge_workflow(GeminiProvider(settings))
                    workflow_result = workflow.invoke({
                        "project_id": selected["id"],
                        "user_request": selected["brief"],
                        "requested_stage": "requirements",
                    })
                    artifact_id = save_project_artifact(
                        settings.database_path,
                        selected["id"],
                        "requirements",
                        workflow_result["requirements"],
                    )
                    add_project_event(
                        settings.database_path,
                        selected["id"],
                        "requirements_agent_completed",
                        workflow_result["summary"],
                    )
                    st.session_state["forgeai_last_artifact_id"] = artifact_id
                    st.success(workflow_result["summary"])
                    for warning in workflow_result.get("warnings", []):
                        st.warning(warning)
                    st.rerun()
                except (AgentExecutionError, ArchitectExecutionError, UIUXExecutionError, ModelProviderError, ValueError) as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Requirements generation failed ({type(exc).__name__}). Check the app logs and configuration.")

        artifact = get_latest_project_artifact(settings.database_path, selected["id"], "requirements")
        if artifact:
            st.divider()
            st.markdown("## Generated requirements specification")
            status = artifact["review_status"]
            st.caption(f"Version {artifact['version']} · Generated {artifact['created_at']} · Review status: {status.replace('_', ' ').title()}")
            render_requirements(artifact["content"])
            if status == "pending":
                st.divider()
                st.markdown("### Human approval")
                st.write("Review the complete specification above. Approval records your decision; requesting changes records feedback for the next revision.")
                review_notes = st.text_area("Review notes (optional)", key=f"review_notes_{artifact['id']}")
                approve_col, changes_col = st.columns(2)
                with approve_col:
                    if st.button("Approve requirements", type="primary", key=f"approve_{artifact['id']}"):
                        review_project_artifact(settings.database_path, artifact["id"], "approved", review_notes)
                        st.success("Requirements approved and decision recorded.")
                        st.rerun()
                with changes_col:
                    if st.button("Request changes", key=f"changes_{artifact['id']}"):
                        if not review_notes.strip():
                            st.error("Add notes describing the changes needed.")
                        else:
                            review_project_artifact(settings.database_path, artifact["id"], "changes_requested", review_notes)
                            st.warning("Change request recorded. The analyst has not automatically regenerated the specification.")
                            st.rerun()
            else:
                st.info(f"Human decision: {status.replace('_', ' ').title()}. {artifact['review_notes']}")

    if selected:
        st.divider()
        st.subheader("Software Architect")
        approved_requirements = get_latest_project_artifact(settings.database_path, selected["id"], "requirements")
        if not approved_requirements or approved_requirements["review_status"] != "approved":
            st.info("The Software Architect is unlocked after you approve the Requirements Analyst specification. This approval gate prevents architecture from being built on unreviewed requirements.")
        else:
            st.caption("The architect uses the approved requirements as its source of truth. It proposes system components, data entities, API contracts, security considerations, design decisions, and unresolved risks.")
            if st.button("Generate architecture", type="primary", key=f"generate_architecture_{selected['id']}", disabled=not settings.has_model_api_key):
                with st.spinner("Software Architect is designing and validating the system architecture..."):
                    try:
                        context = AgentContext(
                            project_id=selected["id"],
                            user_request=f"Create an architecture for {approved_requirements['content'].get('product_name', selected['name'])}.",
                            prior_artifacts={"requirements": approved_requirements["content"]},
                        )
                        workflow = build_forge_workflow(GeminiProvider(settings))
                        workflow_result = workflow.invoke({
                            "project_id": selected["id"],
                            "user_request": selected["brief"],
                            "requested_stage": "architecture",
                            "requirements": approved_requirements["content"],
                            "requirements_approved": approved_requirements["review_status"] == "approved",
                        })
                        save_project_artifact(settings.database_path, selected["id"], "architecture", workflow_result["architecture"])
                        add_project_event(settings.database_path, selected["id"], "software_architect_completed", workflow_result["summary"])
                        st.success(workflow_result["summary"])
                        for warning in workflow_result.get("warnings", []):
                            st.warning(warning)
                        st.rerun()
                    except (AgentExecutionError, ArchitectExecutionError, ModelProviderError, ValueError) as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Architecture generation failed ({type(exc).__name__}). Check the app logs and configuration.")
    
            architecture = get_latest_project_artifact(settings.database_path, selected["id"], "architecture")
            if architecture:
                st.markdown("### Generated system architecture")
                st.caption(f"Version {architecture['version']} · Review status: {architecture['review_status'].replace('_', ' ').title()}")
                design = architecture["content"]
                st.markdown("**System overview**")
                st.write(design["system_overview"])
                st.markdown("### Architecture components")
                for component in design["components"]:
                    with st.expander(component["name"], expanded=True):
                        st.write(component["responsibility"])
                        st.caption("Technology: " + (component["technology"] or "Not specified"))
                        st.caption("Dependencies: " + (", ".join(component["dependencies"]) or "None listed"))
                st.markdown("### Data entities")
                for entity in design["data_entities"]:
                    st.markdown(f"- {entity}")
                st.markdown("### API contract")
                if design["api_endpoints"]:
                    st.dataframe(
                        [
                            {
                                "Method": endpoint["method"],
                                "Path": endpoint["path"],
                                "Purpose": endpoint["purpose"],
                                "Authentication": "Required" if endpoint["authentication_required"] else "Not required",
                            }
                            for endpoint in design["api_endpoints"]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No API endpoints proposed.")
                for heading, key in [
                    ("Security considerations", "security_considerations"),
                    ("Design decisions and trade-offs", "design_decisions"),
                    ("Unresolved risks", "unresolved_risks"),
                ]:
                    st.markdown(f"### {heading}")
                    for item in design[key]:
                        st.markdown(f"- {item}")
                if architecture["review_status"] == "pending":
                    st.markdown("### Architecture approval")
                    architecture_notes = st.text_area("Architecture review notes (optional)", key=f"architecture_notes_{architecture['id']}")
                    approve_arch_col, change_arch_col = st.columns(2)
                    with approve_arch_col:
                        if st.button("Approve architecture", type="primary", key=f"approve_arch_{architecture['id']}"):
                            review_project_artifact(settings.database_path, architecture["id"], "approved", architecture_notes)
                            st.success("Architecture approval recorded.")
                            st.rerun()
                    with change_arch_col:
                        if st.button("Request architecture changes", key=f"request_arch_{architecture['id']}"):
                            if not architecture_notes.strip():
                                st.error("Add notes describing the architecture changes needed.")
                            else:
                                review_project_artifact(settings.database_path, architecture["id"], "changes_requested", architecture_notes)
                                st.warning("Architecture change request recorded. Automatic redesign is not implemented yet.")
                                st.rerun()
                else:
                    st.info(f"Architecture decision: {architecture['review_status'].replace('_', ' ').title()}. {architecture['review_notes']}")
    
        st.divider()
        st.subheader("UI/UX Designer")
        approved_architecture = get_latest_project_artifact(settings.database_path, selected["id"], "architecture")
        if (
            not approved_requirements
            or approved_requirements["review_status"] != "approved"
            or not approved_architecture
            or approved_architecture["review_status"] != "approved"
        ):
            st.info("The UI/UX Designer is unlocked only after both the latest requirements and architecture artifacts are approved.")
        else:
            st.caption("The designer converts the two approved engineering artifacts into user journeys, navigation, detailed screen specifications, reusable components, design tokens, responsive rules, and accessibility requirements.")
            if st.button("Generate UI/UX design", type="primary", key=f"generate_uiux_{selected['id']}", disabled=not settings.has_model_api_key):
                with st.spinner("UI/UX Designer is preparing the product experience specification..."):
                    try:
                        workflow = build_forge_workflow(GeminiProvider(settings))
                        workflow_result = workflow.invoke({
                            "project_id": selected["id"],
                            "user_request": selected["brief"],
                            "requested_stage": "uiux",
                            "requirements": approved_requirements["content"],
                            "requirements_approved": approved_requirements["review_status"] == "approved",
                            "architecture": approved_architecture["content"],
                            "architecture_approved": approved_architecture["review_status"] == "approved",
                        })
                        save_project_artifact(settings.database_path, selected["id"], "uiux_design", workflow_result["uiux_design"])
                        add_project_event(settings.database_path, selected["id"], "uiux_designer_completed", workflow_result["summary"])
                        st.success(workflow_result["summary"])
                        for warning in workflow_result.get("warnings", []):
                            st.warning(warning)
                        st.rerun()
                    except (AgentExecutionError, ArchitectExecutionError, UIUXExecutionError, ModelProviderError, ValueError) as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"UI/UX design generation failed ({type(exc).__name__}). Check the app logs and configuration.")
    
            design_artifact = get_latest_project_artifact(settings.database_path, selected["id"], "uiux_design")
            if design_artifact:
                design = design_artifact["content"]
                st.markdown("### Product experience specification")
                st.caption(f"Version {design_artifact['version']} · Review status: {design_artifact['review_status'].replace('_', ' ').title()}")
                st.markdown("**Design overview**")
                st.write(design["design_overview"])
                st.markdown("### Design goals and personas")
                for item in design["design_goals"]:
                    st.markdown(f"- {item}")
                for item in design["personas"]:
                    st.markdown(f"- Persona: {item}")
                st.markdown("### Navigation structure")
                st.write(" → ".join(design["navigation_structure"]))
                st.markdown("### User journeys")
                for journey in design["user_journeys"]:
                    with st.expander(f"{journey['persona']} · {journey['goal']}", expanded=True):
                        st.caption(f"Entry point: {journey['entry_point']}")
                        for step in journey["steps"]:
                            st.markdown(f"{step['step']}. **{step['user_action']}** — {step['system_response']}")
                            if step["decision_or_exception"]:
                                st.caption(f"Decision / exception: {step['decision_or_exception']}")
                        st.success(journey["success_outcome"])
                st.markdown("### Screen-by-screen specifications")
                for screen in design["screen_specifications"]:
                    with st.expander(screen["screen_name"], expanded=True):
                        st.write(screen["purpose"])
                        st.caption(f"Primary user: {screen['primary_user']}")
                        st.markdown("**Layout regions**")
                        for item in screen["layout_regions"]:
                            st.markdown(f"- {item}")
                        st.markdown("**Key components**")
                        for item in screen["key_components"]:
                            st.markdown(f"- {item}")
                        st.markdown(f"**Primary action:** {screen['primary_action']}")
                        st.markdown("**States and feedback**")
                        for item in screen["states_and_feedback"]:
                            st.markdown(f"- {item}")
                        st.markdown("**Validation and errors**")
                        for item in screen["validation_and_errors"]:
                            st.markdown(f"- {item}")
                st.markdown("### Reusable UI components")
                for component in design["reusable_components"]:
                    with st.expander(component["component_name"]):
                        st.write(component["purpose"])
                        st.write(component["behaviour"])
                        for item in component["accessibility_notes"]:
                            st.caption(item)
                st.markdown("### Design system")
                system = design["design_system"]
                for heading, key in [
                    ("Colour tokens", "colour_tokens"),
                    ("Typography scale", "typography_scale"),
                    ("Spacing and layout rules", "spacing_and_layout_rules"),
                    ("Visual principles", "visual_principles"),
                    ("Responsive behaviour", None),
                    ("Accessibility requirements", None),
                    ("Usability risks", None),
                    ("Open design questions", None),
                ]:
                    st.markdown(f"**{heading}**")
                    values = system[key] if key else design[{
                        "Responsive behaviour": "responsive_behaviour",
                        "Accessibility requirements": "accessibility_requirements",
                        "Usability risks": "usability_risks",
                        "Open design questions": "open_design_questions",
                    }[heading]]
                    for item in values:
                        st.markdown(f"- {item}")
                if design_artifact["review_status"] == "pending":
                    st.markdown("### Human design approval")
                    uiux_notes = st.text_area("Design review notes (optional)", key=f"uiux_notes_{design_artifact['id']}")
                    approve_uiux_col, changes_uiux_col = st.columns(2)
                    with approve_uiux_col:
                        if st.button("Approve UI/UX design", type="primary", key=f"approve_uiux_{design_artifact['id']}"):
                            review_project_artifact(settings.database_path, design_artifact["id"], "approved", uiux_notes)
                            st.success("UI/UX design approval recorded.")
                            st.rerun()
                    with changes_uiux_col:
                        if st.button("Request UI/UX changes", key=f"request_uiux_{design_artifact['id']}"):
                            if not uiux_notes.strip():
                                st.error("Add notes describing the design changes needed.")
                            else:
                                review_project_artifact(settings.database_path, design_artifact["id"], "changes_requested", uiux_notes)
                                st.warning("Design change request recorded. Automatic redesign is not implemented yet.")
                                st.rerun()
                else:
                    st.info(f"Design decision: {design_artifact['review_status'].replace('_', ' ').title()}. {design_artifact['review_notes']}")
    
    
        st.divider()
        st.subheader("Controlled Code Generator")
        latest_requirements = get_latest_project_artifact(settings.database_path, selected["id"], "requirements")
        latest_architecture = get_latest_project_artifact(settings.database_path, selected["id"], "architecture")
        latest_uiux = get_latest_project_artifact(settings.database_path, selected["id"], "uiux_design")
        upstream_ready = all([
            latest_requirements and latest_requirements["review_status"] == "approved",
            latest_architecture and latest_architecture["review_status"] == "approved",
            latest_uiux and latest_uiux["review_status"] == "approved",
        ])
        if not upstream_ready:
            st.info("Code generation unlocks only after the latest requirements, architecture, and UI/UX design artifacts are all approved.")
        else:
            st.caption("The generator creates a bounded, text-only source bundle from all three approved artifacts. It does not write to the repository, run code, install dependencies, or execute tests.")
            if st.button("Generate source code bundle", type="primary", key=f"generate_code_{selected['id']}", disabled=not settings.has_model_api_key):
                with st.spinner("Code Generator is creating and validating a bounded source bundle..."):
                    try:
                        workflow = build_forge_workflow(GeminiProvider(settings))
                        workflow_result = workflow.invoke({
                            "project_id": selected["id"],
                            "user_request": selected["brief"],
                            "requested_stage": "codegen",
                            "requirements": latest_requirements["content"],
                            "requirements_approved": True,
                            "architecture": latest_architecture["content"],
                            "architecture_approved": True,
                            "uiux_design": latest_uiux["content"],
                            "uiux_approved": True,
                        })
                        bundle_id = save_project_artifact(
                            settings.database_path, selected["id"], "code_bundle", workflow_result["code_bundle"]
                        )
                        add_project_event(settings.database_path, selected["id"], "code_generator_completed", workflow_result["summary"])
                        st.session_state["forgeai_last_code_bundle_id"] = bundle_id
                        st.success(workflow_result["summary"])
                        for warning in workflow_result.get("warnings", []):
                            st.warning(warning)
                        st.rerun()
                    except (AgentExecutionError, ArchitectExecutionError, UIUXExecutionError, CodeGenExecutionError, ModelProviderError, ValueError) as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Code generation failed ({type(exc).__name__}). Check the app logs and configuration.")

        code_artifact = get_latest_project_artifact(settings.database_path, selected["id"], "code_bundle")
        if code_artifact:
            bundle = code_artifact["content"]
            st.markdown("### Generated source bundle")
            st.caption(f"Version {code_artifact['version']} · {len(bundle['files'])} files · Review status: {code_artifact['review_status'].replace('_', ' ').title()}")
            st.write(bundle["implementation_summary"])
            for note in bundle["implementation_notes"]:
                st.markdown(f"- {note}")
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for source_file in bundle["files"]:
                    archive.writestr(source_file["path"], source_file["content"])
            st.download_button(
                "Download source bundle (.zip)",
                data=zip_buffer.getvalue(),
                file_name=f"forgeai-project-{selected['id']}-code-v{code_artifact['version']}.zip",
                mime="application/zip",
                key=f"download_code_{code_artifact['id']}",
            )
            for source_file in bundle["files"]:
                with st.expander(f"{source_file['path']} · {source_file['language']}"):
                    st.caption(source_file["purpose"])
                    st.code(source_file["content"], language=source_file["language"] if source_file["language"] in {"python", "javascript", "typescript", "html", "css", "json", "yaml", "toml", "markdown"} else "text")
            if code_artifact["review_status"] == "pending":
                st.markdown("### Human source review")
                st.warning("Treat these files as untrusted. Inspect them before downloading or running locally. ForgeAI has not executed or tested them.")
                code_notes = st.text_area("Source review notes (optional)", key=f"code_notes_{code_artifact['id']}")
                approve_code_col, changes_code_col = st.columns(2)
                with approve_code_col:
                    if st.button("Approve source bundle", type="primary", key=f"approve_code_{code_artifact['id']}"):
                        review_project_artifact(settings.database_path, code_artifact["id"], "approved", code_notes)
                        st.success("Source bundle approval recorded.")
                        st.rerun()
                with changes_code_col:
                    if st.button("Request code changes", key=f"request_code_{code_artifact['id']}"):
                        if not code_notes.strip():
                            st.error("Add notes describing the code changes needed.")
                        else:
                            review_project_artifact(settings.database_path, code_artifact["id"], "changes_requested", code_notes)
                            st.warning("Code change request recorded. Automatic repair and regeneration are not implemented.")
                            st.rerun()
            else:
                st.info(f"Source review decision: {code_artifact['review_status'].replace('_', ' ').title()}. {code_artifact['review_notes']}")



        st.divider()
        st.subheader("QA Engineer · Test Planning")
        if not code_artifact or code_artifact["review_status"] != "approved" or not latest_requirements or latest_requirements["review_status"] != "approved":
            st.info("QA planning unlocks after the latest requirements and source bundle are both human-approved.")
        else:
            st.caption("Creates traceable, risk-based test cases linked to requirement IDs. This phase does not execute the source code or report pass/fail results.")
            if st.button("Generate QA test plan", type="primary", key=f"generate_qa_{selected['id']}", disabled=not settings.has_model_api_key):
                try:
                    workflow_result = build_forge_workflow(GeminiProvider(settings)).invoke({
                        "project_id": selected["id"], "user_request": selected["brief"], "requested_stage": "qa",
                        "requirements": latest_requirements["content"], "requirements_approved": True,
                        "code_bundle": code_artifact["content"], "code_bundle_approved": True,
                    })
                    save_project_artifact(settings.database_path, selected["id"], "qa_test_plan", workflow_result["qa_test_plan"])
                    add_project_event(settings.database_path, selected["id"], "qa_engineer_completed", workflow_result["summary"])
                    st.success(workflow_result["summary"])
                    st.rerun()
                except (QAExecutionError, ModelProviderError, ValueError) as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"QA planning failed ({type(exc).__name__}). Check the app logs.")
            qa_artifact = get_latest_project_artifact(settings.database_path, selected["id"], "qa_test_plan")
            if qa_artifact:
                plan = qa_artifact["content"]
                st.markdown(f"### Test plan · Version {qa_artifact['version']}")
                st.caption(f"Review status: {qa_artifact['review_status'].replace('_', ' ').title()} · Execution: NOT EXECUTED")
                st.write(plan["plan_summary"])
                for scope_item in plan["test_scope"]:
                    st.markdown(f"- {scope_item}")
                for case in plan["test_cases"]:
                    with st.expander(f"{case['test_id']} · {case['title']} · {case['priority'].upper()}", expanded=True):
                        st.write(case["objective"])
                        st.caption(f"Type: {case['test_type']} · Automated candidate: {'Yes' if case['automation_candidate'] else 'No'}")
                        st.caption("Requirements: " + (", ".join(case["related_requirement_ids"]) or "Not linked"))
                        st.markdown("**Preconditions**")
                        for item in case["preconditions"]:
                            st.markdown(f"- {item}")
                        st.markdown("**Steps**")
                        for index, item in enumerate(case["steps"], 1):
                            st.markdown(f"{index}. {item}")
                        st.markdown("**Expected result**")
                        st.write(case["expected_result"])
                if plan["coverage_gaps"]:
                    st.markdown("**Coverage gaps**")
                    for item in plan["coverage_gaps"]:
                        st.warning(item)
                if qa_artifact["review_status"] == "pending":
                    qa_notes = st.text_area("QA plan review notes", key=f"qa_notes_{qa_artifact['id']}")
                    qa_a, qa_c = st.columns(2)
                    with qa_a:
                        if st.button("Approve QA plan", type="primary", key=f"approve_qa_{qa_artifact['id']}"):
                            review_project_artifact(settings.database_path, qa_artifact["id"], "approved", qa_notes)
                            st.rerun()
                    with qa_c:
                        if st.button("Request QA plan changes", key=f"changes_qa_{qa_artifact['id']}"):
                            if not qa_notes.strip():
                                st.error("Add review notes before requesting changes.")
                            else:
                                review_project_artifact(settings.database_path, qa_artifact["id"], "changes_requested", qa_notes)
                                st.rerun()

        st.divider()
        st.subheader("Code Reviewer · Static Review")
        if not code_artifact or code_artifact["review_status"] != "approved" or not latest_requirements or latest_requirements["review_status"] != "approved":
            st.info("Code review unlocks after the latest requirements and source bundle are both human-approved.")
        else:
            st.caption("Inspects source text for evidence-backed correctness, security, reliability, and maintainability findings. No source is executed.")
            if st.button("Run static code review", type="primary", key=f"generate_review_{selected['id']}", disabled=not settings.has_model_api_key):
                try:
                    workflow_result = build_forge_workflow(GeminiProvider(settings)).invoke({
                        "project_id": selected["id"], "user_request": selected["brief"], "requested_stage": "review",
                        "requirements": latest_requirements["content"], "requirements_approved": True,
                        "architecture": latest_architecture["content"] if latest_architecture else {},
                        "code_bundle": code_artifact["content"], "code_bundle_approved": True,
                    })
                    review_content = dict(workflow_result["code_review"])
                    review_content["source_bundle_artifact_id"] = code_artifact["id"]
                    save_project_artifact(settings.database_path, selected["id"], "code_review", review_content)
                    add_project_event(settings.database_path, selected["id"], "code_reviewer_completed", workflow_result["summary"])
                    st.success(workflow_result["summary"])
                    st.rerun()
                except (ReviewExecutionError, ModelProviderError, ValueError) as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Code review failed ({type(exc).__name__}). Check the app logs.")
            review_artifact = get_latest_project_artifact(settings.database_path, selected["id"], "code_review")
            if review_artifact:
                review = review_artifact["content"]
                st.markdown(f"### Static review · Version {review_artifact['version']}")
                st.caption(f"Review status: {review_artifact['review_status'].replace('_', ' ').title()} · AI verdict: {review['verdict'].replace('_', ' ').title()}")
                st.write(review["review_summary"])
                for finding in review["findings"]:
                    with st.expander(f"{finding['finding_id']} · {finding['severity'].upper()} · {finding['file_path']}", expanded=True):
                        st.write(finding["issue"])
                        st.markdown(f"**Impact:** {finding['impact']}")
                        st.markdown(f"**Recommendation:** {finding['recommendation']}")
                        st.caption(f"Category: {finding['category']} · Confidence: {finding['confidence']} · Lines: {finding['line_start'] or 'Not specified'}–{finding['line_end'] or 'Not specified'}")
                if review["limitations"]:
                    st.markdown("**Review limitations**")
                    for item in review["limitations"]:
                        st.warning(item)
                if review_artifact["review_status"] == "pending":
                    review_notes = st.text_area("Code review decision notes", key=f"review_notes_{review_artifact['id']}")
                    review_a, review_c = st.columns(2)
                    with review_a:
                        if st.button("Accept review report", type="primary", key=f"approve_review_{review_artifact['id']}"):
                            review_project_artifact(settings.database_path, review_artifact["id"], "approved", review_notes)
                            st.rerun()
                    with review_c:
                        if st.button("Request another review", key=f"changes_review_{review_artifact['id']}"):
                            if not review_notes.strip():
                                st.error("Add notes before requesting another review.")
                            else:
                                review_project_artifact(settings.database_path, review_artifact["id"], "changes_requested", review_notes)
                                st.rerun()



        st.divider()
        st.subheader("Isolated Test Execution · Docker")
        st.caption("Runs only Python test files already present in the human-approved source bundle. It does not install generated dependencies or execute source code in the Streamlit process.")
        if not code_artifact or code_artifact["review_status"] != "approved":
            st.info("Test execution is locked until the current source bundle has explicit human approval.")
        elif not docker_runner_enabled():
            st.warning("Docker execution is disabled by default. Enable it only on a trusted local machine or disposable VM; do not enable it on a public/shared deployment.")
            st.code("docker build --pull -t forgeai-test-runner:py311 -f runner/Dockerfile .\n\nFORGEAI_ENABLE_DOCKER_RUNNER=true\nFORGEAI_DOCKER_IMAGE=forgeai-test-runner:py311", language="bash")
            st.caption("Add the two environment variables to your local, uncommitted .env file and restart Streamlit.")
        else:
            if st.button("Execute approved test suite in Docker", type="primary", key=f"execute_tests_{selected['id']}"):
                report = DockerTestRunner().run(
                    code_artifact["content"],
                    approved=(code_artifact["review_status"] == "approved"),
                    enabled=True,
                    timeout_seconds=60,
                ).to_dict()
                report["source_bundle_artifact_id"] = code_artifact["id"]
                report["source_bundle_version"] = code_artifact["version"]
                save_project_artifact(settings.database_path, selected["id"], "execution_report", report)
                add_project_event(
                    settings.database_path, selected["id"], "test_execution_attempted",
                    f"Source bundle v{code_artifact['version']}: {report['status']} — {report['message']}",
                )
                st.rerun()

        execution_artifact = get_latest_project_artifact(settings.database_path, selected["id"], "execution_report")
        if execution_artifact:
            execution = execution_artifact["content"]
            if execution.get("source_bundle_artifact_id") != (code_artifact["id"] if code_artifact else None):
                st.warning("The latest execution report belongs to an older source bundle version and is not evidence for the current code.")
            else:
                st.markdown(f"### Execution report · Version {execution_artifact['version']}")
                st.caption(f"Source bundle version: {execution.get('source_bundle_version')} · Status: {execution['status'].replace('_', ' ').upper()}")
                st.write(execution["message"])
                metric_a, metric_b, metric_c = st.columns(3)
                metric_a.metric("Exit code", execution["exit_code"] if execution["exit_code"] is not None else "—")
                metric_b.metric("Duration", f"{execution['duration_seconds']:.2f}s")
                metric_c.metric("Test files", len(execution["test_files"]))
                if execution["test_files"]:
                    st.markdown("**Executed test files**")
                    for test_file in execution["test_files"]:
                        st.code(test_file, language="text")
                if execution["output"]:
                    st.markdown("**Runner output**")
                    st.code(execution["output"], language="text")
                if execution["status"] in {"failed", "timed_out", "output_limit_exceeded", "runner_unavailable", "no_tests", "disabled", "invalid_bundle"}:
                    st.warning("This result is not a successful test run. Review the message and output before proceeding.")



        st.divider()
        st.subheader("Bounded Code Repair · Human-supervised")
        st.caption("ForgeAI can propose up to two repair candidates per repair cycle. It may replace existing application source files only; test files are preserved. Each candidate becomes a new pending source-bundle version and must be reviewed before regression execution.")
        latest_execution_for_repair = get_latest_project_artifact(settings.database_path, selected["id"], "execution_report")
        latest_review_for_repair = get_latest_project_artifact(settings.database_path, selected["id"], "code_review")
        execution_for_repair = {}
        review_for_repair = {}
        if latest_execution_for_repair and code_artifact:
            candidate_execution = latest_execution_for_repair["content"]
            if candidate_execution.get("source_bundle_artifact_id") == code_artifact["id"]:
                execution_for_repair = candidate_execution
        if latest_review_for_repair and code_artifact:
            candidate_review = latest_review_for_repair["content"]
            if candidate_review.get("source_bundle_artifact_id") == code_artifact["id"]:
                review_for_repair = candidate_review

        has_failed_execution = execution_for_repair.get("status") in {"failed", "timed_out", "output_limit_exceeded"}
        has_review_findings = bool(review_for_repair.get("findings"))
        latest_repair = get_latest_project_artifact(settings.database_path, selected["id"], "repair_report")
        if code_artifact and code_artifact["review_status"] == "approved":
            if latest_repair and latest_repair["content"].get("candidate_source_bundle_artifact_id") == code_artifact["id"]:
                repair_cycle_id = latest_repair["content"]["cycle_source_bundle_artifact_id"]
                repair_attempt = int(latest_repair["content"]["attempt"]) + 1
            else:
                repair_cycle_id = code_artifact["id"]
                repair_attempt = 1
            repair_allowed = repair_attempt <= 2 and (has_failed_execution or has_review_findings)
            if not (has_failed_execution or has_review_findings):
                st.info("A repair proposal becomes available after a failed Docker test run or a current-source static review with findings.")
            elif repair_attempt > 2:
                st.warning("This repair cycle has reached its two-proposal limit. Start a new source baseline to begin another cycle.")
            if st.button(
                f"Propose repair · Attempt {repair_attempt}/2",
                type="primary",
                key=f"propose_repair_{selected['id']}_{code_artifact['id']}",
                disabled=not repair_allowed or not settings.has_model_api_key,
            ):
                try:
                    repair_result = build_forge_workflow(GeminiProvider(settings)).invoke({
                        "project_id": selected["id"],
                        "user_request": selected["brief"],
                        "requested_stage": "repair",
                        "requirements": latest_requirements["content"],
                        "requirements_approved": latest_requirements["review_status"] == "approved",
                        "code_bundle": code_artifact["content"],
                        "code_bundle_approved": True,
                        "execution_report": execution_for_repair,
                        "code_review": review_for_repair,
                        "repair_attempt": repair_attempt,
                        "repair_authorized": True,
                    })
                    candidate_id = save_project_artifact(
                        settings.database_path, selected["id"], "code_bundle", repair_result["code_bundle"]
                    )
                    proposal = repair_result["repair_proposal"]
                    save_project_artifact(settings.database_path, selected["id"], "repair_report", {
                        "cycle_source_bundle_artifact_id": repair_cycle_id,
                        "source_bundle_version": code_artifact["version"],
                        "candidate_source_bundle_artifact_id": candidate_id,
                        "attempt": repair_attempt,
                        "repair_summary": proposal["repair_summary"],
                        "changes": proposal["changes"],
                        "addressed_findings": proposal["addressed_findings"],
                        "unresolved_risks": proposal["unresolved_risks"],
                    })
                    add_project_event(
                        settings.database_path, selected["id"], "repair_candidate_created",
                        f"Repair attempt {repair_attempt}/2 created candidate source artifact {candidate_id}; pending human approval.",
                    )
                    st.success("Repair candidate created as a new pending source-bundle version. Review it before approving and rerunning regression tests.")
                    st.rerun()
                except (ModelProviderError, ValueError) as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Repair proposal failed ({type(exc).__name__}). Check the app logs.")
        else:
            st.info("Code repair is locked until the latest source bundle is explicitly approved.")

        if latest_repair:
            repair = latest_repair["content"]
            st.markdown(f"### Latest repair proposal · Attempt {repair['attempt']}/2")
            st.write(repair["repair_summary"])
            st.caption(f"Based on source bundle v{repair['source_bundle_version']} · Candidate artifact ID {repair['candidate_source_bundle_artifact_id']}")
            for change in repair["changes"]:
                with st.expander(f"{change['file_path']} · Proposed replacement"):
                    st.write(change["rationale"])
                    st.caption("Addresses: " + (", ".join(change["addresses"]) or "Not specified"))
            if repair["addressed_findings"]:
                st.markdown("**Findings targeted**")
                for finding in repair["addressed_findings"]:
                    st.markdown(f"- {finding}")
            if repair["unresolved_risks"]:
                st.markdown("**Unresolved risks**")
                for risk in repair["unresolved_risks"]:
                    st.warning(risk)
            st.info("The candidate source bundle is a separate pending artifact. Approve it in the source bundle review section, then execute the Docker regression suite again. Passing tests are required to verify runtime repair.")


    st.divider()
    st.subheader("Your projects")
    if projects:
        for project in projects:
            with st.expander(f"#{project['id']} · {project['name']} — {project['status']}"):
                st.write(project["brief"] or "No brief saved.")
                st.caption(f"Created: {project['created_at']}")
    else:
        st.caption("Your project workspaces will appear here.")

elif page == "Delivery Center":
    st.title("Delivery Center")
    st.write("Package a project's engineering evidence, inspect its delivery readiness, and export a portable hand-off archive. This does not deploy the application.")
    if not projects:
        st.info("Create a project in Product Studio before preparing a delivery package.")
    else:
        delivery_project = st.selectbox(
            "Select a project",
            projects,
            format_func=lambda p: f"#{p['id']} · {p['name']}",
            key="delivery_project",
        )
        delivery_artifacts = {}
        for artifact_type in ARTIFACT_TYPES:
            item = get_latest_project_artifact(settings.database_path, delivery_project["id"], artifact_type)
            if item:
                delivery_artifacts[artifact_type] = item
        delivery_events = list_project_events(settings.database_path, delivery_project["id"])
        delivery_report = build_delivery_report(delivery_project, delivery_artifacts, delivery_events)

        score_col, evidence_col, artifact_col = st.columns(3)
        score_col.metric("Evidence readiness", f"{delivery_report['readiness_percent']}%")
        evidence_col.metric("Artifacts available", len(delivery_artifacts))
        artifact_col.metric("Audit events", len(delivery_events))
        st.progress(delivery_report["readiness_percent"] / 100)
        st.caption("This is an evidence checklist score, not a security certification, test-coverage percentage, or production-readiness guarantee.")

        st.subheader("Release evidence checklist")
        for check in delivery_report["checks"]:
            status_icon = "✅" if check["passed"] else "⬜"
            st.write(f"{status_icon} **{check['label']}** · {check['weight']} points")
        if delivery_report["blockers"]:
            st.warning("Remaining evidence: " + "; ".join(delivery_report["blockers"]))
        else:
            st.success("All configured evidence checks are present for the latest saved artifacts.")

        st.divider()
        st.subheader("Artifact inventory")
        if delivery_artifacts:
            st.dataframe(
                [
                    {
                        "Artifact": kind.replace("_", " ").title(),
                        "Version": item["version"],
                        "Review": item["review_status"].replace("_", " ").title(),
                        "Created": item["created_at"],
                    }
                    for kind, item in sorted(delivery_artifacts.items())
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No engineering artifacts are available yet. Start with requirements generation in Product Studio.")

        st.divider()
        st.subheader("Export engineering hand-off")
        st.write("The ZIP contains the project brief, artifact JSON with review states, readiness report, audit events, and generated source files when available.")
        try:
            archive_bytes = build_delivery_archive(delivery_project, delivery_artifacts, delivery_events, delivery_report)
            safe_name = "".join(ch.lower() if ch.isalnum() else "-" for ch in delivery_project["name"]).strip("-") or "forgeai-project"
            st.download_button(
                "Download complete delivery package",
                data=archive_bytes,
                file_name=f"{safe_name}-forgeai-delivery.zip",
                mime="application/zip",
                type="primary",
                key=f"delivery_zip_{delivery_project['id']}",
            )
            st.download_button(
                "Download readiness report (JSON)",
                data=json.dumps(delivery_report, indent=2, ensure_ascii=False),
                file_name=f"{safe_name}-readiness-report.json",
                mime="application/json",
                key=f"delivery_report_{delivery_project['id']}",
            )
        except (KeyError, TypeError, ValueError) as exc:
            st.error(f"Delivery package could not be prepared: {exc}")

        st.divider()
        st.subheader("Deployment status")
        st.warning("NOT DEPLOYED — ForgeAI prepares the hand-off package but does not publish or provision infrastructure.")
        st.write("The current app uses SQLite. Before hosting real projects, implement durable managed storage, authentication, access controls, backups, secrets management, monitoring, and a staging/rollback process.")
        st.markdown(
            "[Deployment preparation guide](https://github.com/shriramchemical2000-hub/Autonomous-Multi-Agent-AI-Software-Engineering-Platform/blob/main/docs/DEPLOYMENT_GUIDE.md) · "
            "[Evaluation protocol](https://github.com/shriramchemical2000-hub/Autonomous-Multi-Agent-AI-Software-Engineering-Platform/blob/main/docs/EVALUATION_PROTOCOL.md)"
        )

elif page == "Agent Command Center":
    st.title("Agent Command Center")
    st.write("ForgeAI has seven executable specialists coordinated by approval-gated LangGraph stages. The remaining roles are clearly marked as planned.")
    agents = [
        ("Project Manager", "Coordinates workflow, dependencies, and hand-offs.", False),
        ("Requirements Analyst", "Structures requirements, user stories, and acceptance criteria.", True),
        ("Software Architect", "Designs components, data models, and API contracts from approved requirements.", True),
        ("UI/UX Designer", "Defines journeys, screen specifications, design systems, and accessibility requirements.", True),
        ("Implementation Engineer", "Generates a bounded backend/frontend source bundle from approved specifications.", True),
        ("Frontend Developer", "Builds user-facing components against agreed contracts.", False),
        ("QA Engineer", "Creates traceable test plans; approved Python tests can run through the opt-in Docker runner.", True),
        ("Code Reviewer", "Performs evidence-led static review of source text for correctness, security, and maintainability.", True),
        ("Code Repair Engineer", "Proposes bounded, human-reviewed fixes from test failures and static findings.", True),
    ]
    for start in range(0, len(agents), 2):
        left, right = st.columns(2)
        for col, (agent_name, responsibility, active) in zip((left, right), agents[start:start + 2]):
            with col:
                st.markdown(f"**{agent_name}**")
                st.caption(responsibility)
                if active:
                    st.success("Implemented · Invoked from Product Studio")
                else:
                    st.info("Planned · Not yet executable", icon="🧩")

elif page == "Project Memory":
    st.title("Project Memory")
    st.write("Project briefs, generated artifacts, human decisions, and audit events are stored in SQLite.")
    if projects:
        selected = st.selectbox("Choose a project", projects, format_func=lambda p: f"#{p['id']} · {p['name']}")
        st.subheader("Saved product brief")
        st.write(selected["brief"] or "No brief saved.")
        for artifact_type, label in [
            ("requirements", "Requirements specification"),
            ("architecture", "System architecture"),
            ("uiux_design", "UI/UX design specification"),
            ("code_bundle", "Generated source bundle"),
            ("qa_test_plan", "QA test plan"),
            ("code_review", "Static code review"),
            ("execution_report", "Docker test execution report"),
        ]:
            artifact = get_latest_project_artifact(settings.database_path, selected["id"], artifact_type)
            if artifact:
                st.subheader(f"Latest {label}")
                st.caption(f"Version {artifact['version']} · {artifact['review_status'].replace('_', ' ').title()} · {artifact['created_at']}")
                st.json(artifact["content"], expanded=False)
        st.subheader("Audit history")
        events = list_project_events(settings.database_path, selected["id"])
        if events:
            st.dataframe(events, use_container_width=True, hide_index=True)
        else:
            st.caption("No project events recorded yet.")
    else:
        st.info("Create a project first to begin its memory record.")

else:
    st.title("Settings")
    st.subheader("Runtime")
    st.write(f"Environment: {settings.environment}")
    st.write(f"Database: {settings.database_path}")
    st.write(f"Model preference: {settings.model_name}")
    if settings.has_model_api_key:
        st.success("A model API key is configured. Implemented specialists can make model requests.")
    else:
        st.warning("No model API key configured. Add GEMINI_API_KEY to enable live generation.")
    st.caption("Credentials are read from environment variables or a local .env file. Never commit secrets to GitHub.")

st.divider()
st.caption("ForgeAI 1.0.0 · Seven approval-gated specialists · Evidence-based delivery exports · Deployment remains operator-controlled.")
