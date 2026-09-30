# AGENTS.md

## Project Facts

- Runtime: Python 3.14 (`.python-version`, `requires-python >=3.14`)
- Package manager: `uv` (`uv sync`, lockfile: `uv.lock`)
- Build: `make build`
- Tests: `make test`
- Lint / format / typecheck: `make lint`, `make format`, `make ty`
- Security / infra checks: `make bandit`, `make tflint`
- Lambda entry point: `app/api_handler.py`
- Architecture: `routers -> services -> repositories`
- Outbound integrations: `app/clients/`
- Pydantic contracts: `app/models/`
- Terraform: `infrastructure/`
- Configuration: `app/settings.py` using `pydantic-settings`
- Tests use `moto.mock_aws`, seeded SSM parameters, and pytest env config from `pyproject.toml`
- `.env` through `.env.prod` load with `override=True`; later files win
- Review docs: `docs/review.md`; historical plans: `plans/`

These facts may become stale. Inspect the repository before changing code; the repository is authoritative.

## Non-Negotiable Rules

- Never overwrite, revert, or modify unrelated user changes.
- Never expose, hard-code, or log secrets, credentials, tokens, or sensitive data.
- Never claim a command or check passed unless you actually ran it successfully.
- Preserve the dependency direction `routers -> services -> repositories`.
- Routers MUST NOT access repositories directly.
- Every Git commit MUST follow Conventional Commits.
- Never commit unrelated changes together.
- Do not widen a public API, CLI, config format, persisted format, or externally supported interface without explicit approval.

## Priorities

When rules conflict, prefer:

1. Security
2. Correctness
3. Explicit task requirements
4. Existing repository conventions
5. Compatibility
6. Maintainability
7. Testability
8. Performance
9. Small, focused diffs

More specific rules override more general rules.

## Before Coding

Before making changes:

1. Inspect the relevant source files and nearby tests.
2. Check `git status`.
3. Inspect relevant project configuration.
4. Search for existing implementations or patterns before introducing a new one.

Do not implement from `AGENTS.md` assumptions alone.

## Core Rules

- Follow existing repository conventions; extend them instead of creating competing patterns.
- Make the smallest change that fully solves the task.
- Do not mix unrelated refactoring, formatting, dependency changes, or cleanup into the task.
- Keep code private/internal unless broader visibility is genuinely required.
- Do not add a dependency, tool, abstraction, or architectural pattern when existing code already covers the need.
- Catch exceptions only to recover, translate, add meaningful context, or perform cleanup.
- Do not silently swallow errors.
- Outbound HTTP integrations belong in `app/clients/`.
- Request/response and shared Pydantic contracts belong in `app/models/`.

## Bug Fixes

For bug fixes:

1. Reproduce the bug.
2. Add or identify a regression test.
3. Run it and confirm it fails for the expected reason.
4. Find the root cause.
5. Apply the smallest correct fix.
6. Confirm the regression test passes.
7. Run affected tests and relevant checks.

Do not weaken, delete, or skip a valid test just to make broken behavior pass.

## Testing

- Use the existing test framework and project conventions.
- Test observable behavior, not implementation details.
- Mock boundaries such as databases, HTTP, filesystem, AWS, and clocks rather than internal functions.
- Tests must be independent of execution order and shared mutable state.
- Test names should describe behavior.

## Git Commits

Whenever creating or amending a commit, ALWAYS use Conventional Commits.

Format:

```text
<type>(optional-scope): <description>
```

Allowed types:

```text
feat, fix, refactor, test, docs, chore, build, ci, perf, style, revert
```

Rules:

- Type and scope MUST be lowercase.
- Description should normally start lowercase.
- Use imperative mood.
- No trailing period.
- Prefer subject length <=50 characters; 72 is the hard maximum.
- The message MUST describe the staged change, not merely the task or conversation.

Examples:

```text
feat(auth): add OAuth login
fix(api): handle missing user id
refactor(parser): simplify token handling
test(repository): cover missing item case
```

Before `git commit` or `git commit --amend`:

1. Inspect `git diff --cached`.
2. Confirm the staged files form one logical change.
3. Generate the message from the staged diff.
4. Validate the subject against the rules above.

If a body is needed, insert one blank line after the subject and explain **why**, constraints, or non-obvious consequences rather than narrating the diff.

Never create a commit with a non-conforming message.

## Before Finishing

Before reporting completion:

1. Run the narrowest relevant tests first.
2. Run applicable project checks:
   - `make test`
   - `make lint`
   - `make format`
   - `make ty`
   - `make bandit`
   - `make tflint`
3. Review `git status --short` and `git diff`.
4. Review `git diff --cached` if anything is staged.
5. Remove debug code, temporary files, accidental formatting, secrets, and unrelated changes.
6. Confirm requested behavior works and public behavior/docs remain consistent.

If a relevant check was not run, state which one and why.

## Output Style

Be direct and concise.

- Do not repeat the user's request.
- Do not add filler or unearned superlatives.
- State what changed, what was verified, and any relevant limitation.
