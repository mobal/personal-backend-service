# AGENTS.md

## Project Facts

- Language / runtime: Python 3.14 (see `.python-version`, `requires-python >=3.14` in `pyproject.toml`)
- Package manager: uv (`uv sync` to install; lockfile `uv.lock`)
- Build command: `make build` (Lambda layer + API zip via `scripts/build_*.sh`)
- Test command: `make test` (`uv run pytest tests/` with moto, coverage, xdist)
- Lint / format / typecheck commands: `make lint` (`ruff check --fix`), `make format` (`ruff format`), `make ty` (`ty check`), `make bandit` (security), `make tflint` (Terraform)
- Entry point(s): `app/api_handler.py` (AWS Lambda handler via Mangum); app package init `app/__init__.py` loads env files, settings, logger
- Key module boundaries: `app/routers/` (HTTP/FastAPI) -> `app/services/` (business logic) -> `app/repositories/` (DynamoDB persistence); `app/clients/` for outbound HTTP (user service); `app/models/` Pydantic contracts; `infrastructure/` Terraform (Lambda, API GW, DynamoDB, IAM, SSM)
- Non-obvious repo-specific conventions:
  - Config lives in `app/settings.py` (`pydantic-settings`); secrets resolved from SSM Parameter Store via `@computed_field` on each access — param-name env vars required.
  - Tests rely on a root `tests/conftest.py` autouse fixture that mocks AWS (`moto.mock_aws`) and seeds SSM parameters; pytest env is configured in `pyproject.toml` `[tool.pytest.ini_options] env`.
  - Env files `.env` through `.env.prod` are loaded with `override=True` (later files win).
  - Docs: single consolidated review doc at `docs/review.md`; historical plans in `plans/`.

Inspect the repo before writing code even if this section is filled in — it may be stale. If it's empty, fill it in as you learn the repo.

---

## Priorities (tie-breaker when rules conflict)

1. Security
2. Correctness
3. Explicit task requirements
4. Existing repository conventions
5. Compatibility
6. Maintainability
7. Testability
8. Performance
9. Small, focused diffs

## Core Rules

- The repository is the source of truth. Never assume language, framework, package manager, or architecture — inspect first.
- Follow existing conventions; extend them rather than competing with them. If none exist, pick the simplest solution the project's tooling supports.
- Don't modify unrelated files, revert user changes, or mix unrelated refactoring/formatting/dependency work into a feature or fix.
- Respect existing architectural layering (e.g. UI → application → domain → infra). Don't let a layer skip past its immediate neighbor.
- Keep members private unless external access is required. **Before widening any visibility (private → less restrictive), stop and ask for explicit approval.** Same for any breaking change to a public API, CLI, config, or persisted format.
- Never hard-code secrets; never log credentials, tokens, or sensitive data.
- Don't silently swallow errors — catch only when you can recover, translate, add context, or clean up.
- Don't add a dependency, second tool, or new pattern without a concrete reason and without checking whether something already covers it.

## Bug Fixes

Reproduce → write a failing regression test → observe it fail → find root cause → smallest correct fix → observe it pass → run affected tests. Don't patch symptoms or loosen a test to make broken behavior pass.

## Testing

Use the project's existing test framework. Unit tests isolate one component and mock boundaries (DB, network, filesystem, clock), not internals. Test names describe behavior, not mechanics. Tests must be independent of order and of each other's state.

## Commits

- Imperative mood, capitalized, no trailing period, subject ≤50 chars (72 hard limit).
- Blank line between subject and body.
- Body explains *why*, not *how* — the diff already shows how.

## Before Finishing

- Run the actual project checks (tests, lint, types, security) — never claim one passed without running it; if one can't be run, say so.
- Review `git status` / `git diff` for stray files, debug code, secrets, or unrelated changes.
- Confirm: requested behavior works, conventions respected, no unnecessary visibility widening, tests added/passing, docs updated if public behavior changed.

## Output Style

Be direct. Fewest words that convey the fact. No repeating the user's request back, no unearned superlatives, no filler.
