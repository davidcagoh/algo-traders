# Upstream provenance

Copied from [K-Dense AI Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/a1043ef544e3a100c28e70a736b6cf32554d0677/skills/timesfm-forecasting)

- Upstream commit: `a1043ef544e3a100c28e70a736b6cf32554d0677`
- Copied: 2026-10-14
- Skill license declared in `SKILL.md`: Apache-2.0

## Local evaluation notes

- This is a reference skill, not an installed dependency. Do not run its forecast helpers against repo data without reviewing their model version, input assumptions, and outputs.
- Its bundled quick-start defaults to TimesFM 2.5. For the planned experiment, use the separate TimesFM 3.0 API in `references/timesfm3.md` and pin both package and checkpoint revisions.
- TimesFM 3.0 downloaded weights have separate non-commercial and non-production restrictions. The skill's Apache-2.0 license does not change the model-weight terms.
- The skill guides inference and evaluation; the experiment plan and results remain tracked in Beads issue `algo-traders-set`.
