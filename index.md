# WeatherXBiodiversity — Soroye 2020 replication on Iberia

## Claim under test

[Soroye, Newbold & Kerr (2020, *Science*)](https://doi.org/10.1126/science.aax8591) reported that **increasing thermal-exposure frequency — the rate at which a location exceeds species-specific historical thermal tolerances — predicts local extinction of bumble bees** across North America and Europe.

This repository tests whether the claim replicates on the **Iberian Peninsula** using an independent Python re-implementation of the authors' R pipeline, open [GBIF](https://www.gbif.org/) occurrence data, and CRU TS 3.24.01 climate.

## Method

A faithful Python port of Soroye's five R scripts lives in `soroye_port/`:

1. Clean bombus occurrences (species filter, synonym merge, IUCN exclusion list)
2. Rasterise onto a 100 km cylindrical-equal-area grid per (species × period × season); infer absences from other-species sampling
3. Compute per-cell sampling effort (distinct-LYID counts) summed across all six period-seasons; build the continent raster
4. Derive per-species **Thermal Exposure Index (TEI)** and **Precipitation Exposure Index (PEI)** baseline + delta using bilinearly-interpolated CRU TS monthly climate
5. Fit the mixed-effects logistic GLMM
   ```
   extinction ~ continent + sc_sampling
     + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta
     + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta
     + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta
     + (1|species)
   ```

## Results

### Phase 2 — Python port validation on Soroye's own data

Running the port on the authors' NA + Europe bombus dataset with CRU TS climate should reproduce the sign and significance of the published coefficients.

| | Coefficient | 95 % CI |
|---|---:|---|
| `sc_TEI_delta` | **+0.15** | [0.12, 0.19] |

Sign matches Soroye's published claim — port is validated.

![Phase 2 forest plot](soroye_port/phase2_forest.png)

### Phase 3 — Iberia regional replication

Apply the same Python code to Iberian *Bombus* occurrences from GBIF (31 species, 528 rows) combined with CRU TS climate.

| | Coefficient | 95 % CI |
|---|---:|---|
| `sc_TEI_delta` | **+0.48** | [0.27, 0.69] |

**Soroye's claim replicates on Iberia** — TEI_delta positive, highly significant.

![Phase 3 forest plot](soroye_port/phase3_forest.png)

## What replicating means here

- **Reproduction** (same data, different code): our Python port recovers Soroye's positive TEI_delta on his North America + Europe dataset (Phase 2).
- **Replication** (different data, same method): applying the validated port to Iberia GBIF + CRU TS also yields a positive, significant TEI_delta (Phase 3).

Together these two tests support the generality of the thermal-exposure → extinction mechanism at the Iberian regional scale.

## FORRT nanopub chain

A full FORRT Replication chain (Research Question → AIDA sentence → Claim → Replication Study → Replication Outcome) is published on [Science Live](https://platform.sciencelive4all.org) referencing this work. URIs will be added here once the chain is finalised.

## Context

Prepared for the [BioHackathon Europe 2026](https://biohackathon-europe.org/) project *WeatherXBiodiversity*, which packages cross-domain biodiversity × climate data as [ARC](https://arc-rdm.org/) / [RO-Crate](https://www.researchobject.org/ro-crate/) FAIR Digital Objects.
