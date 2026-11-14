"""ForgeAI — human-supervised AI software engineering workspace."""
from __future__ import annotations

import streamlit as st

from forgeai.agents.contracts import AgentContext
from forgeai.agents.requirements_analyst import AgentExecutionError
from forgeai.agents.software_architect import AgentExecutionError as ArchitectExecutionError
from forgeai.agents.uiux_designer import AgentExecutionError as UIUXExecutionError
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
        ["Overview", "Product Studio", "Agent Command Center", "Project Memory", "Settings"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("PHASE 7 · PRODUCT DESIGN WORKSPACE")
    st.caption("Three specialists are coordinated through an approval-gated LangGraph workflow.")


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
    c2.metric("Specialist roles designed", "8")
    c3.metric("Executable specialists", "3")
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
    st.write("Create a project, generate an implementation-ready requirements specification, and review it before architecture begins.")
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
    st.subheader("Your projects")
    if projects:
        for project in projects:
            with st.expander(f"#{project['id']} · {project['name']} — {project['status']}"):
                st.write(project["brief"] or "No brief saved.")
                st.caption(f"Created: {project['created_at']}")
    else:
        st.caption("Your project workspaces will appear here.")

elif page == "Agent Command Center":
    st.title("Agent Command Center")
    st.write("ForgeAI has three executable specialists coordinated by a LangGraph workflow. The remaining roles are clearly marked as planned.")
    agents = [
        ("Project Manager", "Coordinates workflow, dependencies, and hand-offs.", False),
        ("Requirements Analyst", "Structures requirements, user stories, and acceptance criteria.", True),
        ("Software Architect", "Designs components, data models, and API contracts from approved requirements.", True),
        ("UI/UX Designer", "Defines journeys, screen specifications, design systems, and accessibility requirements.", True),
        ("Backend Developer", "Implements approved services and business logic.", False),
        ("Frontend Developer", "Builds user-facing components against agreed contracts.", False),
        ("QA Engineer", "Creates tests, runs validation, and reports defects.", False),
        ("Code Reviewer", "Reviews correctness, maintainability, and security risks.", False),
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
st.caption("ForgeAI 0.5.0 · LangGraph-coordinated Requirements Analyst + Software Architect + UI/UX Designer · Generated code is never executed by this application.")
