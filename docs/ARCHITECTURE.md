# ForgeAI Architecture

## Current implementation (Phase 1)

The Streamlit application is the presentation layer. Configuration is loaded from environment variables, and SQLite persists projects and project events.

    flowchart TD
      U[User] --> UI[Streamlit Workspace]
      UI --> CFG[Environment Configuration]
      UI --> DB[(SQLite)]
      DB --> P[Projects]
      DB --> E[Project Events]

## Target multi-agent workflow

    flowchart TD
      U[Product Brief] --> PM[Project Manager]
      PM --> RA[Requirements Analyst]
      RA --> H1{Human approves requirements?}
      H1 -->|Revise| RA
      H1 -->|Approve| SA[Software Architect]
      SA --> H2{Architecture approved?}
      H2 -->|Revise| SA
      H2 -->|Approve| PLAN[Implementation Plan]
      PLAN --> FE[Frontend Developer]
      PLAN --> BE[Backend Developer]
      FE --> QA[QA Engineer]
      BE --> QA
      QA -->|Defects| FIX[Bounded repair cycle]
      FIX --> QA
      QA --> REVIEW[Code Reviewer]
      REVIEW --> H3{Human delivery approval?}
      H3 -->|No| PLAN
      H3 -->|Yes| OUT[Delivery Package]

The target workflow will use typed state and explicit transitions. These diagrams describe the intended design; they do not claim that the agents are currently running.

## Design principles
- Specialisation: each agent owns a defined task and output contract.
- Shared state: agents exchange structured artifacts, not untracked chat history.
- Traceability: inputs, decisions, artifacts, tests, and approvals are recorded.
- Bounded iteration: repair loops have attempt limits and stop conditions.
- Human oversight: requirements, architecture, and delivery have approval gates.
- Provider abstraction: model access should be replaceable without rewriting agent logic.

## Security boundary

Generated source code is untrusted. It must never execute in the Streamlit process or on the host machine. A future runner must use an isolated sandbox with resource limits, a restricted filesystem, network disabled by default, no inherited secrets, and auditable execution. External integrations and deployment actions require explicit approval.

## Planned service evolution

The initial application is a single Streamlit process backed by SQLite. As workflow capabilities grow, orchestration and API services can be separated behind FastAPI. Multi-user deployment may require PostgreSQL and managed secret storage.
