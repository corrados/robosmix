# Robosmix Audio AI Mixing Tool

Creates a pleasurable audio mix of your recording session including mixing and mastering. Everything powered by AI.

## Project definition

There are open DAWs like Ardour or Morningdaw availabe which are very powerful but complicated to operate. Mixing and mastering audio is a pice of art which requires a lot of knowledge. AI can help with that.

Robosmix intended workflow:
- Musicians of a band create tracks of their instrument and provide it to Robosmix.
- The band defines the desired final sound by a short recipe like "Rock music with dominant guitars and fat drums".
- If special treatment of audio tracks are required, this should also be added.
- AI remote controls a DAW and creates multiple final versions of the song like "Powerful mix", "High dynamic", etc. where the band can select one flavor. Based on this, the band gives feedback which is then incorporated into the final version. This repeats until the band is happy. Important: It must be possible to go back to each iteration point and start a different path from that.

## Status

Milestone 1 is implemented: project initialization, content-addressed storage,
stem import with role detection, audio analysis, and a commit history. Milestone
2 is in progress, starting with the strict `MixPlan` schema and validator. See
[docs/PLAN.md](docs/PLAN.md) for the full architecture and roadmap. The AI
audio-analysis research and recommendation is in
[docs/AI-AUDIO-ANALYSIS.md](docs/AI-AUDIO-ANALYSIS.md).

## Quick start

```bash
uv sync
uv run robosmix init "My Song" --path sessions/my-song
uv run robosmix import stems/*.wav --project sessions/my-song
uv run robosmix analyze --project sessions/my-song
uv run robosmix status --project sessions/my-song
uv run robosmix history --project sessions/my-song
```

Set `--role vocals` on import to override automatic role detection.

## Development

- AI implements everything.
- Architecture and roadmap: [docs/PLAN.md](docs/PLAN.md).
- Conventions and commands: [AGENTS.md](AGENTS.md).
- Project skills: [.opencode/skills/](.opencode/skills/).
- Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
  and `uv run mypy src` before submitting changes.
