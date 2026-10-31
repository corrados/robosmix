# AI Audio Analysis for Mixing and Mastering

Status: research note v0.1
Date: 2026-10-31
Related: `docs/PLAN.md`, `.opencode/skills/ai-mix-agent/SKILL.md`,
`.opencode/skills/audio-mixing/SKILL.md`

## 1. Question and short answer

Can an AI listen to individual tracks, a mixdown, or a master and derive the
"correct" mixing and effect settings?

Short answer: no single current AI can do that reliably. The closest published
systems are reference-guided automatic-mixing pipelines with learned critics,
not general-purpose audio chatbots. The practical design is a hybrid:

```text
local DSP measurement
    + optional music/effect embeddings
    + a reference or target profile
    + constrained parameter search / differentiable DSP
    + an LLM planner that only chooses among validated actions
    + render, measure, compare, and human feedback
```

General audio LLMs are useful for description, diagnosis, and planning from
structured analysis. They are not yet reliable mix engineers. Sending a full
stereo mix to a general audio model is also lossy: Gemini's audio path is
documented as 16 kbps mono input, and Anthropic's Messages API does not expose
native audio input.

The strongest specific evidence is MixAgent, a 2026 preprint that finds
"prompting recent multimodal models to listen and revise often worsens the
mix"; its learned critic reduces error by 19% relative to the initial mix and
beats Qwen3-Omni, Gemini 3.8 Flash, and GPT-4o-audio in a human listening test.
Even MixAgent still has a large gap to its parameter-fitted oracle and requires
a reference song.

## 2. What "correct" means

Mixing is not a single-answer prediction problem. Several mixes can be valid
for the same input, and quality depends on genre, reference, listener, and
creative intent. It helps to separate three decision classes:

| Decision class | Examples | Can AI derive it? | Best current method |
| --- | --- | --- | --- |
| Objective / technical | sample rate, clipping, true peak, integrated loudness, DC offset, phase, mono compatibility | Yes, deterministically | DSP measurement and standards |
| Corrective / diagnostic | high-pass frequency, low-mid buildup, masking, harshness, sibilance, excessive dynamics | Partly | Measurement, role-aware rules, reference matching, bounded search |
| Creative / aesthetic | balance, compression character, reverb space, saturation, stereo image, "fat drums" | No reliable general solution | Reference tracks, learned critic, multiple flavors, human feedback |

This distinction should be explicit in the product. Robosmix should not claim to
know the one correct mix. It should produce measurable, explainable candidates,
show the plan, and let the user branch from them.

Mastering is more automatable than mixing because its targets are largely
measurable: loudness, true peak, tonal balance, dynamics, and stereo consistency.
Even there, taste remains; a limiter can hit -14 LUFS / -1 dBTP without making a
good master.

## 3. Evidence review

### 3.1 General audio LLMs

- **Gemini** accepts audio, but its audio guide documents 32 tokens per second,
  16 kbps resolution, 9.5 hours maximum per prompt, and combining multichannel
  audio into one channel. The media-resolution page currently reports 25
  tokens/second for Gemini 3/4 audio. Either way, the binding limitation is
  low-bitrate mono input. That loses stereo image, high-frequency detail,
  transient shape, and much of the information a mastering decision needs.
- **Claude** is a strong text planner, but the Messages API reference documents
  text, image, document, search-result, thinking, tool, and container blocks; it
  does not document an audio input block. Claude can still reason over a JSON
  analysis report.
- **OpenAI GPT-Audio** accepts audio, but `gpt-audio` is marked deprecated and
  scheduled for shutdown on 2027-01-20, replaced by `gpt-audio-1.5`. It is an
  audio-chat model, not evidence of music-mixing parameter accuracy.
- **Qwen3-Omni** is open-weight and strong on music-understanding benchmarks
  (for example, 52.1 on RUL-MuchoMusic and 93.1 on GTZAN in its report), but
  those tasks are recognition and question answering, not estimation of EQ,
  compression, or reverb settings. It is a candidate local audio encoder or
  reasoner, not an automatic mix engineer.

General audio understanding is itself still difficult. MMAU-Pro (AAAI 2026)
contains 5,305 expert-annotated instances across 49 skills; the best-reported
model is Gemini 2.5 Flash at roughly 57-59%, and Audio Flamingo 3 at roughly
46-52%, depending on the paper version. Both approach random performance in
multiple categories. AudioBench (NAACL 2025) found that none of the five
evaluated AudioLLMs excelled consistently across its tasks. This does not
directly measure mixing, but it is a warning against assuming that a good audio
chatbot can infer good plugin settings.

### 3.2 Automatic-mixing research

- **MixAgent / Agentic Music Post-Production (2026 preprint).** A grouping agent
  assigns tracks to subgroups; a planner selects and orders effects using
  retrieved examples; a learned detector and critic revise numerical parameters
  bottom-up. It uses MixCritic, 45,657 repair critiques derived from parameters
  fitted to professional mixes. On MedleyDB, learned refinement reduces error by
  19% versus the initial mix, and the authors report higher human quality ratings
  than Qwen3-Omni, Gemini 3.8 Flash, and GPT-4o-audio. The important negative
  result is that prompted self-revision often made mixes worse. The system is
  reference-guided, uses a small effects library, and still falls well short of
  ground-truth-fitted parameters.
- **MEGAMI (2025).** A conditional diffusion model generates per-track effect
  embeddings, then a neural effect processor applies them. It explicitly models
  the one-to-many nature of mixing and reports listening-test quality
  approaching human level across genres. Its native output is an effect
  embedding and a neural processor, not a portable MixPlan of standard plugin
  parameters; replacing the processor with a parameter estimator is future work.
- **Diff-MST (ISMIR 2024).** A differentiable mixing console plus a transformer
  controller estimates gain, pan, four-band EQ, compressor, and master-bus
  parameters from raw tracks and a reference song. It supports an arbitrary
  number of unlabeled tracks and is interpretable because it predicts console
  parameters. It is reference/style transfer, uses a fixed chain, and requires
  a trained model.
- **GRAFX (DAFx 2024).** An open-source PyTorch library for differentiable audio
  processing graphs; parameters can be optimized by gradient descent. It is a
  fitting/optimization tool, not a standalone "AI mixer." It is useful for
  creating pseudo-ground-truth plans and for reference-driven refinement.
- **Fx-Encoder++ (2025).** Extracts instrument-wise audio-effect representations
  from mixtures using contrastive learning and an instrument query. It improves
  effect retrieval but the paper itself notes reduced effect-parameter matching
  performance and difficulty with single-effect understanding. Good for
  similarity and retrieval; not sufficient as a parameter predictor.
- **MERT (ICLR 2024).** A self-supervised acoustic music-understanding model that
  generalizes across 14 MIR tasks. It supplies useful musical embeddings, not
  mixing decisions. It is a sensible optional feature extractor after license,
  runtime, and quality checks.

### 3.3 Commercial tools

Commercial products are consistent with the hybrid approach, but their internals
are closed and their claims are vendor claims.

- **iZotope Neutron 5 Mix Assistant** creates a custom signal chain after
  analysis, offers instrument profiles and reference matching, and is explicitly
  a starting point for further refinement. An earlier iZotope description of Mix
  Assistant explains learned track grouping and automatic gain suggestions; the
  user still refines the result.
- **LANDR Mastering** says its engine identifies musical style, analyzes
  dynamics, frequency balance, and stereo width, then builds a processing chain
  and offers three mastering styles. This is a mastering-oriented
  analysis-plus-chain system, not a general LLM.
- **sonible smart:EQ 4** uses target Profiles, including genre and reference
  profiles, and cross-channel unmasking across tracks. The user chooses the
  profile and can adjust the result. Its "intelligence" is constrained spectral
  processing, not an open-ended audio conversation.

The common pattern is consistent: analysis, a target/profile, a constrained
processor chain, and user control. None of these products documents an LLM
listening to raw audio and deriving arbitrary settings.

### 3.4 Evaluation evidence

Automatic-mixing evaluation is inherently difficult. The DL4AM evaluation
material states that mixing is creative and subjective, that there is no unique
correct solution, and that a mix deviating from a reference is not necessarily
bad. Listening tests are therefore necessary, and objective metrics alone cannot
establish quality.

There is also no widely adopted benchmark for "given these stems and this
recipe, produce the correct MixPlan." Existing benchmarks measure audio
understanding, captioning, retrieval, or reconstruction against a reference.
Robosmix will need its own plan-level and render-level evaluation set.

## 4. Candidate evaluation

| Candidate | Input / output | Strengths | Limitations | Role in Robosmix |
| --- | --- | --- | --- | --- |
| Local DSP analysis | audio -> measurements | deterministic, cheap, local, explainable | no aesthetic judgment | Required foundation |
| Heuristic planner | measurements + role -> MixPlan | reproducible, offline, safe baseline | generic, not artist-level | Required fallback |
| Reference matching + differentiable DSP | stems + reference -> parameters | interpretable, controllable, measurable | needs reference and fitting budget; fixed chains | Preferred refinement path |
| Diff-MST-style parameter model | stems + reference -> console parameters | predicts real effect parameters, arbitrary track count | trained model, fixed console, research code | Prototype/evaluate later |
| MEGAMI-style generative effects | stems -> effect embeddings/audio | models multiple valid mixes, strong listening results | not a standard MixPlan; neural processor; training data | Research reference, not M2 dependency |
| FxEncoder++ / MERT / CLAP | audio -> embeddings | useful retrieval, similarity, role/context features | not settings; license/runtime review needed | Optional feature layer |
| General audio LLM | audio -> text/JSON | broad description, diagnosis, planning | mono 16 kbps for Gemini, no native Claude audio, weak parameter accuracy | Optional second opinion, opt-in only |
| Text LLM planner | analysis JSON + recipe -> MixPlan | strong structured reasoning; provider-agnostic | can hallucinate; no direct hearing | Default planner candidate |
| Commercial assistants | audio -> preset/chain | polished, validated by users | closed, proprietary, not local-first, limited control | Competitive reference only |

The most defensible ranking for Robosmix is:

1. Local DSP plus a deterministic heuristic planner.
2. Reference-guided constrained optimization, with a learned critic only after a
   suitable dataset exists.
3. A text LLM planner over structured analysis for recipe interpretation and
   plan selection.
4. An optional audio-capable model for a second opinion, never as the sole
   authority and never by default for full songs.
5. A trained end-to-end automatic mixer only after Robosmix has its own
   evaluation set and a licensing strategy.

## 5. Recommended architecture

```text
stems
  -> decode, validate, normalize metadata
  -> local analysis per track (technical, spectral, stereo, temporal)
  -> optional embeddings (role, instrument, effect/style)
  -> AnalysisReport (versioned JSON)

recipe + optional reference
  -> TargetProfile (genre, loudness, dynamics, tone, space, constraints)

AnalysisReport + TargetProfile
  -> Planner (text LLM or deterministic heuristic)
  -> MixPlan (validated, bounded, diffable)

MixPlan
  -> internal DSP renderer (required) or DAW adapter (optional)
  -> RenderReport (loudness, true peak, spectrum, stereo, masking, clipping)
  -> Compare against target and previous commits
  -> Refine within a fixed budget, or commit

human feedback
  -> structured tags + plan delta
  -> new child commit, never mutation of history
```

### 5.1 Analysis layer

The analysis layer must produce a stable, serializable `AnalysisReport` that is
recorded with every render. It should contain enough information for a planner
to reason without hearing the audio:

- Technical: sample rate, channels, duration, frames, peak, true peak, RMS,
  crest factor, integrated loudness, loudness range, DC offset, silence, clip
  counts.
- Spectral: band energies, centroid, rolloff, flatness, low-mid buildup,
  resonant peaks, masking estimates between important tracks.
- Stereo: correlation, mid/side energy, width, mono compatibility, low-frequency
  stereo content.
- Temporal: transient density, onset strength, tempo, section boundaries,
  short-term loudness variation, vocal/lead activity.
- Content: confirmed role, optional instrument/vocal embeddings, confidence.
- Reference: target curves, per-band deltas, dynamics and stereo targets, and
  optional effect-style embeddings.
- Provenance: analyzer version, sample rate conversions, window sizes, and
  source file hashes.

The current analyzer is a good M1 baseline but should not be treated as
sufficient for mixing: the spectral summary is a coarse center-window estimate,
not a time-varying masking or section analysis. M2 should extend it before the
agent relies on it.

### 5.2 Planner layer

The planner should receive measurements, not raw audio, for the default path.
Its job is to map intent and constraints onto a bounded action space:

- Choose a target profile from the recipe, reference, and genre.
- Choose which tracks need corrective processing and which should stay untouched.
- Set conservative starting values using role-aware rules.
- Produce one plan per flavor, independently.
- Include a short rationale and the analysis hash used.

The model must not emit code, shell commands, DAW commands, or unbounded
parameter values. The `MixPlan` validator remains the authority. On invalid
output, repair once with the validation error and then fail clearly.

### 5.3 Reference-guided refinement

Reference matching is the most promising way to move beyond generic presets.
For each candidate render:

1. Compute the same features for the candidate and the reference.
2. Weight the distance by decision class: technical constraints are hard;
   tonal/dynamics distances are soft; stereo and mono compatibility are
   guarded.
3. Search a small, bounded parameter space (coordinate search, Bayesian
   optimization, or differentiable DSP where available).
4. Penalize excessive gain, EQ boosts, limiting, width, and parameter changes.
5. Keep every candidate as a branch; do not overwrite the prior render.

This is where GRAFX/Diff-MST ideas are useful. It is also where a learned critic
could eventually help, but only with enough high-quality paired or preference
data. MixAgent is evidence that a learned critic can beat prompted self-revision;
it is not evidence that Robosmix can skip the data and evaluation work.

### 5.4 Feedback layer

Feedback should be interpreted into structured tags and a proposed plan delta:
for example `drums=loud`, `vocals=buried`, `mix=bright`, `chorus=flat`. The
system should show the interpretation, validate the delta, render a child
commit, and measure whether the intended direction changed. It should not ask an
LLM to "fix the mix" from raw audio.

## 6. Evaluation plan

Robosmix needs two levels of evaluation.

### Plan-level

- Schema validation succeeds for every generated plan.
- Every parameter is inside documented safe ranges.
- The plan's rationale references measured features, not invented ones.
- Given the same analysis, recipe, model, prompt, temperature, and seed, cached
  planning is reproducible.
- A deterministic heuristic planner produces a valid baseline for every fixture.
- Invalid or malicious model output fails closed.

### Render-level

Use a small, license-compatible multitrack set plus synthetic fixtures:

- Baselines: raw sum, loudness-normalized sum, heuristic plan, LLM-only plan,
  reference-guided optimization, and a human reference where available.
- Objective: integrated loudness, true peak, LRA, crest factor, spectral
  distance, stereo correlation/width, mono compatibility, clipping, and
  parameter distance when ground truth exists.
- Perceptual: blind, randomized, loudness-matched preference or MUSHRA-style
  tests with experienced listeners and target users.
- Robustness: different genres, track counts, recording quality, missing roles,
  mono sources, phase issues, and heavily processed stems.
- Regression: every plan/render stores hashes, model/provider/prompt versions,
  analyzer version, and metrics. Golden metrics use tolerances, not exact bytes.

Do not use an LLM's opinion as ground truth. Do not optimize a single metric such
as LUFS. A master that hits the loudness target but destroys transients is a
failure, not a success.

Suggested acceptance gates for the deterministic M2 renderer:

- No clipping at any stage; limiter ceiling respected.
- Integrated loudness and true peak within a defined tolerance of the target.
- No unexpected mono-compatibility or phase regression.
- Analysis and render reports are reproducible from stored inputs.
- Golden metrics remain within tolerance for synthetic fixtures.

For M4, add:

- All three flavors produce valid plans from one fixture recipe.
- An invalid plan is rejected and repaired or fails clearly.
- The heuristic fallback matches or beats a raw-sum baseline on at least the
  measured technical criteria.
- A reference-guided refinement improves the weighted objective without
  violating hard constraints.

## 7. Privacy, cost, and operational constraints

- Local-first remains the default. No audio leaves the machine unless the user
  explicitly configures and enables a remote provider.
- If remote analysis is offered, send an excerpt or structured report rather
  than full stems by default; document retention and provider terms.
- Do not train on user audio without explicit consent.
- Cache analysis and model responses by content hash so identical inputs produce
  stable results.
- Pin model snapshots and prompt versions; providers deprecate models. GPT-Audio
  is already deprecated, and Gemini/Claude model names change frequently.
- The deterministic DSP renderer must work with no network and no DAW.
- Verify every model, weight, and plugin license before adding a dependency.
- Keep API keys in environment variables or a secret store, never in project
  files or commits.

## 8. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Audio LLM receives downsampled mono audio | Loses stereo, HF, transients; bad mastering advice | Use DSP/analysis JSON as primary; audio LLM only for second opinion |
| LLM hallucinates plausible settings | Bad or unsafe renders | Strict schema, safe ranges, deterministic validation, fail closed |
| No unique correct mix | Evaluation and product claims are misleading | Multiple flavors, references, human feedback, plan transparency |
| Reference mismatch or bad reference | System confidently copies wrong target | Show reference features; allow genre fallback; user confirms |
| Metric overfitting | Loud but lifeless masters | Multi-metric objective plus listening tests |
| Training data and model licenses | Legal/release risk | License audit; permissive-only policy; defer training |
| Remote audio privacy | User trust and compliance risk | Local default; explicit opt-in; excerpts; documented retention |
| Model/API drift | Non-reproducible results | Pin snapshots, cache responses, record versions |
| Compute cost/latency | Poor UX for long songs | Local DSP first; cache; budgeted refinement; background jobs |

## 9. Decision and scope

Adopt the hybrid architecture. Do not make a general audio LLM the core mixing
engine.

For the next milestones:

- **M2:** build the deterministic analysis/render foundation, extend the feature
  set, and add a rule-based baseline planner. Do not wait for an AI model.
- **M3:** keep the DAW adapter independent of the analysis provider.
- **M4:** use a provider-agnostic text LLM planner over `AnalysisReport` and
  `TargetProfile`, with the heuristic fallback. Evaluate providers on the same
  fixtures rather than choosing by marketing.
- **M4 optional:** add a remote audio second-opinion path behind an explicit
  flag, with excerpts only and no automatic upload.
- **M5:** interpret feedback into structured deltas; use measured changes to
  validate the interpretation.
- **Later:** prototype reference-guided differentiable optimization and a
  learned critic only after a licensed evaluation set exists.

What would change this recommendation:

- An audio model that preserves full-band stereo at a useful token rate and
  demonstrates parameter-level mixing accuracy on a public benchmark.
- A public benchmark for mix-plan correctness, not just audio understanding.
- An open-weight model that matches a strong reference-guided baseline in blind
  listening tests.
- A licensing path for training on suitable multitrack data.

Until then, "AI derives the correct settings" is not a credible product claim.
"AI proposes bounded, inspectable candidates and improves them against measured
targets and feedback" is.

## 10. Open questions

1. Which text LLM is the default planner, and is a fully local planner required?
2. Should reference-track upload be part of M2 or wait for M4?
3. Is any remote audio processing acceptable, and under what consent and
   retention policy?
4. Which embedding models pass the license, runtime, and quality review?
5. Do we train a critic, or rely on reference-guided optimization first?
6. Which multitrack datasets and human-listening protocol are affordable and
   license-compatible?

## 11. Sources

Accessed 2026-10-31. Evidence types are noted because vendor claims and
preprints are not equivalent to peer-reviewed results.

1. MixAgent, "Agentic Music Post-Production," arXiv preprint, 2026-10-21.
   https://arxiv.org/abs/2610.29093
2. MEGAMI, "Automatic Music Mixing using a Generative Model of Effect
   Embeddings," arXiv preprint, 2025-11-11.
   https://arxiv.org/abs/2511.08040
3. GRAFX, "An Open-Source Library for Audio Processing Graphs in PyTorch,"
   DAFx24. https://arxiv.org/abs/2408.03204
4. Diff-MST, "Differentiable Mixing Style Transfer," ISMIR 2024.
   https://arxiv.org/abs/2407.08889
5. Fx-Encoder++, "Extracting Instrument-Wise Audio Effects Representations from
   Mixtures," arXiv preprint, 2025-07-03.
   https://arxiv.org/abs/2507.02273
6. MERT, "Acoustic Music Understanding Model with Large-Scale Self-supervised
   Training," ICLR 2024. https://arxiv.org/abs/2306.00107
7. Qwen3-Omni Technical Report, 2025.
   https://arxiv.org/abs/2509.17765
8. MMAU-Pro, AAAI 2026.
   https://doi.org/10.1609/aaai.v40i27.39430
   https://arxiv.org/abs/2508.13992
9. AudioBench, NAACL 2025.
   https://aclanthology.org/2025.naacl-long.218/
10. Google, "Audio understanding," Gemini API documentation.
    https://ai.google.dev/gemini-api/docs/audio
11. Google, "Media resolution," Gemini API documentation.
    https://ai.google.dev/gemini-api/docs/media-resolution
12. Anthropic, "Messages," API reference.
    https://platform.claude.com/docs/en/api/messages
13. OpenAI, "GPT-Audio" model page.
    https://developers.openai.com/api/docs/models/gpt-audio
14. OpenAI, "Deprecations."
    https://developers.openai.com/api/docs/deprecations
15. iZotope, "Neutron 5."
    https://www.izotope.com/products/neutron
16. iZotope, "Behind the Technology of Mix Assistant."
    https://www.izotope.com/community/blog/behind-the-technology-of-mix-assistant
17. LANDR, "What is AI Mastering and How Does it Work?"
    https://www.landr.com/what-is-ai-mastering-and-how-does-it-work
18. sonible, "smart:EQ 4."
    https://www.sonible.com/smarteq4/
19. DL4AM, "Evaluation," Deep Learning for Automatic Mixing tutorial.
    https://dl4am.github.io/tutorial/part_4/01_evaluation.html
20. DL4AM, "Intelligent Music Production," Deep Learning for Automatic Mixing
    tutorial. https://dl4am.github.io/tutorial/part_2/01_imp.html
21. ITU-R BS.1770-5, "Algorithms to measure audio programme loudness and
    true-peak audio level," 2023.
    https://www.itu.int/rec/R-REC-BS.1770/en
