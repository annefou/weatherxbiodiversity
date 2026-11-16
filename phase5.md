# Phase 5 — Continental data with ERA5

Phase 4 found that the Iberian replication does not hold when CRU TS is
replaced by ERA5. Phase 5 asks: **does Soroye et al.'s claim hold with ERA5 on
their own continental data?**

Same records as Phase 2 (Soroye et al.'s data deposit: 66 *Bombus* species,
North America and Europe), same code and model as Phase 4; only the climate
dataset changes:

- **CRU TS 3.24.01**, the climate data of Soroye et al. (2020), 1901–2015;
- **CRU TS restricted to 1940–2014**, ERA5's years (baseline climate 1940–1974);
- **ERA5**, 1940–2014, retrieved only for the ARCO store tiles around the
  1,905 grid cells with records (about 3,000 one-degree tiles).

## Headline result

| Climate data | `sc_TEI_delta`, all rows | Rows | `sc_TEI_delta`, the same 13,614 rows |
|---|---:|---:|---:|
| CRU TS 3.24.01 (paper), 1901–2015 | **+0.15** [0.12, 0.19] | 13,614 | **+0.15** [0.12, 0.19] |
| CRU TS, 1940–2014 only | **+0.19** [0.15, 0.22] | 13,614 | **+0.19** [0.15, 0.22] |
| ERA5, 1940–2014 | **+0.14** [0.10, 0.17] | 15,268 | **+0.11** [0.07, 0.15] |

Posterior mean and 95 % interval of the mixed-effects model (variational
Bayes, seed 42).

With CRU TS the workflow gives back Phase 2 (+0.153 with the original Python
port, +0.152 with the workflow), so the workflow code reproduces the paper on
the continental data. **With ERA5 the claim also holds**: the effect of the
change in thermal exposure on local extinction is positive and credible, on
all ERA5 rows and on exactly the rows CRU TS covers. It is somewhat smaller
than with CRU TS (+0.11 against +0.15 on the same rows).

```{figure} figures/phase5_forest_common_rows.png
:alt: Forest plot of all model coefficients for CRU TS, CRU TS restricted to 1940-2014, and ERA5, on the same 13,614 rows of the continental data
:width: 100%

All model coefficients for the three climate sources, on the same 13,614
species × grid-cell rows of Soroye et al.'s continental data. The highlighted
row, `sc_TEI_delta`, is the effect of the change in thermal exposure tested
by Soroye et al. (2020).
```

The same figure with every source on all its rows:
[`figures/phase5_forest_all_rows.png`](figures/phase5_forest_all_rows.png).
ERA5 has 1,654 more rows than CRU TS (1,406 in Europe, 248 in North America):
cells near the coast, where the land-only CRU TS has no value.

## What differs between the climate datasets

On the 13,614 common rows the response (local extinction, 51.3 % of the rows)
is identical. Comparing CRU TS restricted to 1940–2014 with ERA5:

| Quantity (mean over the rows) | CRU TS 1940–2014 | ERA5 | Correlation per row |
|---|---:|---:|---:|
| Baseline mean temperature (°C) | 6.87 | 6.73 | 0.99 |
| Warming, recent − baseline (°C) | 0.88 | 1.13 | 0.43 |
| `TEI_delta` | 0.013 | 0.016 | 0.57 |
| Precipitation change (mm) | 34.0 | 40.7 | 0.60 |
| `PEI_delta` | 0.012 | 0.015 | 0.59 |

- The two datasets agree on the baseline climate, much less on the change
  per cell: ERA5 warms more on average, and the per-row correlation of
  `TEI_delta` is lower than in Iberia (0.57 against 0.80).
- Despite this, the effect of thermal exposure is found with both, which
  suggests that over 66 species and two continents the signal does not depend
  on the details of one climate dataset.
- Other coefficients do depend on the dataset: the change in precipitation
  exposure (`sc_PEI_delta`) is negative with CRU TS and positive with ERA5,
  and the interaction of baseline and change in thermal exposure is weaker
  with ERA5.

These are observations, not a tested mechanism.

## Phase 4 and Phase 5 together

| | Iberia (Phase 4) | North America + Europe (Phase 5) |
|---|---|---|
| Records | GBIF, 31 species | Soroye et al.'s data, 66 species |
| Rows (same rows) | 528 | 13,614 |
| CRU TS | +0.48, holds | +0.15, holds |
| CRU TS 1940–2014 | +0.46, holds | +0.19, holds |
| ERA5 | +0.05, **not detected** | +0.11, **holds** |
| Per-row correlation of `TEI_delta` | 0.80 | 0.57 |
| Per-row correlation of precipitation change | 0.13 | 0.60 |

Soroye et al.'s continental claim holds with ERA5; the Iberian replication
does not. In a single region with few species and cells, the result can
depend on the climate dataset, here mostly through the precipitation terms,
on which CRU TS and ERA5 hardly agree in Iberia. For reusing the method in
other regions this means: enough species × cells, and a check with a second
climate dataset.

## Reproduce

The records come from Soroye et al.'s data deposit
([Figshare, 10.6084/m9.figshare.9956471](https://doi.org/10.6084/m9.figshare.9956471)),
unpacked under `reference/Bumblebee_repo_wbombusdat/` (path set in
`config/continental.yaml`), and are cleaned with the Phase 2 port
(`soroye_port/01_clean_data.py`) by the `Soroye_Records` step.

```bash
pixi install
cp credentials/cds_credentials.example.json credentials/cds_credentials.json   # add your CDS API key
pixi run snakemake --configfile config/continental.yaml --cores 4
```

The ERA5 retrieval takes about 13 hours (about 3,000 store tiles, 10 time
chunks each). Downloads go to `data/continental/`, results to
`results/continental/` (one folder per climate source, and `comparison/`).
