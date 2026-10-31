# Robosmix Agent Guide

Robosmix turns multitrack recordings into AI-assisted mixes and masters, with
branchable history and a feedback loop. Start with `README.md` and
`docs/PLAN.md`.

## Working agreements

- Read `docs/PLAN.md` before changing architecture or the data model.
- Keep changes small and focused; update the plan when a decision changes.
- Never commit audio, model caches, secrets, or generated deliverables unless
  the task explicitly asks for a fixture.
- Everything is local-first. Do not add network calls that send user audio
  anywhere without explicit configuration and documentation.
- Prefer deterministic, testable code over clever code.
- Update this file and the relevant skill when commands, layout, or conventions
  change.

## Commands

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run robosmix --help
```

Run all checks before reporting a task done.

## Architecture rules

- Dependency direction: `domain` -> nothing; `store`, `audio`, `daw` ->
  `domain`; `agent` -> `domain` + tool interfaces; `services` composes all;
  `cli` / `web` are composition roots.
- Domain models are immutable and I/O-free.
- Commits and artifacts are immutable. Never edit history; append new nodes.
- The AI emits validated `MixPlan` objects, never raw DAW commands.
- The internal DSP renderer must work without a DAW installed.
- Every render records its plan, recipe, model version, and analysis inputs.

## Project skills

Load the relevant skill with the `skill` tool before working in these areas:

| Skill | Use for |
| --- | --- |
| `robosmix-architecture` | Module layout, boundaries, new commands, data model changes |
| `audio-mixing` | DSP, gain staging, EQ, compression, loudness, mastering |
| `daw-integration` | Ardour OSC/Lua, session import/export, render adapter |
| `ai-mix-agent` | LLM orchestration, prompts, tools, feedback interpretation |
| `mix-versioning` | Commit DAG, branches, artifacts, feedback, migrations |

## Definition of done

- Tests cover the new behavior, including an end-to-end CLI path when relevant.
- `ruff` and `mypy` pass.
- `docs/PLAN.md` still describes the implementation.
- No unrelated files or formatting churn.
