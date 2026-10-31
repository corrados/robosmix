---
name: daw-integration
description: Use when working on the DAW adapter, Ardour OSC/Lua bridge, session import/export, render or bounce logic, or DAW integration tests in Robosmix.
---

# DAW Integration

Read `docs/PLAN.md` sections 3 and 8 before changing the adapter contract.

## Backend contract

Every DAW adapter implements the same protocol and returns domain values, not
DAW objects:

```text
create_session(project, tracks) -> session_ref
apply_plan(session_ref, plan) -> session_ref
render(session_ref, format, range) -> artifact_ref
snapshot(session_ref) -> artifact_ref
close(session_ref) -> None
```

Requirements:

- The adapter must be deterministic for the same project, plan, and render
  settings.
- Every render records the plan hash, session snapshot hash, adapter version,
  and DAW version in the commit.
- The internal DSP renderer remains the fallback when no DAW is installed.
- Never assume a GUI; support headless operation.

## Ardour (primary target)

- Drive Ardour through OSC and its Lua scripting interface.
- Treat the session file (XML) as an external format: parse defensively and
  keep a project-owned serialization in the store.
- Prefer creating a fresh session per render over mutating a shared session.
- Pin the tested Ardour version and document compatible ranges.
- Verify exact OSC paths and Lua calls against the installed Ardour
  documentation and version; do not rely on memory. Cover them with an
  integration test.
- Isolate the OSC endpoint and session paths per test run to avoid collisions.

## Testing

- Unit-test plan-to-session translation without a running DAW.
- Integration tests may skip when Ardour is unavailable, but must run in CI
  where it is installed.
- Compare the DAW render against the internal render using objective metrics
  with tolerances, not byte equality.
- Test reopening a session snapshot and rendering it again.
- Clean up sessions, sockets, and temporary files on failure.
