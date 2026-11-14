# ForgeAI Docker Test Runner

## What it does

The optional runner executes Python test files already included in a human-approved source bundle. It does not install project dependencies and does not execute the source bundle in the Streamlit process. Only `test_*.py` and `*_test.py` files are selected. If the approved bundle contains no matching tests, the result is `no_tests`; ForgeAI does not invent a passing result.

The runner stores a bounded execution report with the source artifact ID/version, status, exit code, duration, selected test files, and captured output.

## Build the runner image

Install Docker Desktop (Windows/macOS) or Docker Engine (Linux), start the Docker daemon, then from the repository root run:

```bash
docker build --pull -t forgeai-test-runner:py311 -f runner/Dockerfile .
```

The image includes Python 3.11 and pytest 8.3.5. Project dependencies are not installed inside the job. Add only the test/runtime dependencies that the project needs to a separately reviewed runner image; do not allow generated bundles to supply a Dockerfile or install packages at execution time.

## Explicit opt-in

Set the following in the local environment or uncommitted `.env` file:

```dotenv
FORGEAI_ENABLE_DOCKER_RUNNER=true
FORGEAI_DOCKER_IMAGE=forgeai-test-runner:py311
```

Restart Streamlit. The execution control is shown only when the latest source bundle has been explicitly approved. The runner checks approval again before starting Docker.

For Streamlit Community Cloud or another shared/public hosting service, leave the setting false. The feature is designed for a trusted local operator on a dedicated disposable VM, not as an internet-facing code execution service.

## Container restrictions

Each job runs with:
- Docker network disabled (`--network=none`)
- Read-only container root filesystem and read-only source mount
- No Linux capabilities and no-new-privileges
- Non-root UID/GID 65534
- 256 MB memory, one CPU, 64 process limit, and a bounded host timeout
- A 64 MB no-exec temporary filesystem
- No application environment variables, API keys, Docker socket, or host directories mounted into the container
- Pytest plugin auto-loading disabled and bounded captured output

The runner uses a temporary workspace that is removed after execution. It attempts to remove a named container if the Docker client times out.

## Security limitations

Docker is a useful isolation boundary, not a perfect security boundary. The Docker daemon is a privileged host service and the container shares the host kernel. A container-runtime or kernel vulnerability could still affect the host. Do not enable this feature on a public shared app, a production host, or a machine containing sensitive credentials. Use a disposable VM dedicated to untrusted code, keep Docker patched, and destroy/recreate the VM after suspicious workloads.

Network isolation means tests cannot download dependencies or call external services. A test suite requiring packages not present in the runner image will fail until an operator deliberately builds and reviews an image containing those packages.

This phase executes tests that already exist in the approved source bundle. The structured QA plan remains separate; it is not automatically translated into executable test code. Automatic repair loops are not part of this phase.
