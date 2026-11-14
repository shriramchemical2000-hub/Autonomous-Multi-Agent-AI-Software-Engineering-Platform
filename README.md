# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace designed to turn a product brief into traceable engineering deliverables through specialised agents, shared project state, validation, and human approval gates.

**Current status:** Phase 5 integration. The application foundation, Gemini provider adapter, typed agent contracts, executable Requirements Analyst, executable Software Architect, Streamlit workflows, versioned artifact persistence, and human review recording are implemented. A live Gemini request still requires a user-supplied API key and has not been verified in repository CI.

## Current capabilities
- Create and persist projects in SQLite.
- Generate a structured requirements specification from a saved project brief.
- Validate model output with strict Pydantic schemas and at most one correction retry per agent.
- Display the complete requirements specification, including functional requirements, acceptance criteria, user stories, scope, assumptions, non-functional requirements, and open questions.
- Save immutable, versioned requirements and architecture artifacts.
- Require explicit human approval of requirements before architecture generation.
- Generate an architecture from the approved requirements: system overview, components, responsibilities, technology choices, dependencies, data entities, API endpoints, security considerations, design decisions, and unresolved risks.
- Record human approval or change requests with review notes for both requirements and architecture.
- Maintain an audit event history and browse saved artifacts in Project Memory.
- Browse the application and create project records without a model API key; live generation requires one.

## Specialist team
1. Project Manager — coordinates workflow and dependencies. (Planned)
2. Requirements Analyst — produces requirements, user stories, and acceptance criteria. (Implemented)
3. Software Architect — designs components, data models, API contracts, and security considerations from approved requirements. (Implemented)
4. UI/UX Designer — defines user journeys and interface specifications. (Planned)
5. Backend Developer — implements approved backend tasks. (Planned)
6. Frontend Developer — implements user-facing components. (Planned)
7. QA Engineer — creates tests and reports defects. (Planned)
8. Code Reviewer — checks correctness, maintainability, and security. (Planned)

The two implemented specialists are bounded, schema-validated services connected through saved project artifacts and a human approval gate. The full LangGraph multi-agent workflow, automatic change-request regeneration, code generation, and isolated execution sandbox are not implemented yet.

## Technology
Python 3.11+, Streamlit, SQLite, Pydantic, LangChain Gemini adapter, Pytest, and GitHub Actions. LangGraph orchestration is planned.

## Run locally
    pip install -r requirements.txt
    streamlit run app.py

Run tests:
    pytest -q

Configure GEMINI_API_KEY in the environment or a local .env file to make real model requests. Never commit .env files, API keys, access tokens, or production data. Live generation is subject to Gemini availability and quota.

## Safety
Generated code is untrusted input. ForgeAI does not execute generated code. Any future execution service must use an isolated, resource-limited sandbox, network disabled by default, no access to host secrets, and explicit human approval.

## Roadmap
- [x] Phase 1 — application foundation, project persistence, configuration
- [x] Phase 2 — model provider abstraction and typed agent contracts
- [x] Phase 3 — first executable Requirements Analyst and bounded output validation
- [x] Phase 4 — requirements workflow, artifact persistence, and human review
- [x] Phase 5 — Software Architect specialist and approval-gated architecture workflow
- [ ] Phase 6 — LangGraph orchestration and coordinated specialist hand-offs
- [ ] Phase 7 — controlled development workspace and code generation
- [ ] Phase 8 — test generation, bounded repair, and code review
- [ ] Phase 9 — extended approval gates, audit trail, and project memory
- [ ] Phase 10 — delivery exports, deployment, evaluation suite, and end-to-end demo

## License
No license has been selected. Until one is added, standard copyright applies.
