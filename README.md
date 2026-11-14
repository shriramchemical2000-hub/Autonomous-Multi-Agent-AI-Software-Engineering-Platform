# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace that turns a product brief into traceable engineering deliverables through specialist agents, structured validation, a shared LangGraph workflow, versioned artifacts, and explicit human approval gates.

**Current status: Phase 9B isolated Docker test execution implemented as an explicit local opt-in; bounded repair and delivery remain pending.** Six specialists are executable: Requirements Analyst, Software Architect, UI/UX Designer, Code Generator, QA Engineer, and Code Reviewer. The application has automated unit tests for their contracts and workflow gates. A live Gemini request still requires a user-supplied API key and has not been verified by repository CI.

## Current capabilities

- Create and persist project workspaces and product briefs in SQLite.
- Generate a structured requirements specification from a saved brief.
- Validate model output with strict Pydantic contracts and at most one correction retry per specialist.
- Review full requirements, including scope, functional requirements, acceptance criteria, user stories, non-functional requirements, assumptions, and open questions.
- Require explicit human approval of the latest requirements before architecture generation.
- Generate architecture from approved requirements: system overview, components, responsibilities, technology choices, dependencies, data entities, API endpoints, security considerations, decisions, and unresolved risks.
- Require explicit human approval of the latest architecture before UI/UX design generation.
- Generate an implementation-ready UI/UX specification from both approved inputs: personas, user journeys, navigation, screen-by-screen layouts and interactions, component specifications, design tokens, responsive behaviour, accessibility requirements, usability risks, and open design questions.
- Generate a bounded source bundle (up to 30 files, 200 KB total, 30 KB per file) from all three approved specifications.
- Validate generated paths, extensions, duplicate names, and size limits before storage or ZIP export.
- Review source files in the app and download them as a ZIP; generated code is never executed by ForgeAI.
- Generate risk-based QA plans with actionable test cases, priorities, requirement traceability, and coverage gaps; plans are explicitly marked not executed.
- Perform model-backed static source reviews with severity-ranked findings, file references, impact, recommendations, and confidence.
- Persist QA plans and static review reports as versioned artifacts with human review controls and audit events.
- Optionally execute existing Python test files from an approved source bundle in a restricted Docker container; execution reports are versioned and tied to the exact source bundle.
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
7. QA Engineer — creates requirement-traceable risk-based test plans; it does not execute tests. **Implemented**
8. Code Reviewer — performs static source review and reports evidence-backed findings. **Implemented**

## Orchestration and approval model

The six implemented specialists are routed through a LangGraph state graph. Each invocation executes one bounded stage and ends for human review:

1. Requirements Analyst runs on the saved product brief; its artifact must be approved.
2. Software Architect receives the approved requirements; its artifact must be approved.
3. UI/UX Designer receives both approved requirements and approved architecture; its artifact must be approved.
4. Code Generator receives all three approved artifacts and returns a bounded text-only source bundle for human review.
5. After the source bundle is approved, QA Engineer creates a traceable test plan and Code Reviewer performs a static source review. Both outputs await human review.
6. If an operator explicitly enables the local Docker runner, existing Python test files in the approved bundle can be executed with network disabled, read-only source, non-root user, resource limits, and bounded output/time. The execution report is tied to the exact source artifact.

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

- Generated code is untrusted. ForgeAI does not execute generated code, install packages, invoke a shell, or write generated files into the application repository.
- Source bundles are limited to 30 files, 200 KB total, and 30 KB per file; only a defined set of text extensions and safe relative paths is accepted. These limits reduce risk but do not prove generated code is safe.
- The Code Generator creates a first source bundle. The optional Docker runner executes only existing Python test files from a human-approved bundle; it does not generate missing tests, install generated dependencies, or execute code in the Streamlit process. QA output remains a proposed test plan, and code review is static model-assisted inspection only. Automatic repair loops and deployment are not implemented.
- Docker execution is disabled by default and must only be enabled on a trusted local machine or dedicated disposable VM. Docker shares the host kernel and the Docker daemon is privileged; this is not a perfect security boundary. See [Docker runner threat model and setup](docs/DOCKER_TEST_RUNNER.md).
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
- [x] Phase 8 — controlled text-only source generation and human review
- [x] Phase 9A — requirement-traceable QA planning and static AI code review
- [x] Phase 9B — opt-in restricted Docker test execution and versioned execution reports
- [ ] Phase 9C — bounded repair loop, regression reruns, and execution-backed defect closure
- [ ] Phase 10 — delivery exports, deployment, evaluation suite, and end-to-end demo

## License

No license has been selected. Until one is added, standard copyright applies.
