# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace designed to turn a product brief into traceable engineering deliverables through specialised agents, shared project state, validation, and human approval gates.

**Current status:** Phase 4 integration. The application foundation, Gemini provider adapter, typed agent contracts, executable Requirements Analyst, Streamlit workflow, artifact persistence, and human review recording are implemented. A live Gemini request still requires a user-supplied API key and has not been verified in this repository's CI.

## Current capabilities
- Create and persist projects in SQLite.
- Generate a structured requirements specification from a saved project brief using the Requirements Analyst.
- Validate model output with strict Pydantic schemas and at most one correction retry.
- Display the full specification: problem, target users, scope, assumptions, functional requirements, acceptance criteria, user stories, non-functional requirements, and open questions.
- Save immutable, versioned requirements artifacts in SQLite.
- Record explicit human approval or change-request decisions and review notes.
- Maintain an audit event history for project creation, artifact generation, and human review.
- Browse saved artifacts and audit history in Project Memory.
- Configure Gemini through environment variables or a local .env file without requiring a key to browse the app.

## Planned specialist team
1. Project Manager — coordinates workflow and dependencies.
2. Requirements Analyst — produces requirements, user stories, and acceptance criteria. (Implemented; integrated into Product Studio.)
3. Software Architect — designs components, data models, and API contracts.
4. UI/UX Designer — defines user journeys and interface specifications.
5. Backend Developer — implements approved backend tasks.
6. Frontend Developer — implements user-facing components.
7. QA Engineer — creates tests and reports defects.
8. Code Reviewer — checks correctness, maintainability, and security.

These are intended to be cooperating workflow nodes with typed inputs/outputs and shared state, not independent chat personas. The full multi-agent workflow and code execution sandbox are not implemented yet. A change request is recorded for human follow-up; automatic regeneration is not yet implemented.

## Technology
Python 3.11+, Streamlit, SQLite, Pydantic, LangChain Gemini adapter, Pytest, and GitHub Actions. LangGraph orchestration is planned.

## Run locally
Install dependencies and run:

    pip install -r requirements.txt
    streamlit run app.py

Run tests with:

    pytest -q

Configure GEMINI_API_KEY in the environment or a local .env file to make real model requests. Never commit .env files, API keys, access tokens, or production data. The application can be browsed and project records can be created without a key; live generation requires one and is subject to Gemini availability and quota.

## Safety
Generated code is untrusted input. ForgeAI does not execute generated code. Any future execution service must use an isolated, resource-limited sandbox, network disabled by default, no access to host secrets, and explicit human approval.

## Roadmap
- [x] Phase 1 — application foundation, project persistence, configuration
- [x] Phase 2 — model provider abstraction and typed agent contracts
- [x] Phase 3 — first executable Requirements Analyst and bounded output validation
- [x] Phase 4 — integrate the analyst into Product Studio, persist artifacts, and record human review
- [ ] Phase 5 — Software Architect agent and LangGraph orchestration
- [ ] Phase 6 — controlled development workspace and code generation
- [ ] Phase 7 — test generation, bounded repair, and code review
- [ ] Phase 8 — extended approval gates, audit trail, and project memory
- [ ] Phase 9 — delivery exports, deployment, evaluation suite, and end-to-end demo

## License
No license has been selected. Until one is added, standard copyright applies.
