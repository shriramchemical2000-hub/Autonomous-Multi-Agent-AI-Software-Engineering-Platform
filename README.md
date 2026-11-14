# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace designed to turn a product brief into traceable engineering deliverables through specialised agents, shared project state, validation, and human approval gates.

**Current status:** Phase 1 foundation. The application shell, local project persistence, configuration, and starter tests are implemented. Specialist agents and code-generation workflows are roadmap items, not yet active features.

## Planned specialist team
1. Project Manager — coordinates workflow and dependencies.
2. Requirements Analyst — produces requirements, user stories, and acceptance criteria.
3. Software Architect — designs components, data models, and API contracts.
4. UI/UX Designer — defines user journeys and interface specifications.
5. Backend Developer — implements approved backend tasks.
6. Frontend Developer — implements user-facing components.
7. QA Engineer — creates tests and reports defects.
8. Code Reviewer — checks correctness, maintainability, and security.

These are intended to be cooperating workflow nodes with typed inputs/outputs and shared state, not independent chat personas.

## Current capabilities
- Create and persist projects in SQLite.
- Browse projects in the workspace.
- Record project events.
- Configure the app through environment variables.
- Inspect the planned workflow and implementation status.

## Technology direction
Python 3.11+, Streamlit, SQLite, Pydantic, LangGraph (planned), Gemini API through a provider abstraction (planned), Pytest, and GitHub Actions.

## Run locally
Create a virtual environment, install requirements, then run:

    pip install -r requirements.txt
    streamlit run app.py

Copy .env.example to .env if you want to configure environment values. An API key is not required for Phase 1.

Run tests with:

    pytest -q

## Configuration
- FORGEAI_ENV: runtime environment (default development)
- FORGEAI_DB_PATH: SQLite location (default data/forgeai.db)
- GEMINI_API_KEY: future model-provider credential
- FORGEAI_MODEL: preferred model (default gemini-2.5-flash)

Never commit .env files, API keys, access tokens, or production data.

## Safety
Generated code is untrusted input. A future execution service must use an isolated, resource-limited sandbox, network disabled by default, no access to host secrets, and explicit human approval. Phase 1 does not execute generated code.

## Roadmap
- [x] Phase 1 — application foundation, project persistence, configuration, tests
- [ ] Phase 2 — model provider abstraction and typed agent contracts
- [ ] Phase 3 — requirements and architecture agents
- [ ] Phase 4 — LangGraph orchestration and shared workflow state
- [ ] Phase 5 — controlled development workspace
- [ ] Phase 6 — test generation, bounded repair, and code review
- [ ] Phase 7 — human approval gates, audit trail, and project memory
- [ ] Phase 8 — delivery exports and workspace UX
- [ ] Phase 9 — deployment, evaluation suite, and end-to-end demo

## License
No license has been selected. Until one is added, standard copyright applies.
