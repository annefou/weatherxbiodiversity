# Analysis

Tests whether more frequent temperatures above historical baselines predict local extinction of species, following Soroye et al. (2020). It calculates Thermal and Precipitation Exposure Indices (baseline and change) for each species and grid cell, then fits a mixed-effects logistic regression of local extinction on these indices and sampling effort. The output is a summary of the model coefficients and a forest plot.

## Description

CWL tools for the Analysis part of the WeatherXBiodiversity replication
(Soroye et al. 2020). The input occurrences are the output of
`GBIF_Preprocessing` (generic cleaning of the GBIF download); step 01 adds the
study's definitions (continent, erroneous observations, periods, seasons).

Every tool is parameterized: study-level values
(species inputs, grid, years, seed, sampling settings) come from the CWL
inputs, never from the code. Method definitions (aggregations, formulas,
continent codes) stay in the code, matching the paper.

## Steps

| Step | Script | CWL | Inputs | Output |
|------|--------|-----|--------|--------|
| 01 | `01_study_records.py` | `01-study-records.cwl` | cleaned GBIF occurrences (`GBIF_Preprocessing`), erroneous observations (assay), continent | `clean_records.csv` |
| 02 | `02_presence_absence.py` | `02-presence-absence.cwl` | step 01 + grid + periods | `presence_absence.npz` |
| 03 | `03_sampling_continent.py` | `03-sampling-continent.cwl` | step 01 + grid | `sampling_continent.npz` |
| 04 | `04_climate_tei_pei.py` | `04-climate-tei-pei.cwl` | step 02 + climate dir + years + grid | `climate_tei_pei.npz` |
| 05a | `05a_build_data_glmm.py` | `05a-build-data-glmm.cwl` | steps 02+03+04 | `dataGLMM_extinction.parquet` |
| 05b | `05b_glmm_extinction.py` | `05b-glmm-extinction.cwl` | step 05a + seed | `logistic_summary.csv`, `posterior_vb_summary.csv` |
| 05 | `05_bayesian_glmm.py` | `05-bayesian-glmm.cwl` | step 05a + seed + sampling settings | `posterior_summary.csv`, `posterior.nc` |
| 06 | `06_forest_plot.py` | `06-forest-plot.cwl` | summary CSV (05b/05) + title/subtitle/color | `forest.png` |

Step 04 reads monthly climate files `<source>_{tmp,tmn,tmx,pre}_monthly_<start>_<end>.nc`
(`--climate-source`, default `era5`: the output of
`workflows/ERA5_Preprocessing/era5_to_climate.py`). Another climate source
(e.g. Destination Earth Climate DT) only needs to write the same files.

## Reproducibility notes

- 01–04, 05a: deterministic, validated bit-for-bit against the replication
  outputs.
- 05b: `fit_vb` is stochastic (mean-field VI); `--seed` is required and
  passed as `rng`, giving bit-for-bit reproducible fits.
- 05: MCMC is stochastic; `--seed` is required. Reproducibility is
  statistical (posterior means match across runs/containers within MCMC
  noise), not bit-for-bit.
- 06: deterministic for a given matplotlib version (validated pixel-for-
  pixel against `plot_forest.py`).

## Container

Single `Dockerfile` for all steps (micromamba + python + pandas/numpy/
pyproj/scipy/xarray/netcdf4 + pyarrow/statsmodels/bambi for step 05 +
matplotlib for step 06).