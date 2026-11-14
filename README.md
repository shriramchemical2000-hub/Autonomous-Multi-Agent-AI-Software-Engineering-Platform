# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace designed to turn a product brief into traceable engineering deliverables through specialised agents, shared project state, validation, and human approval gates.

**Current status:** Phase 3 implementation. The application foundation, model-provider abstraction, typed agent contracts, and first executable specialist (Requirements Analyst) are implemented. The specialist has not yet been verified against a live Gemini API key.

## Current capabilities
- Create and persist projects in SQLite.
- Browse projects in the workspace and record project events.
- Configure Gemini through environment variables without requiring a key to import the app.
- Generate a structured requirements specification through the Requirements Analyst service.
- Validate model output with strict Pydantic schemas.
- Include functional requirements, priorities, acceptance criteria, user stories, scope, assumptions, non-functional requirements, and open questions.
- Retry malformed or invalid model output at most once; no unbounded agent loop.
- Require human review of the generated requirements before downstream work.

## Planned specialist team
1. Project Manager — coordinates workflow and dependencies.
2. Requirements Analyst — produces requirements, user stories, and acceptance criteria. (First executable specialist implemented.)
3. Software Architect — designs components, data models, and API contracts.
4. UI/UX Designer — defines user journeys and interface specifications.
5. Backend Developer — implements approved backend tasks.
6. Frontend Developer — implements user-facing components.
7. QA Engineer — creates tests and reports defects.
8. Code Reviewer — checks correctness, maintainability, and security.

These are intended to be cooperating workflow nodes with typed inputs/outputs and shared state, not independent chat personas. The full multi-agent workflow and code execution sandbox are not implemented yet.

## Technology
Python 3.11+, Streamlit, SQLite, Pydantic, LangChain Gemini adapter, Pytest, and GitHub Actions. LangGraph orchestration is planned.

## Run locally
Install dependencies and run:

    pip install -r requirements.txt
    streamlit run app.py

Run tests with:

    pytest -q

Configure GEMINI_API_KEY in the environment or a local .env file to make real model requests. Never commit .env files, API keys, access tokens, or production data.

## Safety
Generated code is untrusted input. ForgeAI does not execute generated code. Any future execution service must use an isolated, resource-limited sandbox, network disabled by default, no access to host secrets, and explicit human approval.

## Roadmap
- [x] Phase 1 — application foundation, project persistence, configuration
- [x] Phase 2 — model provider abstraction and typed agent contracts
- [x] Phase 3 — first executable Requirements Analyst and bounded output validation
- [ ] Phase 4 — integrate the analyst into Product Studio and add the Software Architect agent
- [ ] Phase 5 — LangGraph orchestration, dependencies, and shared workflow state
- [ ] Phase 6 — controlled development workspace and code generation
- [ ] Phase 7 — test generation, bounded repair, and code review
- [ ] Phase 8 — human approval gates, audit trail, and project memory
- [ ] Phase 9 — delivery exports, deployment, evaluation suite, and end-to-end demo

## License
No license has been selected. Until one is added, standard copyright applies.
