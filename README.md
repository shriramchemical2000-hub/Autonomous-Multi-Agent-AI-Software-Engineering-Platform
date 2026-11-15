# ForgeAI — Autonomous Multi-Agent AI Software Engineering Platform

ForgeAI is a human-supervised AI software engineering workspace that turns a product brief into traceable engineering deliverables through specialist agents, structured validation, a shared LangGraph workflow, versioned artifacts, and explicit human approval gates.

**Current status: Phase 10 delivery exports, deterministic readiness scoring, deployment guidance, and evaluation protocol are implemented. Actual hosting/deployment remains an operator task.** Seven specialists are executable: Requirements Analyst, Software Architect, UI/UX Designer, Code Generator, QA Engineer, Code Reviewer, and Code Repair Engineer. The application has automated unit tests for their contracts and workflow gates. A live Gemini request still requires a user-supplied API key and has not been verified by repository CI.

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
- Review source files in the app and download them as a ZIP. Generated code is never executed inside the Streamlit process; execution is available only through the separate, opt-in restricted Docker runner.
- Generate risk-based QA plans with actionable test cases, priorities, requirement traceability, and coverage gaps; plans are explicitly marked not executed.
- Perform model-backed static source reviews with severity-ranked findings, file references, impact, recommendations, and confidence.
- Persist QA plans and static review reports as versioned artifacts with human review controls and audit events.
- Optionally execute existing Python test files from an approved source bundle in a restricted Docker container; execution reports are versioned and tied to the exact source bundle.
- Generate up to two bounded repair proposals per repair cycle from failed test output or current-source static review findings. Repairs replace existing non-test source files only, preserve tests, and create a separate pending source-bundle version for human approval and regression reruns.
- Persist immutable, versioned artifacts and record approval/change-request decisions with review notes.
- Browse the latest requirements, architecture, and UI/UX artifacts plus project audit events in Project Memory.
- Generate a deterministic delivery evidence score, inspect artifact versions and blockers, and export a portable ZIP containing the project brief, artifact JSON, source bundle, readiness report, and audit history.
- Export the readiness report separately as JSON; a passing test report counts only when tied to the exact latest source-bundle artifact ID.
- Use documented deployment and evaluation checklists; the app does not provision hosting or claim a deployment.
- Browse the app and create project records without an API key; live model generation requires `NVIDIA_API_KEY`.

## Specialist team

1. Project Manager — coordinates workflow, dependencies, and hand-offs. **Planned**
2. Requirements Analyst — produces requirements, user stories, and acceptance criteria. **Implemented**
3. Software Architect — designs components, data models, API contracts, and security considerations from approved requirements. **Implemented**
4. UI/UX Designer — defines user journeys, navigation, detailed screen specifications, reusable components, and accessibility requirements. **Implemented**
5. Backend Developer — implements approved backend tasks. **Planned**
6. Frontend Developer — builds user-facing components against approved design and API contracts. **Planned**
7. QA Engineer — creates requirement-traceable risk-based test plans; it does not execute tests. **Implemented**
8. Code Reviewer — performs static source review and reports evidence-backed findings. **Implemented**
9. Code Repair Engineer — proposes bounded replacements for existing non-test source files using failed execution output or current-source review findings. **Implemented**

## Orchestration and approval model

The seven implemented specialists are routed through a LangGraph state graph. Each invocation executes one bounded stage and ends for human review:

1. Requirements Analyst runs on the saved product brief; its artifact must be approved.
2. Software Architect receives the approved requirements; its artifact must be approved.
3. UI/UX Designer receives both approved requirements and approved architecture; its artifact must be approved.
4. Code Generator receives all three approved artifacts and returns a bounded text-only source bundle for human review.
5. After the source bundle is approved, QA Engineer creates a traceable test plan and Code Reviewer performs a static source review. Both outputs await human review.
6. If an operator explicitly enables the local Docker runner, existing Python test files in the approved bundle can be executed with network disabled, read-only source, non-root user, resource limits, and bounded output/time. The execution report is tied to the exact source artifact.
7. After a failed run or actionable static finding, the Code Repair Engineer can propose up to two rounds of replacements for existing non-test source files. Each candidate is a new pending source artifact; a human must approve it before regression tests can run. Test files cannot be modified by the repair agent.

The application checks the latest saved artifact's review status before enabling the next stage, and the graph independently checks approval flags before invoking a downstream specialist. A new artifact version is pending review. A change request is recorded, but automatic regeneration from review notes is not implemented. SQLite is the durable project and artifact store; durable LangGraph checkpointing is not implemented.

## Technology

Python 3.11+, Streamlit, SQLite, Pydantic, LangGraph, NVIDIA NIM OpenAI-compatible adapter, Pytest, and GitHub Actions.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```bash
pytest -q
```

Configure `NVIDIA_API_KEY` in Streamlit Secrets, the environment, or a local `.env` file for real model requests. Set `NVIDIA_MODEL` to a model identifier available in the NVIDIA API Catalog; the default is `meta/llama-3.3-70b-instruct`. Never commit `.env` files, API keys, access tokens, or production data. Hosted API availability and rate limits apply. CI uses fake providers and does not make live model calls.

## Safety and current limitations

- Generated code is untrusted. ForgeAI does not execute generated code, install packages, invoke a shell, or write generated files into the application repository.
- Source bundles are limited to 30 files, 200 KB total, and 30 KB per file; only a defined set of text extensions and safe relative paths is accepted. These limits reduce risk but do not prove generated code is safe.
- The Code Generator creates a first source bundle. The optional Docker runner executes only existing Python test files from a human-approved bundle; it does not generate missing tests, install generated dependencies, or execute code in the Streamlit process. QA output remains a proposed test plan, and code review is static model-assisted inspection only. Automatic repair loops and deployment are not implemented.
- Docker execution is disabled by default and must only be enabled on a trusted local machine or dedicated disposable VM. Docker shares the host kernel and the Docker daemon is privileged; this is not a perfect security boundary. See [Docker runner threat model and setup](docs/DOCKER_TEST_RUNNER.md), [deployment guide](docs/DEPLOYMENT_GUIDE.md), and [evaluation protocol](docs/EVALUATION_PROTOCOL.md).
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
- [x] Phase 9C — bounded repair proposals, human-approved candidate bundles, and regression reruns
- [x] Phase 10A — delivery center, evidence readiness report, and portable project export
- [x] Phase 10B — deployment preparation guide and production checklist
- [x] Phase 10C — evaluation protocol and end-to-end manual verification scenarios
- [ ] Optional follow-on — managed database, authentication, staging deployment, and production operations

## License

No license has been selected. Until one is added, standard copyright applies.
