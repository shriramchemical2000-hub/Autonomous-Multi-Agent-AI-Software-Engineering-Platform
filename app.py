"""ForgeAI — initial Streamlit workspace."""
from __future__ import annotations

import streamlit as st

from forgeai.config import get_settings
from forgeai.database import create_project, initialize_database, list_projects

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

with st.sidebar:
    st.markdown("## ⚙️ ForgeAI")
    st.caption("Autonomous Multi-Agent Software Engineering")
    page = st.radio(
        "Workspace",
        ["Overview", "Product Studio", "Agent Command Center", "Project Memory", "Settings"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("PHASE 1 · FOUNDATION")
    st.caption("Agent execution is not enabled yet.")

projects = list_projects(settings.database_path)

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
    c3.metric("Workflow stage", "Foundation")
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
    st.write("Start with a product idea. ForgeAI will progressively turn it into an auditable engineering workflow.")
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
            st.error("Add a short product brief so the project has useful context.")
        else:
            project_id = create_project(settings.database_path, name, brief)
            st.success(f"Project workspace created — ID {project_id}.")
            st.rerun()
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
    st.write("The target team is defined below. Agents are marked as planned until their execution and validation paths are implemented.")
    agents = [
        ("Project Manager", "Coordinates workflow, dependencies, and hand-offs."),
        ("Requirements Analyst", "Structures requirements, user stories, and acceptance criteria."),
        ("Software Architect", "Designs components, data models, and API contracts."),
        ("UI/UX Designer", "Defines journeys, interaction patterns, and screen specifications."),
        ("Backend Developer", "Implements approved services and business logic."),
        ("Frontend Developer", "Builds user-facing components against agreed contracts."),
        ("QA Engineer", "Creates tests, runs validation, and reports defects."),
        ("Code Reviewer", "Reviews correctness, maintainability, and security risks."),
    ]
    for start in range(0, len(agents), 2):
        left, right = st.columns(2)
        for col, (agent_name, responsibility) in zip((left, right), agents[start:start + 2]):
            with col:
                st.markdown(f"**{agent_name}**")
                st.caption(responsibility)
                st.info("Planned · Not yet executable", icon="🧩")

elif page == "Project Memory":
    st.title("Project Memory")
    st.write("Phase 1 stores project briefs in SQLite. Retrieval, semantic memory, and decision linking will be introduced later.")
    if projects:
        selected = st.selectbox("Choose a project", projects, format_func=lambda p: f"#{p['id']} · {p['name']}")
        st.subheader("Saved product brief")
        st.write(selected["brief"] or "No brief saved.")
        st.caption(f"Current status: {selected['status']}")
    else:
        st.info("Create a project first to begin its memory record.")

else:
    st.title("Settings")
    st.subheader("Runtime")
    st.write(f"Environment: {settings.environment}")
    st.write(f"Database: {settings.database_path}")
    st.write(f"Model preference: {settings.model_name}")
    if settings.has_model_api_key:
        st.success("A model API key is configured. Model calls are not active in Phase 1.")
    else:
        st.warning("No model API key configured. This is expected for the Phase 1 foundation.")
    st.caption("Credentials are read from environment variables. Never commit secrets to GitHub.")

st.divider()
st.caption("ForgeAI 0.1.0 · Phase 1 foundation · No generated code is executed by this application.")
