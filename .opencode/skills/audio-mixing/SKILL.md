---
name: audio-mixing
description: Use when implementing or tuning DSP, gain staging, EQ, compression, reverb, saturation, loudness normalization, mastering, or audio analysis in Robosmix.
---

# Audio Mixing and Mastering

Read `docs/PLAN.md` sections 5 and 7 before changing DSP behavior.

## Signal conventions

- Process in float32 at the project sample rate, default 48 kHz.
- Keep channels explicit; do not silently downmix. Check mono compatibility.
- Apply gain before dynamics, and the limiter last in the master chain.
- Use short fades at clip boundaries to prevent clicks.
- Never clip intermediate stages; if a stage can exceed 0 dBFS, document and
  handle it.

## Default targets

| Deliverable | Integrated | True peak |
| --- | --- | --- |
| Streaming default | -14 LUFS | -1 dBTP |
| High dynamic | about -16 LUFS | -1 dBTP |
| Loud / powerful | about -11 LUFS | -1 dBTP |

Loudness normalization happens at the end of the master chain, after EQ,
compression, and limiting. Measure with true-peak oversampling; never trust a
sample-peak meter alone.

## Safe ranges

Validate these before rendering. Reject, do not clamp silently.

- Track gain: -24 to +12 dB.
- Pan: -1.0 (hard left) to +1.0 (hard right); center is 0.0.
- High-pass: 20 to 400 Hz, 12 or 24 dB/oct.
- EQ boost/cut: -12 to +12 dB; prefer cuts over broad boosts.
- Compressor ratio: 1:1 to 10:1; attack 1 to 100 ms; release 20 to 1000 ms.
- Saturation: 0.0 to 1.0 drive, compensate output gain.
- Reverb send: 0.0 to 0.5.
- Limiter ceiling: never above -0.1 dBTP; default -1.0 dBTP.
- Stereo width: 0.0 to 2.0, with mono-compatibility checks.

## Mixing heuristics

- Establish gain staging first; balance tracks before adding processing.
- High-pass everything that does not need low end, then shape the low-mid
  buildup across drums, bass, and guitars.
- Use compression for consistency, not to fix a bad performance.
- Keep the lead vocal intelligible: check its level and 2 to 5 kHz presence
  against the full mix.
- Use one reverb space for cohesion; avoid many different reverbs.
- Preserve transients on drums and consonants on vocals.
- Check the mix at low volume and in mono.

## Measurement

For every render, record integrated loudness, short-term loudness range, LRA,
true peak, crest factor, correlation, and a coarse spectral balance. Compare
against the target profile and against earlier commits.

## Libraries and tests

Prefer established, permissively licensed tools: `numpy`, `scipy`,
`soundfile`, `pyloudnorm`, `librosa`, and `pedalboard`. Test DSP with synthetic
signals (sines, sweeps, impulses, noise) and assert metrics within tolerances.
Avoid committing large audio files; generate fixtures where possible.
