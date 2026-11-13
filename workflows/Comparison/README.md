# Comparison (`compare_sources.py`)

The Analysis results of the climate sources side by side: the same GBIF
records and the same code, only the climate data differ.

- `coefficients.csv`: every coefficient per source (mean, sd, 95% interval,
  number of model rows);
- `forest_comparison.png`: all coefficients, sources side by side,
  `sc_TEI_delta` (the effect of warming tested by Soroye et al.) highlighted.

```bash
python compare_sources.py --source cru results/iberia/cru "CRU TS 3.24.01 (paper)" \
    --source era5 results/iberia/era5 ERA5 --output-dir results/iberia/comparison
```

Snakemake rule: `comparison` (sources from `config/iberia.yaml`, `analysis.sources`).

The number of model rows differs between sources: CRU TS is a land-only
dataset, so coastal grid cells get no climate value, whereas the ERA5 boxes
cover them. The sources are therefore not fitted on exactly the same
species × grid-cell combinations.

## Same rows

`common_rows.py` restricts the model table of every source to the species ×
grid-cell rows common to all sources, re-standardises the predictors within
those rows (as Analysis 05a does over its table), and the rules refit them
with Analysis 05b and compare them (`results/<study>/comparison/common_rows/`).
This separates the effect of the climate values from that of the coverage.

## A source restricted to a period

`climate_period.py` makes a climate source from another one restricted to a
period, e.g. `cru_1940` (CRU TS on ERA5's years, 1940–2014; `config/iberia.yaml`,
`climate.cru_1940.period_of: cru`), to separate the effect of the dataset from
that of the period (ERA5 starts in 1940).
