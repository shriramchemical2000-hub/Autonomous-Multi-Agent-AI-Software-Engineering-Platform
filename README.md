# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace that turns a product brief into traceable engineering deliverables through specialist agents, structured validation, a shared LangGraph workflow, versioned artifacts, and explicit human approval gates.

**Current status: Phase 7 implemented in code.** Three specialists are executable: Requirements Analyst, Software Architect, and UI/UX Designer. The application has automated unit tests for their contracts and workflow gates. A live Gemini request still requires a user-supplied API key and has not been verified by repository CI.

## Current capabilities

- Create and persist project workspaces and product briefs in SQLite.
- Generate a structured requirements specification from a saved brief.
- Validate model output with strict Pydantic contracts and at most one correction retry per specialist.
- Review full requirements, including scope, functional requirements, acceptance criteria, user stories, non-functional requirements, assumptions, and open questions.
- Require explicit human approval of the latest requirements before architecture generation.
- Generate architecture from approved requirements: system overview, components, responsibilities, technology choices, dependencies, data entities, API endpoints, security considerations, decisions, and unresolved risks.
- Require explicit human approval of the latest architecture before UI/UX design generation.
- Generate an implementation-ready UI/UX specification from both approved inputs: personas, user journeys, navigation, screen-by-screen layouts and interactions, component specifications, design tokens, responsive behaviour, accessibility requirements, usability risks, and open design questions.
- Persist immutable, versioned artifacts and record approval/change-request decisions with review notes.
- Browse the latest requirements, architecture, and UI/UX artifacts plus project audit events in Project Memory.
- Browse the app and create project records without an API key; live model generation requires `GEMINI_API_KEY`.

## Specialist team

1. Project Manager — coordinates workflow, dependencies, and hand-offs. **Planned**
2. Requirements Analyst — produces requirements, user stories, and acceptance criteria. **Implemented**
3. Software Architect — designs components, data models, API contracts, and security considerations from approved requirements. **Implemented**
4. UI/UX Designer — defines user journeys, navigation, detailed screen specifications, reusable components, and accessibility requirements. **Implemented**
5. Backend Developer — implements approved backend tasks. **Planned**
6. Frontend Developer — builds user-facing components against approved design and API contracts. **Planned**
7. QA Engineer — creates tests and reports defects. **Planned**
8. Code Reviewer — checks correctness, maintainability, and security. **Planned**

## Orchestration and approval model

The three implemented specialists are routed through a LangGraph state graph. Each invocation executes one bounded stage and ends for human review:

1. Requirements Analyst runs on the saved product brief; its artifact must be approved.
2. Software Architect receives the approved requirements; its artifact must be approved.
3. UI/UX Designer receives both approved requirements and approved architecture; its artifact must be approved.

The application checks the latest saved artifact's review status before enabling the next stage, and the graph independently checks approval flags before invoking a downstream specialist. A new artifact version is pending review. A change request is recorded, but automatic regeneration from review notes is not implemented. SQLite is the durable project and artifact store; durable LangGraph checkpointing is not implemented.

## Technology

Python 3.11+, Streamlit, SQLite, Pydantic, LangGraph, LangChain Gemini adapter, Pytest, and GitHub Actions.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```bash
pytest -q
```

Configure `GEMINI_API_KEY` in the environment or a local `.env` file for real model requests. Never commit `.env` files, API keys, access tokens, or production data. Live generation is subject to Gemini availability and quota. CI uses fake providers and does not make paid or live model calls.

## Safety and current limitations

- Generated code is untrusted. ForgeAI does not execute generated code.
- No backend/frontend source-code generation, test execution sandbox, automatic repair loop, or deployment workflow is implemented yet.
- Any future execution service must use an isolated, resource-limited sandbox, network disabled by default, no access to host secrets, and explicit human approval.
- The UI/UX artifact is a detailed design specification, not a rendered interactive prototype or evidence of usability testing.
- Human approval is recorded in the artifact store; graph checkpoint persistence is not enabled.

## Roadmap

- [x] Phase 1 — application foundation, project persistence, configuration
- [x] Phase 2 — model provider abstraction and typed agent contracts
- [x] Phase 3 — executable Requirements Analyst and bounded output validation
- [x] Phase 4 — requirements workflow, artifact persistence, and human review
- [x] Phase 5 — Software Architect and approval-gated architecture workflow
- [x] Phase 6 — LangGraph orchestration and approval-gated specialist hand-offs
- [x] Phase 7 — UI/UX Designer and approval-gated product experience specification
- [ ] Phase 8 — controlled development workspace and code generation
- [ ] Phase 9 — test generation, bounded repair, and code review
- [ ] Phase 10 — delivery exports, deployment, evaluation suite, and end-to-end demo

## License

No license has been selected. Until one is added, standard copyright applies.
