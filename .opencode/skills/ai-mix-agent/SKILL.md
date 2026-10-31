---
name: ai-mix-agent
description: Use when changing LLM orchestration, recipe interpretation, mix-plan generation, tool definitions, feedback interpretation, prompts, provider adapters, or agent evaluation and guardrails.
---

# AI Mix Agent

Read `docs/PLAN.md` sections 5 and 6 before changing the agent.

## Separation of concerns

The model plans; the engine executes. The agent may only call registered tools
and must return plans that validate against the domain schema. It must never
emit raw DAW commands, shell commands, or file paths.

Pipeline:

```text
recipe + analysis -> target profile -> candidate plans -> validate
-> render -> measure -> compare -> refine or commit
```

## Structured output

- Use a strict schema for `MixPlan` and every tool argument.
- On validation failure, repair once with the validation error, then fail
  clearly. Do not silently coerce out-of-range values.
- Include `schema_version`, flavor name, and a short rationale in plans.
- Keep plans diffable and stable: sorted keys, fixed numeric precision.

## Tools

Expose the minimum surface: read project/analysis, propose and render a plan,
measure and compare renders, record feedback interpretation. Every tool:

- validates input before acting,
- returns structured data, not prose,
- is idempotent or explicitly side-effecting,
- writes through the store so results are reproducible.

## Prompts

- Keep prompts versioned and recorded with each commit.
- Put hard constraints and safety limits in code, not only in the prompt.
- Give the model measured analysis, not raw audio.
- Ask for one flavor per call; generate flavors independently.
- Provide a deterministic heuristic planner as a fallback and as an A/B
  baseline.

## Feedback interpretation

Convert free text into structured tags plus a proposed plan delta, then show or
log the interpretation. Feedback creates a child commit; it never mutates the
commit it refers to.

## Evaluation and reproducibility

- Record provider, model id, prompt version, temperature, seed, and tool trace.
- Cache model responses keyed by inputs so repeated runs are stable.
- Maintain a small evaluation set of recipes and expected plan properties.
- Test agent logic with a fake provider; do not require network access in unit
  tests.
- Fail closed on missing credentials or unexpected model output.
