# ForgeAI Deployment Guide

## Current deployment status

ForgeAI is an application repository with a local Streamlit interface and SQLite persistence. It is **not deployed** by the delivery workflow. The Delivery Center exports evidence and calculates readiness; it does not publish code, provision infrastructure, or configure production services.

## Run locally

1. Use Python 3.11.
2. Create and activate a virtual environment.
3. Install dependencies with pip install -r requirements.txt.
4. Set GEMINI_API_KEY as a secret environment variable only if live model generation is needed.
5. Start the app with streamlit run app.py.
6. Run pytest -q before sharing a build.
7. Enable Docker test execution only on a trusted disposable local VM, following DOCKER_TEST_RUNNER.md.

## Hosting decision

A Streamlit-compatible host can run the UI, but the current SQLite database is a local file. Do not assume a hosted container's local filesystem is durable across restarts, rebuilds, or scaling. Before hosting real projects, migrate persistence to a managed PostgreSQL service and add backups, access control, retention rules, and migration tests.

## Secrets and configuration

- Store GEMINI_API_KEY in the hosting provider's secret manager.
- Set FORGEAI_ENV=production when production configuration is implemented and validated.
- Set FORGEAI_DB_PATH only to a durable mounted volume or after PostgreSQL support is implemented.
- Keep FORGEAI_ENABLE_DOCKER_RUNNER=false on public/shared hosting.
- Never place secrets in source code, project briefs, generated bundles, ZIP exports, or GitHub commits.

## Production readiness checklist

- [ ] Select and review a hosting provider and region.
- [ ] Implement managed PostgreSQL persistence and tested migrations.
- [ ] Add authentication, authorization, and project-level access controls.
- [ ] Configure secrets, key rotation, and least-privilege access.
- [ ] Add backup, restore, retention, and deletion procedures.
- [ ] Configure TLS, security headers, rate limits, and monitoring.
- [ ] Review privacy, data residency, and generated-code handling.
- [ ] Complete dependency, static security, and penetration testing.
- [ ] Verify accessibility and usability with representative users.
- [ ] Run a full staging deployment and rollback exercise.
- [ ] Obtain human sign-off before production release.

## What the delivery score means

The score measures the presence of selected engineering evidence and approvals for the latest saved artifacts. It is not a security certification, test-coverage percentage, SLA, or production-readiness guarantee. A passing test report counts only when it references the exact current source-bundle artifact ID.
