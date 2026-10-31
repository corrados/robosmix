# Robosmix Project Plan

Status: draft v0.3 (M2 in progress)
Date: 2026-10-31
Owner: AI maintainers

## 1. Product goal

Build a local-first tool that turns raw multitrack recordings into a finished,
release-ready mix and master from a short natural-language recipe. The user can
request several mix flavors, listen to them, give feedback, and continue
iterating without ever losing an earlier result.

Success means a band can go from stems to a good-sounding candidate mix without
learning a DAW, while still being able to inspect, compare, and branch from every
iteration.

## 2. Primary user workflow

```text
robosmix init "My Song"
robosmix import stems/ --roles auto
robosmix recipe "Rock with dominant guitars and fat drums"
robosmix mix --flavors powerful,dynamic,vocal-forward
robosmix compare <commit-a> <commit-b>
robosmix feedback <commit> "Drums too loud, vocals need air"
robosmix mix --from <commit>
robosmix history
robosmix checkout <commit> --branch alternate
robosmix export <commit> --format wav,mp3
```

All commands operate on a project directory containing a `.robosmix/` store.
Nothing is uploaded unless the user configures a remote AI provider.

## 3. Architecture

```text
             +-------------------------------+
             |          CLI / Web UI         |
             +---------------+---------------+
                             |
             +---------------v---------------+
             |       Application services    |
             |  project, mix, feedback, jobs |
             +---+--------+--------+---------+
                 |        |        |
      +----------v--+ +---v----+ +-v-----------+
      | Project     | | Mix    | | AI agent    |
      | store       | | engine | | orchestrator|
      | (DAG, blobs)| |        | | + tools     |
      +------+------+ +---+----+ +------+------+
             |            |             |
      +------v------+ +---v--------+ +--v-----------+
      | SQLite +    | | DSP/audio  | | Provider     |
      | content     | | analysis   | | abstraction  |
      | addressed   | | + render   | | (LLM/local)  |
      | blob store  | |            | |              |
      +-------------+ +---+--------+ +--------------+
                          |
                    +-----v------+
                    | DAW adapter|
                    | Ardour etc.|
                    +------------+
```

### Components

| Component | Responsibility |
| --- | --- |
| `robosmix/domain` | Immutable domain models, schemas, validation. No I/O. |
| `robosmix/store` | Project metadata, commit DAG, content-addressed artifacts, migrations. |
| `robosmix/audio` | Audio I/O, analysis, DSP chains, mastering, rendering. |
| `robosmix/daw` | Backend protocol plus concrete DAW adapters. |
| `robosmix/agent` | Recipe interpretation, mix planning, tool loop, feedback interpretation. |
| `robosmix/services` | Use-case orchestration shared by CLI and future web UI. |
| `robosmix/cli` | Thin command-line composition root. |
| `robosmix/web` | Optional web UI, added after the CLI workflow is stable. |

Dependency rule: `domain` depends on nothing; `store`, `audio`, and `daw` depend
only on `domain`; `agent` depends on `domain` and abstract tools; `services`
composes everything; `cli` and `web` are composition roots.

## 4. Data model and versioning

The versioning model is the heart of the product: it must be possible to return
to any iteration point and start a different path.

- `Project`: metadata, track list, recipe history, store schema version.
- `Track`: stable id, source file hash, detected and user-confirmed role,
  notes, optional alignment offsets.
- `Commit`: immutable node with parents, branch, message, plan hash, analysis
  hash, render artifact hashes, and metrics. Commits form a directed acyclic
  graph, not a linear list.
- `Branch`: named pointer to a commit. Creating a flavor creates a branch;
  feedback creates a child commit on the current branch.
- `Feedback`: attached to a commit, stored as text plus optional structured
  tags (e.g. `drums=loud`, `vocals=buried`) and the agent's interpretation.
- `Artifact`: content-addressed blob (audio render, analysis JSON, DAW session).
  Identical content is stored once and referenced by hash.

Invariants:

1. Commits and artifacts are immutable. Corrections create new nodes.
2. Every render records the plan, recipe, agent/model version, and analysis
   inputs used to produce it.
3. A branch name is unique within a project; history is never rewritten.
4. All paths and hashes are stored relative to the project root.
5. Store schema changes require a versioned migration.

## 5. Mix plan

The AI never directly emits arbitrary DAW commands. It emits a validated MixPlan
that the engine can execute deterministically.

```json
{
  "schema_version": 1,
  "flavor": "powerful",
  "target": {
    "genre": "rock",
    "reference_recipe": "dominant guitars and fat drums",
    "integrated_lufs": -14.0,
    "true_peak_db": -1.0
  },
  "tracks": {
    "track-id": {
      "gain_db": 0.0,
      "pan": 0.0,
      "high_pass_hz": 30,
      "eq": [{"freq_hz": 60, "gain_db": 2.0, "q": 0.8}],
      "compressor": {"threshold_db": -18, "ratio": 3, "attack_ms": 10, "release_ms": 120},
      "saturation": 0.1,
      "reverb_send": 0.05
    }
  },
  "master": {
    "eq": [],
    "compressor": null,
    "limiter": {"ceiling_db": -1.0},
    "stereo_width": 1.0
  },
  "rationale": "Keep the drums forward and the guitars controlled."
}
```

Rules:

- `tracks` is keyed by stable `Track.id`; omitted tracks pass through unchanged.
  Role-based groups or buses can be added later without changing the plan shape.
- Every parameter has a documented safe range; validation rejects extreme
  values before rendering.
- Plans are serializable, diffable, and human-readable.
- Flavor presets are plan templates plus boundaries, not hard-coded audio files.
- The engine can render a plan without any LLM involvement.

## 6. AI agent design

Flow:

```text
recipe + track analysis
        -> target profile
        -> candidate mix plans (one per flavor)
        -> schema validation + constraint check
        -> render + objective analysis
        -> compare against targets and references
        -> optional refinement loop
        -> commits and branches
```

Tool surface exposed to the model (all validated before execution):

- `get_project`, `get_analysis`, `list_references`
- `propose_plan`, `render_plan`, `measure_render`
- `compare_renders`
- `record_feedback_interpretation`

Guardrails:

- Structured outputs only; reject and repair invalid plans.
- Hard limits on gain, EQ boost, limiter ceiling, and render duration.
- Never overwrite an existing commit or artifact.
- Cache model decisions so re-running the same commit is byte-stable where
  possible.
- Provide a deterministic heuristic planner as an offline fallback and as a
  baseline for evaluation.
- Log model/provider/prompt version with every commit.

Research decision: the default agent consumes a structured `AnalysisReport`, not
raw audio. Audio-capable models are optional second opinions behind explicit
configuration, because current audio LLM inputs are lossy and are not reliable
for parameter-level mixing. Reference-guided constrained optimization and a
deterministic baseline come first; a learned critic requires a suitable
evaluation set. Evidence and sources are in `docs/AI-AUDIO-ANALYSIS.md`.

## 7. Audio targets and quality

- Internal processing in float32 at the project sample rate (default 48 kHz).
- Default streaming master: -14 LUFS integrated, -1 dBTP true peak.
- Alternate flavors: higher dynamic range (around -16 LUFS) and louder
  (around -11 LUFS) with true-peak protection.
- Measure integrated loudness, short-term loudness, LRA, true peak, correlation,
  mono compatibility, and spectral balance.
- Never clip; the limiter is the final stage and its ceiling is enforced.
- Use only permissively licensed DSP and plugins.

## 8. DAW integration

Primary target: Ardour on Linux, driven through OSC plus Lua scripting, with
session files in Ardour's XML format. A DAW-agnostic `DawBackend` protocol keeps
the rest of the system independent:

```text
create_session(project, tracks) -> session_ref
apply_plan(session_ref, plan) -> session_ref
render(session_ref, format, range) -> artifact_ref
snapshot(session_ref) -> artifact_ref
```

Fallback: an internal headless DSP renderer so the product works even when no
DAW is installed. REAPER and DAWproject import/export are later adapters.

## 9. Repository layout

```text
robosmix/
  README.md
  AGENTS.md
  opencode.json
  docs/PLAN.md
  .opencode/skills/...          # project skills for AI maintainers
  pyproject.toml                # created in milestone 1
  src/robosmix/
    domain/
    store/
    audio/
    daw/
    agent/
    services/
    cli/
  tests/
    unit/
    integration/
    fixtures/
```

## 10. Milestones

### M0 - Plan and skills (done)

- Project plan, architecture decisions, repository conventions.
- Project skills defined for future AI work.
- Acceptance: plan reviewed and key open decisions confirmed.

### M1 - Vertical slice: import, analyze, store (done)

- Python package, CLI skeleton, content-addressed store, SQLite index.
- Import WAV/AIFF/FLAC stems, detect basic track roles, persist project.
- Audio analysis: duration, sample rate, loudness, peak, spectral summary.
- Acceptance: `init`, `import`, `analyze`, `status` work on a fixture project;
  store is deterministic and covered by tests.
- Implemented: `robosmix` package with `init`, `import`, `analyze`, `status`,
  `history`, and `version`; 33 tests cover the domain, store, analysis, and CLI.

### M2 - Deterministic mixing and rendering (in progress)

- MixPlan schema and validator.
- DSP chain with gain, pan, high-pass, EQ, compression, saturation, reverb send.
- Multi-flavor presets and mastering with loudness normalization.
- WAV/FLAC export; objective report per render.
- Acceptance: a fixture plan renders without a DAW; loudness and true-peak
  targets are met; golden metrics stay within tolerance.
- Implemented: strict `MixPlan` schema and validator with documented safe
  ranges; covered by unit tests.

### M3 - DAW adapter

- `DawBackend` protocol and Ardour adapter using OSC/Lua.
- Create session from project, apply plan, render, snapshot.
- Integration test against a headless Ardour instance in CI where available.
- Acceptance: an Ardour-rendered artifact is comparable to the internal render
  and the session snapshot can be reopened.

### M4 - AI mix agent

- Provider abstraction with configurable model.
- Recipe parsing, target profile, plan generation, validation/repair.
- Render/measure/compare refinement loop with guardrails.
- Deterministic heuristic fallback.
- Acceptance: for a fixture recipe the agent produces valid plans for three
  flavors; invalid plans are rejected; runs are reproducible from cached inputs.

### M5 - Iteration, branches, feedback

- Commit DAG, branches, checkout, diff, compare.
- Structured and free-text feedback interpretation.
- Branch from any commit; feedback creates new iterations.
- Acceptance: full workflow from README works end to end, including returning
  to an older commit and branching.

### M6 - Usability

- Web UI for upload, recipe entry, A/B playback, flavor selection, feedback,
  and history graph.
- Job queue for long renders; progress reporting.
- Acceptance: the same workflow is possible without the CLI.

### M7 - Hardening and release

- Packaging, installation docs, sample project, performance tuning.
- Security review, dependency/license audit, migration testing.
- Acceptance: reproducible install on a clean Linux machine; documented
  architecture and limitations.

## 11. Testing and quality

- Unit tests for domain validation, store semantics, plan validation, and DSP
  primitives.
- Synthetic audio fixtures (sine sweeps, impulses, noise, multitrack stems) with
  known expected properties.
- Golden audio metrics with tolerances, not committed large binaries where
  avoidable.
- Integration tests for store, render pipeline, and DAW adapter.
- End-to-end CLI tests for the full workflow.
- Static checks: `ruff` and `mypy`; formatting via `ruff format`.
- CI runs on Linux, plus a DAW integration job when Ardour is available.

## 12. Security and privacy

- Local-first: audio and models stay local by default.
- Provider credentials only from environment variables or a secret store.
- Validate and sandbox every agent tool call; no arbitrary shell execution.
- Treat imported audio filenames and metadata as untrusted.
- Sanitize project and artifact paths; never follow symlinks outside the project.

## 13. Decisions and open questions

Confirmed:

1. First DAW target: Ardour.
2. First platform: Linux.
3. Language: Python 3.12 with `uv`.
4. Provider-agnostic AI with a deterministic local fallback; CLI before web UI.
5. Permissively licensed plugins only.

Still open:

1. Choose the default LLM provider and whether a fully local model is required
   (trade-offs in `docs/AI-AUDIO-ANALYSIS.md`).
2. Agree on the initial plugin set.
3. Confirm when the web UI enters the schedule relative to the AI workflow.

## 14. Immediate next steps

1. Build the deterministic DSP chain and flavor presets.
2. Add mastering, loudness normalization, and WAV/FLAC export.
3. Add golden-metric tests for rendering.
