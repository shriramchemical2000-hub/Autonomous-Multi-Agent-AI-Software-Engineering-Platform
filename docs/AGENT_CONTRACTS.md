# Model Provider, Agent Contracts, and Workflow Boundaries

## Provider boundary

Agent code depends on the `ModelProvider` protocol, not directly on a vendor SDK. The initial `GeminiProvider` adapter uses LangChain's Google GenAI chat integration and loads credentials from application settings. The client is created lazily, so importing the application does not require credentials.

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
