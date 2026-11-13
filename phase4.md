# Phase 4 — Climate data sensitivity: CRU TS vs ERA5

Phase 4 asks: **does the Iberian replication of Phase 3 hold when the
climate data change, with everything else kept the same?**

This is a robustness check of the regional replication. Same occurrence
records, same code, same grid and periods. Only the climate dataset from
which the thermal and precipitation exposure indices (TEI, PEI) are computed
changes:

- **CRU TS 3.24.01**, the climate data of Soroye et al. (2020): monthly
  station-based interpolation, 0.5°, land only, from 1901;
- **ERA5**, the ECMWF reanalysis: hourly data aggregated to monthly
  statistics with the same definitions (monthly mean, mean daily minimum
  and maximum temperature, monthly precipitation), 0.25°, from 1940.

## What was changed

| Element | Phase 3 | Phase 4 |
|---|---|---|
| Occurrence data | GBIF *Bombus*, ES + PT, [10.15468/dl.3frmsq](https://doi.org/10.15468/dl.3frmsq) | Same records |
| Climate | CRU TS 3.24.01 | CRU TS 3.24.01 **and** ERA5 (and CRU TS restricted to 1940–2014) |
| Pipeline | `soroye_port/` | The workflow (`Snakefile`, `workflows/`): the same steps as the [ARC](https://git.nfdi4plants.org/lifewatch-eric/WeatherXBiodiversity_Soroye2020) |
| Grid, periods, model spec | Soroye et al. (2020) | Unchanged |

ERA5 starts in 1940, so its baseline climate is 1940–1974 (CRU TS: 1901–1974).
To separate the effect of the dataset from that of the period, the analysis
was also run with **CRU TS restricted to ERA5's years** (1940–2014).

CRU TS is land only, so coastal grid cells have no CRU value, whereas the
ERA5 retrieval boxes cover them: the ERA5 model table has 679 species × cell
rows, the CRU one 528. To separate the effect of the climate values from that
of the coverage, all sources were also fitted on **the 528 rows common to
all**, with the predictors re-standardised within those rows.

## Headline result

| Climate data | `sc_TEI_delta`, all rows | Rows | `sc_TEI_delta`, the same 528 rows |
|---|---:|---:|---:|
| CRU TS 3.24.01 (paper), 1901–2015 | **+0.48** [0.26, 0.69] | 528 | **+0.48** [0.26, 0.69] |
| CRU TS, 1940–2014 only | **+0.46** [0.25, 0.67] | 528 | **+0.46** [0.25, 0.67] |
| ERA5, 1940–2014 | **−0.05** [−0.24, 0.14] | 679 | **+0.05** [−0.16, 0.26] |

Posterior mean and 95 % interval of the mixed-effects model (variational
Bayes, seed 42).

With CRU TS the regional replication holds, and it still holds when CRU TS is
restricted to ERA5's years. With ERA5 the effect of warming on local
extinction is not detectable, on all its rows and on exactly the rows CRU TS
covers. **The Iberian replication of Soroye's claim depends on the climate
dataset**, not on the baseline period or on the coverage.

```{figure} figures/phase4_forest_common_rows.png
:alt: Forest plot of all model coefficients for CRU TS, CRU TS restricted to 1940-2014, and ERA5, on the same 528 rows
:width: 100%

All model coefficients for the three climate sources, on the same 528
species × grid-cell rows. The highlighted row, `sc_TEI_delta`, is the effect
of the change in thermal exposure tested by Soroye et al. (2020).
```

The same figure with every source on all its rows:
[`figures/phase4_forest_all_rows.png`](figures/phase4_forest_all_rows.png).

## What differs between the climate datasets

On the 528 common rows the response (local extinction, 35.6 % of the rows) is
identical, so only the climate predictors differ. Comparing CRU TS restricted
to 1940–2014 with ERA5:

| Quantity (mean over the rows) | CRU TS 1940–2014 | ERA5 | Correlation per row |
|---|---:|---:|---:|
| Baseline mean temperature (°C) | 11.75 | 11.42 | 0.93 |
| Warming, recent − baseline (°C) | 1.07 | 1.24 | 0.80 |
| `TEI_delta` | 0.026 | 0.025 | 0.80 |
| Precipitation change (mm) | −17.7 | −11.1 | **0.13** |
| `PEI_delta` | −0.016 | −0.005 | **0.17** |

- The two datasets agree on the average warming and on the average change in
  thermal exposure, and moderately per grid cell (correlation 0.80).
- With CRU TS the change in thermal exposure separates the extinct from the
  persisting species × cell combinations more clearly (mean `TEI_delta`
  0.0265 vs 0.0253) than with ERA5 (0.0254 vs 0.0250).
- The datasets hardly agree on the change in precipitation (correlation 0.13).
  The model estimates the effect of warming jointly with the precipitation
  terms and their interactions, so this disagreement also affects
  `sc_TEI_delta`.

These are observations, not a tested mechanism. A station-based
interpolation (CRU TS) and a reanalysis (ERA5) can differ most where stations
are sparse and in precipitation, which is the more variable field.

## Note on Phase 3

The workflow downloads CRU TS 3.24.01 from its producer, the
[University of East Anglia](https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_3.24.01/).
Over the study region, 42 of the 44 files are identical to the local copy of
Soroye et al.'s data deposit used in Phase 3. In that copy, `tmx` 2011–2015 is
missing and `tmp` 2011–2015 is damaged (its time axis runs from 2011 back to
1900). The Phase 3 code also summed monthly precipitation with missing values
skipped, giving 0 mm over the sea next to the coast (fixed in the workflow).
`sc_TEI_delta` is barely affected (Phase 3: +0.479; the workflow with CRU TS:
+0.478); other coefficients differ by up to 0.03.

## Reproduce

```bash
pixi install
cp credentials/cds_credentials.example.json credentials/cds_credentials.json   # add your CDS API key
pixi run snakemake --cores 1
```

The comparison is in `results/iberia/comparison/` (all rows) and
`results/iberia/comparison/common_rows/` (the same rows): `coefficients.csv`
and `forest_comparison.png`. The climate sources compared are set in
`config/iberia.yaml` (`analysis.sources`).
