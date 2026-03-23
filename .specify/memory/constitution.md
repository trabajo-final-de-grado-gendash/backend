<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0 (MINOR: added Principle VII - Testing Strategy;
  expanded Technology Stack with secrets management and API versioning policy;
  expanded Principle V with mypy)
Added sections / content:
  - Principle VII: Testing Strategy (nuevo principio)
  - Secrets & Environment management (en Technology Stack)
  - API versioning policy (en Technology Stack)
  - mypy agregado a Principle V (Python Code Standards)
Modified principles:
  - V. Python Code Standards: agregado mypy como type checker obligatorio
Modified sections:
  - Technology Stack: tabla expandida con secrets y API version
Removed sections: N/A
Templates requiring updates:
  ✅ .specify/memory/constitution.md (this file)
  ⚠  .specify/templates/plan-template.md — "Constitution Check" debe mencionar Principios I-VII
  ⚠  .specify/templates/tasks-template.md — fases deben incluir tareas de tests (pytest)
     siguiendo el patrón del viz_agent: conftest.py, test_agent.py, test_integration.py
  ⚠  .specify/templates/spec-template.md — NFRs deben requerir .env.example para todo
     secret nuevo que se agregue
Deferred TODOs:
  - None.
-->

# GenBI Constitution

## Core Principles

### I. Agent-First Architecture

Every unit of intelligence in GenBI MUST be encapsulated as a standalone, independently
runnable agent. No agent may require the HTTP layer (FastAPI) to execute — each agent
MUST be fully usable from a Python script or REPL without the API or frontend running.

**Non-negotiable rules**:
- Each agent lives in its own directory at the repository root (e.g., `viz_agent/`,
  `decision_agent/`).
- Each agent exposes a single, documented entry-point function (e.g., `run()` or `invoke()`).
- Agents MUST NOT import `fastapi` or any HTTP transport library directly.
- Integration with the API happens only through the Orchestration layer.
- A console-level smoke test MUST pass before an agent is considered "done" and
  eligible for integration.

**Rationale**: Agents developed in isolation are easier to test, debug, and replace.
Coupling agent logic to infrastructure slows iteration and breaks the sprint DoD.

### II. Single-Responsibility per Agent

Each agent MUST solve exactly one, clearly named problem. Routing logic between agents
belongs exclusively to the Orchestration layer — agents MUST NOT call other agents directly.

**Current agent registry**:

| Agent | Responsibility |
|---|---|
| `viz_agent` | Generate Plotly code + JSON from a user prompt + pandas DataFrame |
| `decision_agent` | Classify user intent → Vanna / Viz Bypass / Fallback |
| _(backlog)_ `vanna_agent` | Translate natural language to SQL and execute against Chinook |

**Non-negotiable rules**:
- If an agent's scope grows to cover two distinct responsibilities, it MUST be split.
- Agent interfaces MUST be pure functions or stateless classes: same input → same
  category of output, no hidden side-effects on shared state.

**Rationale**: Single-responsibility makes each agent independently testable and
replaceable without ripple effects across the system.

### III. Sandbox Code Execution

Any agent that generates and then executes Python code MUST do so in a controlled,
restricted scope. Unrestricted `exec()` with global namespace access is forbidden.

**Non-negotiable rules**:
- Use a restricted namespace dict as execution scope — only expose the libraries and
  data objects strictly required for that agent's code to run; never pass the module's
  own `globals()` directly.
- The DataFrame (or any mutable input) passed into exec MUST be treated as read-only
  within that scope; mutations MUST NOT propagate outside the sandbox.
- All exceptions raised during execution MUST be caught, logged with full traceback,
  and returned as structured error objects — never silently swallowed.
- Retry loops MUST be capped at **5 attempts** per agent invocation.
- This principle extends to any future agent that generates executable artifacts.

**Rationale**: Unrestricted code execution poses security and reproducibility risks.
Sandboxing also makes error feedback to the LLM more reliable and auditable.

### IV. Fail-Fast & Descriptive Errors

Every agent and API endpoint MUST return structured, descriptive error responses.
Silent failures, bare `except: pass` blocks, and generic messages are forbidden.

**Non-negotiable rules**:
- Errors MUST be typed (custom exception classes or Pydantic error schemas).
- Error payloads MUST include: `error_type`, `message` (human-readable), and
  `context` (last generated code / input that triggered the failure, where applicable).
- The API layer MUST map agent exceptions to consistent HTTP error responses
  (4xx for client errors, 5xx for agent/LLM failures).
- All agent invocations MUST emit a structured log entry containing: input summary,
  route taken, number of attempts, and final outcome (success / failure reason).
- Logging is mandatory — it is not optional or a "nice-to-have".

**Rationale**: Descriptive errors accelerate debugging during development and provide
actionable feedback to both developers and (via the API) the frontend.

### V. Python Code Standards

All Python code in this repository MUST follow consistent style and naming conventions.

**Non-negotiable rules**:
- **Naming**: `snake_case` for variables, functions, and module names; `CamelCase` for
  class names; `UPPER_SNAKE_CASE` for module-level constants.
- **Formatting**: Code MUST be formatted with `ruff format` before commit.
  Line length limit: 100 characters.
- **Linting**: `ruff check` MUST pass with zero errors before commit.
  Disable rules only with an inline comment explaining why (`# noqa: <code> — <reason>`).
- **Type hints**: All public functions and methods MUST have type annotations on
  parameters and return values.
- **Type checking**: `mypy` MUST pass with no errors on the `src/` tree of each agent.
- **Docstrings**: All public classes and functions MUST have a one-line docstring minimum.
- **Dependency management**: MUST use `uv` for all dependency installation and virtual
  environment management. Direct `pip install` is forbidden outside of `uv run` scripts.
- **Models**: Use `pydantic` (v2) for all structured I/O between modules and layers.

**Rationale**: Consistent style and types reduce cognitive load during code review and
prevent whole categories of runtime bugs that would otherwise only surface in production.

### VI. Design Patterns & SOLID Principles

Code MUST apply established design patterns and SOLID principles where they reduce
complexity and increase maintainability. Over-engineering for its own sake is forbidden
— justify every abstraction introduced.

**Non-negotiable rules**:
- **Single Responsibility (S)**: Each class/module has one reason to change.
  Mirrors Principle II at the code level.
- **Open/Closed (O)**: Agent logic MUST be open for extension (new chart types, new
  routing rules) without modifying existing agent code. Use strategy or registry
  patterns where applicable (see `viz_agent` plan: Strategy pattern for chart types).
- **Dependency Inversion (D)**: High-level orchestration modules MUST depend on
  abstractions (Protocol classes or ABCs), not on concrete agent implementations.
  This enables swapping agents without touching the orchestrator.
- **Prefer composition over inheritance** for combining agent behaviors.
- Every pattern introduced MUST be justified in the PR description or `plan.md` with
  a concrete problem it solves.

**Rationale**: SOLID principles prevent the "big ball of mud" anti-pattern that
plagues research prototypes when they are rushed toward integration.

### VII. Testing Strategy

All agents and API endpoints MUST have automated tests written with `pytest`.
Tests are not optional — they are a definition-of-done gate for every story.

**Non-negotiable rules**:
- **Framework**: `pytest` + `pytest-cov`. Every agent directory MUST contain a
  `tests/` sub-directory with at minimum: `conftest.py`, `test_<agent>.py`.
- **Coverage**: Aim for ≥ 80% line coverage on agent modules. Coverage report MUST be
  generated with `pytest --cov` before a story is marked done.
- **Test types required**:
  - **Unit tests**: Test individual modules (analyzer, validator, etc.) in isolation.
    External LLM calls MUST be mocked (e.g., with `pytest-mock` or `unittest.mock`).
  - **Integration / smoke tests**: Test the agent end-to-end using the Chinook dataset
    without mocking the LLM. These run against real Gemini API — mark them
    `@pytest.mark.integration` so they can be skipped in CI if needed.
- **Console smoke test**: Every agent MUST include an `examples/` script (like
  `viz_agent/examples/`) that serves as a runnable smoke test before API integration.
- **No LLM calls in unit tests**: Unit tests MUST NOT make real API calls.
  Mock or monkeypatch all `GeminiClient` (or equivalent) calls.
- **Test the error paths**: Sad-path scenarios (empty DataFrame, bad prompt,
  code execution failure) MUST have dedicated test cases.

**Rationale**: Based on the viz_agent implementation (pytest + pytest-cov, conftest fixtures,
Chinook integration tests), this pattern is already proven in this codebase and MUST be
replicated consistently across all new agents.

## Technology Stack

These choices are fixed for the current project phase and MUST NOT be changed without
a constitution amendment.

| Layer | Technology | Notes |
|---|---|---|
| API Framework | FastAPI (Python ≥ 3.11) | Async, auto-docs via OpenAPI |
| LLM | Gemini models (google-genai) | Flash variant preferred for latency/cost |
| Visualization | Plotly (`plotly.express` / `plotly.graph_objects`) | viz_agent only |
| Data Layer | pandas DataFrame + Pydantic v2 | Primary data + schema validation |
| Test Dataset | Chinook DB | Development & integration smoke tests |
| Dependency mgmt | `uv` + `pyproject.toml` + `uv.lock` | Lock file MUST be committed |
| Testing | `pytest` + `pytest-cov` + `pytest-mock` | See Principle VII |
| Linting / Format | `ruff` (lint + format) + `mypy` | See Principle V |
| Python version | ≥ 3.11 | Required for modern type hint syntax |

**Secrets & Environment management**:
- All secrets (API keys, etc.) MUST be stored in a `.env` file loaded via `python-dotenv`.
- `.env` MUST be listed in `.gitignore`. It MUST NOT be committed.
- Every agent and the API MUST ship an `.env.example` file listing all required variables
  with placeholder values. Adding a new secret without updating `.env.example` is forbidden.
- In code, configuration MUST be loaded via a `Config` class (Pydantic `BaseSettings` or
  equivalent), not with bare `os.getenv()` calls scattered across the codebase.

**API versioning policy**:
- The API MUST use a version prefix: `POST /api/v1/chat`.
- Breaking changes to the request/response schema MUST increment the version (`v2`, etc.).
- During the TFG phase, a single `v1` is sufficient; no backward-compatibility guarantee
  is required between sprints, but version must be explicit in the URL.

## Development Workflow & Quality Gates

1. **Spec before code**: Every new agent or feature MUST have a `spec.md` created with
   `/speckit.specify` before any implementation begins.
2. **Plan before tasks**: A `plan.md` (`/speckit.plan`) MUST exist before generating
   `tasks.md` (`/speckit.tasks`).
3. **Agent isolation gate**: Before integrating an agent into the API, a console-level
   smoke test (`examples/` script) MUST pass. No exceptions.
4. **Tests gate**: `pytest` MUST pass (with ≥ 80% coverage) before a story is closed.
5. **Type check gate**: `mypy` MUST report zero errors on the agent's source tree.
6. **No dead code in `main`**: Unused imports, commented-out logic, and experimental
   stubs MUST NOT be committed to `main`. Use feature branches.
7. **Constitution check on every PR**: Reviewers MUST verify adherence to Principles
   I–VII before approving. Violations require explicit justification in the PR body.
8. **Commit message format**: `<type>: <description>` where type is one of
   `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

## Governance

This constitution supersedes all verbal agreements, ad-hoc conventions, and README
snippets. When a conflict arises between this document and any other artifact,
this document takes precedence.

**Amendment procedure**:
1. Open a Jira issue with label `constitution-amendment` describing the proposed change.
2. Update this file, increment the version using semantic versioning:
   - MAJOR: backward-incompatible governance or principle removal/redefinition.
   - MINOR: new principle or section added, or materially expanded guidance.
   - PATCH: clarifications, wording, typo fixes.
3. Update the Sync Impact Report HTML comment at the top of this file.
4. Run the consistency propagation checklist (templates, specs, plans, tasks).
5. Commit with: `docs: amend constitution to vX.Y.Z (<reason>)`.

**Compliance review**: Every spec review and PR MUST verify adherence to all principles.
Non-compliance MUST be documented and either remediated or explicitly accepted with
justification before merge.

**Version**: 1.1.0 | **Ratified**: 2026-02-17 | **Last Amended**: 2026-03-23
