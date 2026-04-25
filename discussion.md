# Discussion

## Why the Iberian coefficient is stronger

Phase 3's `sc_TEI_delta = +0.48` is roughly three times the magnitude of
Phase 2's continental mean of `+0.15`. This isn't a contradiction — it's
exactly what Soroye's mechanism predicts.

The mechanism says extirpation risk depends on how often local temperatures
*exceed a species-specific historical limit*. Two factors amplify the
signal on the Iberian Peninsula:

- **Many *Bombus* species reach their southern range edge there.** A
  species' baseline thermal position (`sc_TEI_bs`) is closer to its hot
  limit than at the continental average. Phase 3 corroborates this:
  `sc_TEI_bs` is +0.61 on Iberia versus +0.21 in Phase 2.
- **Recent warming over the Iberian Peninsula has been substantial.**
  Combined with the elevated baseline thermal position, even moderate
  warming pushes more local temperatures above species-specific limits.

The Phase 3 result is therefore a *stronger* test of the mechanism, not
an artefact of regional zoom or different data.

## What about the hot-edge × thermal-change interaction?

In Phase 2, `sc_TEI_bs:sc_TEI_delta` is positive and significant — species
already near their warm limit are *more* sensitive to additional warming.
On the Iberian subset that interaction collapses to +0.03 and becomes
non-significant.

The most parsimonious explanation is range restriction: the Iberian
sample concentrates species at the warm end of their distribution, so
there's less variation along `sc_TEI_bs` for the interaction to act on.
Statistically the cells are clustered in the upper-right of the (`TEI_bs`,
`TEI_delta`) space, leaving the slope of the interaction poorly identified.

We do *not* read this as evidence against the mechanism — only as a known
limitation of testing an interaction term on a small, range-restricted
sample.

## What the chain enables — future research

A claim that has been independently *re*plicated becomes a tool. Three
follow-up directions seem most promising:

### 1. Future-climate projection

Project the validated pipeline onto future climate scenarios — most
naturally [Destination Earth Climate Digital Twin](https://destination-earth.eu/)
(~5 km resolution, EU FAIR-aligned). The TEI definition extrapolates
naturally: keep the same per-species historical thermal limits, swap in
projected `tasmin` / `tasmax` for the future window, predict from the
v0.2.0 mixed-effects model.

This produces a spatially explicit map of where Iberian (or pan-European)
*Bombus* extirpation risk will rise, and where conditions may *fall back*
within thermal limits — i.e. candidate climate refugia. A separate
companion repo and a new FORRT chain, citing the v0.2.0 nanopubs as
methodological provenance, would be the natural shape of that work.

### 2. Cross-taxon transfer

The same pipeline can be applied to other thermally-sensitive insect taxa
that have GBIF occurrence coverage and historical climate baselines:
solitary bees, butterflies, hoverflies. The Snakefile + Dockerfile +
parameterised `OUT_SUBDIR` make adding a new taxon a matter of swapping
in the cleaning script for that group.

### 3. Conservation prioritisation

By overlaying the projected risk maps with protected-area boundaries and
known refugia, this analysis can flag conservation priority areas where
intervention would protect species from thermal-exposure events — the
"manage habitats to reduce exposure to the growing frequency of
temperatures that are extreme relative to species' historical
tolerances" recommendation Soroye et al. close their paper with.

## What this work doesn't do

- It does not test the mechanism on individual species — the GLMM treats
  species as a random effect rather than fitting per-species coefficients.
  Per-species rankings of vulnerability would need a follow-up study.
- It does not evaluate alternative climate predictors (drought indices,
  diurnal range, extreme-event metrics). Soroye's TEI is a
  monthly-resolution, single-statistic predictor; finer climate variables
  may yield a stronger or sharper signal.
- It does not quantify the contribution of land-use change. Soroye's
  paper controls for land use and reports the climate effect as
  independent of it; a parallel land-use replication on Iberia would
  require regional land-use rasters we have not assembled here.

## Reflection on the FORRT chain itself

Two practical points worth surfacing for anyone doing similar work:

- **Paper-rooted vs question-rooted chains start differently.** If there's
  an upstream paper, start with Quote-with-comment + AIDA. If you're
  asking your own question, start with PCC question. Both end at the same
  Claim → Study → Outcome backbone.
- **One repo can host two replication branches.** When a single Python
  pipeline is exercised on two datasets (Phase 2 = Soroye's data,
  Phase 3 = GBIF Iberia), the cleaner shape is one Claim with two
  Study + Outcome branches, *not* two separate repos. The 95 %-shared
  code stays in one place; the chain on Science Live stays navigable.

Both observations are now folded into the FORRT chain-design heuristics
captured in our memory for future projects.
