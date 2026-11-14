# Model Provider and Agent Contracts

## Provider boundary

Agent code depends on the `ModelProvider` protocol, not directly on a vendor SDK. The initial `GeminiProvider` adapter uses LangChain's Google GenAI chat integration and loads credentials from application settings. The client is created lazily, so importing the application does not require credentials.

Provider failures are translated to `ModelProviderError`. The adapter deliberately avoids returning raw request details or credentials in user-facing exception messages. A future provider can implement the same interface without changing agent contracts.

## Agent boundary

- `AgentContext` carries the project ID, product request, constraints, and previously approved artifacts.
- `AgentResult` standardises completion state, summary, artifact payload, warnings, and errors.
- `RequirementsDocument` defines structured product requirements and acceptance criteria.
- `ArchitectureDocument` defines components, data entities, API endpoints, decisions, and risks.
- `SpecialistAgent` defines the common execution protocol.

The contracts reject unknown fields to catch accidental schema drift early. The models define data shapes only; they do not imply that requirements or architecture agents have been implemented yet.

## Next implementation step

Build the Requirements Analyst as the first real specialist: prompt construction, structured JSON parsing, Pydantic validation, explicit handling of malformed output, and persisted artifacts. Then add the Software Architect and connect both to a LangGraph workflow with human approval checkpoints.
