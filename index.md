# WeatherXBiodiversity — does Soroye 2020's bumble bee–climate claim replicate?

## What this site is

A FORRT (Framework for Open and Reproducible Research Training) replication
study of [Soroye, Newbold & Kerr (2020, *Science*)](https://doi.org/10.1126/science.aax8591).

The original paper claims that the *frequency* with which local temperatures
exceed species-specific historical thermal tolerances — not just mean warming —
predicts local extirpation of bumble bee species across North America and
Europe. We test whether that claim:

1. **Reproduces** when the authors' R analysis is re-implemented in Python,
   on the *same* underlying data, and
2. **Replicates** when the same Python pipeline is applied to *independent*
   open occurrence data for the Iberian Peninsula.

Both tests come back **Validated, High confidence**, with the Iberian
coefficient ~3× larger in magnitude than the continental mean.

## Headline result

| Phase | Dataset | n | sc_TEI_delta (mixed VB) | 95 % CI |
|---|---|---:|---:|:---:|
| 2 — Reproduction | Soroye continental data | 13 614 | **+0.15** | [0.12, 0.19] |
| 3 — Replication | Iberian *Bombus* via [GBIF](https://doi.org/10.15468/dl.3frmsq) | 528 | **+0.48** | [0.27, 0.69] |

The mechanism Soroye describes is real, and on the warm-edge subregion of
Iberia it is *stronger* — exactly what one would predict if species reaching
their thermal limit are most vulnerable to thermal-exposure events.

## The full FORRT chain

Nine nanopublications, all on [Science Live](https://platform.sciencelive4all.org):

```
                        Soroye et al. 2020
                              ▲
              ┌───────────────┴───────────────┐
              │                               │
    Quote-with-comment  ───►  AIDA  ───►  FORRT Claim
                                              │
                                              │ (tested by)
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                       ▼
                Phase 2 Replication Study           Phase 3 Replication Study
                    (Robustness)                       (Regional replicability)
                          │                                       │
                          ▼                                       ▼
                 Phase 2 Outcome                          Phase 3 Outcome
                  Validated / High                          Validated / High
                          │                                       │
                          ▼                                       ▼
              CiTO confirms Soroye 2020              CiTO confirms Soroye 2020
                          │                                       │
                          └─────────────► Wikidata  ◄─────────────┘
```

- **The claim level** is paper-rooted: a verbatim quote from Soroye's
  Discussion is wrapped with a personal comment and an AIDA-format claim.
- **Each Phase** has its own Replication Study + Outcome — Phase 2 swaps
  *the analysis software* (R → Python) while keeping data fixed; Phase 3
  swaps *the data* (continental → Iberian GBIF) while keeping software
  fixed. Together they isolate two different senses of "the claim holds up."
- **CiTO citations** wire each Outcome back to the original paper DOI so
  the replication shows up downstream in [Wikidata / Scholia](https://scholia.toolforge.org/work/Q89582023).

The next pages walk through each layer.

## Quick links

- [The Claim](claim.md) — Quote, AIDA, FORRT Claim
- [Phase 2 — Reproduction on Soroye's data](phase2.md)
- [Phase 3 — Iberian replication](phase3.md)
- [Methods](methods.md) — Python port, grid, TEI/PEI, GLMM
- [Discussion](discussion.md) — Why is Iberia stronger? What's next?
- [References](references.md)

## Reuse and citation

This work is meant to be *reused* — to project bumble bee extirpation risk
onto future climate, to flag candidate climate refugia, or to extend the
mechanism to other thermally-sensitive insect taxa. The validated pipeline
is archived at [Zenodo](https://doi.org/10.5281/zenodo.19756173) and the
GBIF download at [10.15468/dl.3frmsq](https://doi.org/10.15468/dl.3frmsq).

If you build on this, please cite both the [original paper](https://doi.org/10.1126/science.aax8591) and this repository.

## Context

Prepared for the [BioHackathon Europe 2026](https://biohackathon-europe.org/)
project *WeatherXBiodiversity*, which packages cross-domain biodiversity ×
climate data as [ARC](https://arc-rdm.org/) /
[RO-Crate](https://www.researchobject.org/ro-crate/) FAIR Digital Objects.
