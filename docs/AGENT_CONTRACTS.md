# Model Provider, Agent Contracts, and Workflow Boundaries

## Provider boundary

Agent code depends on the `ModelProvider` protocol, not directly on a vendor SDK. The `NvidiaProvider` adapter uses NVIDIA NIM's OpenAI-compatible hosted chat-completions API and loads credentials from application settings. Agents consume only the shared `ModelProvider` protocol. The client is created lazily, so importing the application does not require credentials.

Provider failures are translated to `ModelProviderError`. The adapter deliberately avoids returning raw request details or credentials in user-facing exception messages. A future provider can implement the same interface without changing agent contracts.

## Shared agent boundary

- `AgentContext` carries the project ID, product request, constraints, and previously approved artifacts.
- `AgentResult` standardises execution status, summary, artifact payload, warnings, and errors.
- `RequirementsDocument` validates requirements and acceptance criteria.
- `ArchitectureDocument` validates components, data entities, API endpoints, decisions, and risks.
- `UIUXDesignDocument` validates personas, journeys, navigation, screen specifications, reusable components, design tokens, responsive behaviour, accessibility, usability risks, and open design questions.

Contracts reject unknown fields to detect schema drift. They define the shape of an artifact; they do not by themselves establish that a specialist is executable.

## Implemented specialist behaviour

### Requirements Analyst

Uses the saved product brief to create a structured requirements specification. It validates the response and makes at most one correction retry. A valid result is marked `needs_review` and must be explicitly approved.

### Software Architect

Requires the approved requirements artifact as its input. It proposes a practical system design without silently expanding product scope. Its structured output is validated and returned for human review. It makes at most one correction retry.

### UI/UX Designer

Requires both approved requirements and approved architecture. It treats both as binding sources of truth and produces a detailed experience specification: user journeys, navigation, screen-by-screen layout and interaction details, reusable UI components, design system, responsive behaviour, accessibility, usability risks, and unresolved design questions. It does not generate frontend source code or claim usability testing has occurred. Its output is schema-validated and returned for human review after at most one correction retry.

## LangGraph workflow

The graph routes a request to one specialist stage per invocation. Each stage ends with an artifact awaiting human approval. Downstream stages independently check explicit approval flags before calling a model. The Streamlit application obtains those flags from the latest persisted artifact review statuses.

SQLite stores projects, immutable artifact versions, review decisions, and audit events. LangGraph durable checkpointing is not configured. A change request is recorded for human traceability; it does not automatically trigger regeneration.

## Testing boundary

Automated tests use fake providers to validate parsing, schema enforcement, bounded retries, and approval gates without external API calls. A passing CI run does not verify live Gemini credentials, quota, or provider availability.


## Code Generator

The Code Generator requires requirements, architecture, and UI/UX artifacts as upstream inputs. The LangGraph node checks all three explicit approval flags before the model is invoked. The agent creates a compact source bundle and validates it against `CodeGenerationDocument`.

Each file has a safe relative POSIX path, an allowlisted text extension, a 30 KB content limit, and a bounded path depth. A bundle is limited to 30 files and 200 KB total, and duplicate paths are rejected. Hidden files, absolute paths, parent traversal, backslashes, unsupported extensions, and extra schema fields are rejected.

The generated bundle is stored as a versioned `code_bundle` artifact pending human review. Streamlit displays file contents and exports a ZIP after validation. ForgeAI does not execute generated files, install dependencies, run shell commands, or write generated files into its own repository. Passing schema validation is not a security review and does not establish that generated code is safe or functional.


## QA Engineer

The QA Engineer requires approved requirements and an explicitly approved source bundle. It creates a structured, risk-based test plan with test IDs, requirement traceability, test type, priority, preconditions, steps, expected results, and automation candidacy. Coverage gaps are called out separately. The contract forces `execution_status` to `not_executed`; this agent does not run code or claim pass/fail evidence. Output is versioned and awaits human approval.

## Code Reviewer

The Code Reviewer requires approved requirements and an explicitly approved source bundle. It inspects only supplied source text and returns a structured verdict plus findings with severity, category, path, optional exact line range, issue, impact, recommendation, and confidence. Findings must refer to paths in the supplied bundle. It does not execute code, install dependencies, perform a live dependency audit, or claim runtime verification. The report is versioned and awaits human review.

## Phase 9 safety boundary

QA planning and static review are model-backed analysis, not a secure execution environment. ForgeAI does not execute generated source in the Streamlit process or on the application host. Isolated test execution and bounded repair remain unimplemented until a separately isolated, resource-limited runner is available and verified.
