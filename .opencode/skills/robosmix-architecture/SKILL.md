---
name: robosmix-architecture
description: Use when adding or changing Robosmix modules, CLI commands, services, or the domain data model. Covers repository layout, dependency rules, and where new code belongs.
---

# Robosmix Architecture

Read `docs/PLAN.md` first. Treat it as the source of truth; if an
implementation detail contradicts it, update the plan in the same change.

## Module boundaries

| Module | Owns | Must not |
| --- | --- | --- |
| `domain` | Immutable models, schemas, validation, pure decision logic | Import I/O, store, audio, or agent code |
| `store` | Project metadata, commit DAG, content-addressed blobs, migrations | Contain DSP or LLM logic |
| `audio` | File I/O for audio, analysis, DSP chains, mastering, rendering | Know about branches or prompts |
| `daw` | `DawBackend` protocol and concrete adapters | Leak DAW-specific types into other modules |
| `agent` | Recipe parsing, planning, tool loop, provider adapters | Write directly to the store or DAW |
| `services` | Use-case orchestration that composes the modules above | Contain CLI presentation or framework code |
| `cli` / `web` | Composition roots, argument parsing, rendering output | Contain business logic |

Dependency direction is one-way: `domain` depends on nothing; `store`, `audio`,
and `daw` depend on `domain`; `agent` depends on `domain` and abstract tool
interfaces; `services` composes everything; `cli` and `web` call `services`.

## Adding a command

1. Define or reuse a domain request/result type.
2. Implement the use case in `services`; keep it UI-independent.
3. Add the thin CLI wrapper in `cli` and an end-to-end test.
4. Update `docs/PLAN.md`, `AGENTS.md`, and any affected skill.

## Domain rules

- Models are frozen dataclasses or pydantic models with validation.
- No file paths, sockets, or clocks inside domain models; pass explicit values.
- All schema changes include a version field and a migration path.
- Prefer pure functions for planning and validation so they are easy to test.

## Quality bar

- No new dependency without a note in the plan and a permissive license.
- Every new module gets tests; every CLI path gets at least one end-to-end test.
- Keep `ruff` and `mypy` clean once the toolchain exists.
