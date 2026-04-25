# Methods

This page documents the Python re-implementation of Soroye et al. 2020's
analysis pipeline. The full code lives in `soroye_port/` in the repository
([Zenodo concept DOI 10.5281/zenodo.19756173](https://doi.org/10.5281/zenodo.19756173)).

## The five-script pipeline

Each Python script is a port of one of the R scripts in Soroye's Figshare
release ([10.6084/m9.figshare.9956471](https://doi.org/10.6084/m9.figshare.9956471)).

| Script | R original | Purpose |
|---|---|---|
| `01_clean_data.py` (Phase 2) | `1_Cleandata_and_makeMCPs.R` | Continental *Bombus* cleaning |
| `01_clean_data_iberia.py` (Phase 3) | adapted | Iberian GBIF cleaning |
| `02_presence_absence.py` | `2_CalcSpeciesPr_Rich.R` | 100 km equal-area presence/absence rasters |
| `03_sampling_continent.py` | `3_CalcSamplingEffort_Cont.R` | Per-cell sampling effort + continent |
| `04_climate_tei_pei.py` | climate-position helpers | Per-species TEI / PEI |
| `05_regression.py` | `5_binomialGLMM4Presence.R` (bambi/MCMC) | Mixed-effects GLMM, MCMC |
| `05b_regression_statsmodels.py` | fallback | Variational Bayes mixed-effects GLMM |

All scripts 02–05 read an `OUT_SUBDIR` environment variable that controls
whether they operate on Phase 2 (`outputs/`) or Phase 3 (`outputs_iberia/`)
intermediates. Only the `01_clean_*.py` script differs between phases.

## The 100 km cylindrical equal-area grid

Following Soroye 2020:

- Projection: `+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84`
- Bounds: x ∈ [−20 037 507, 20 062 493], y ∈ [−5 263 885, 6 336 115]
- Resolution: 401 × 116 = 46 516 cells globally, of which the *Bombus*
  range covers ~13 600 cells (Phase 2) or ~99 sampled Iberian cells (Phase 3).

Continent assignment: `lon < −25` ⇒ North America, otherwise Europe
(Iberia is naturally classified as Europe).

## Periods and seasons

- Baseline: 1901–1974, three 25-year sub-windows
- Recent: 2000–2014, three 5-year sub-windows
- 6 total period-season combinations

## Thermal Exposure Index (TEI)

The original paper's TEI is the rate at which monthly maximum temperatures
exceed the species-specific historical maximum. Mathematically, for
species $s$ in cell $c$:

- Compute the species' **historical thermal limits** $T_{\min}^s$ and
  $T_{\max}^s$ from baseline data: respectively the 5-lowest-monthly-min
  and 5-highest-monthly-max averages across cells where $s$ was observed.
- For each year, count months where $T_{\max} > T_{\max}^s$ (and parallel
  cold-side counts).
- Average across years to get a per-period **climatic position index** in
  [0, 1].
- TEI is the difference between baseline and recent period CPI.

By **linearity of CPI**, this is equivalent to computing CPI from the
period-mean temperatures rather than averaging per-year CPI values. The
Python port uses the linearised form for speed; the result is identical
to within floating-point.

PEI is the analogous Precipitation Exposure Index.

## Mixed-effects logistic GLMM

The model fitted on the species × cell observation matrix is:

```
extinction ~ continent
           + sc_sampling
           + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta
           + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta
           + sc_TEI_bs:sc_PEI_bs
           + sc_TEI_delta:sc_PEI_delta
           + (1 | species)
```

`sc_*` denotes z-score standardisation (Bessel-corrected, i.e. `ddof=1`,
matching R's `scale()`). Soroye's R code uses `MCMCglmm` with full Markov-
chain Monte Carlo. This work uses `statsmodels.BinomialBayesMixedGLM`
with variational Bayes — a fast approximation that preserves point
estimates and signs but typically underestimates credible-interval widths
by 10–20 %.

## Definitions of the response variable

Following the R code (`5_binomialGLMM4Presence.R`):

- `pr_change = 2 × rc − bs` (where `bs` and `rc` are baseline and recent
  presence/absence indicators in {0, 1})
- `extinction = 1` if `pr_change == −1` (present at baseline, absent
  recently)
- `extinction = 0` if `pr_change == 2` (colonisation) or `pr_change == 1`
  (persistence)
- `extinction = NA` otherwise (never sampled in either period)

Three discrepancies between an early simplified port and Soroye's R code
were caught and fixed in v0.2.0:

1. Sampling effort: the `samp` column must sum across all 6 period-season
   rasters (`stackApply(... rep(1, 6), sum)` in the R), not baseline only.
2. z-scoring: `numpy.std` defaults to `ddof=0`; R's `scale()` uses
   Bessel-corrected `ddof=1`. The Python port now matches R.
3. Extinction definition: persistence (bs=1, rc=1) AND colonisation
   (bs=0, rc=1) are both `extinction = 0`. An early version only counted
   persistence as 0, which inflated extinction rate from 51 % to 60 %.

## GBIF data acquisition (Phase 3 only)

The Iberian *Bombus* dataset is fetched via the GBIF Occurrence Download
API in `notebooks/01b_gbif_download_doi.py`:

- Predicate: `genusKey = 1340278 ∧ country ∈ {ES, PT} ∧ hasCoordinate ∧ ¬hasGeospatialIssue`
- Format: SIMPLE_CSV (tab-separated)
- Output: 36 560 records, citable as
  [10.15468/dl.3frmsq](https://doi.org/10.15468/dl.3frmsq) under
  CC-BY-NC 4.0

The script submits the download, polls until completion, and saves the
DOI + metadata to `data/gbif_bombus_iberia_metadata.json`. Re-running it
mints a new DOI rather than re-downloading the original; the existing DOI
remains valid for citation.

## Reproducibility

- Environment: see `environment.yml` (Python 3.12, conda-forge channel).
  CI uses `mamba-org/setup-micromamba@v3` with the same file.
- Container: `Dockerfile` builds an image with the full pipeline; archived
  as a citable Docker image on Zenodo.
- Pipeline orchestration: `Snakefile`. CI workflow runs the Phase 2 port
  end-to-end on every push.
