"""
Step 5a: assemble the model data table (dataGLMM) from the outputs of
scripts 02, 03 and 04, and save it as dataGLMM_extinction.parquet.

This is the shared predecessor of both regressors:
  - 05_regression.py           (Bayesian GLMM via bambi — needs `bambi`)
  - 05b_regression_statsmodels.py (statsmodels VB — the published path)

It is also a Snakefile step (port_dataglmm), so the pipeline runs end to
end on a clean checkout without invoking the optional Bayesian script.
Requires only numpy/pandas/pyarrow, all in environment.yml.
"""
from __future__ import annotations

from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
import os as _os
OUT_DIR = ROOT / 'soroye_port' / _os.environ.get('OUT_SUBDIR', 'outputs')

# ---------------------------------------------------------------------------
# Load intermediate data from scripts 02, 03, 04

print('Loading intermediate data …')
pa = np.load(OUT_DIR / 'presence_absence.npz', allow_pickle=True)
sc = np.load(OUT_DIR / 'sampling_continent.npz', allow_pickle=True)
cl = np.load(OUT_DIR / 'climate_tei_pei.npz', allow_pickle=True)

species_list = list(pa['species'])
prab_baseline = pa['prab_baseline']   # (n_spp, n_cells) — 1=present, 0=absent, NaN=not sampled
prab_recent = pa['prab_recent']

sampling_baseline = sc['samp_baseline']
sampling_recent = sc['samp_recent']
sampling_total = sc['samp_total']      # ← sum of all 6 season rasters (matches R)
continent = sc['continent']           # (n_cells,) — 1 NA or 2 EUR
n_x, n_y = int(pa['n_x']), int(pa['n_y'])

avgtemp_bs = cl['avgtemp_bs']
avgtemp_delta = cl['avgtemp_delta']
avgprecip_bs = cl['avgprecip_bs']
avgprecip_delta = cl['avgprecip_delta']
TEI_bs = cl['TEI_bs']                 # (n_spp, n_cells)
TEI_delta = cl['TEI_delta']
PEI_bs = cl['PEI_bs']
PEI_delta = cl['PEI_delta']

n_spp, n_cells = prab_baseline.shape
print(f'  {n_spp} species × {n_cells:,} cells')

# ---------------------------------------------------------------------------
# Build dataGLMM — one row per (species, cell) with all covariates.
# R lines 85–116: construct sppdat for each species, rbind all species together

print('\nAssembling dataGLMM …')
rows = []
for s, sp in enumerate(species_list):
    # Extinction flag: 1 if present in baseline AND absent in recent
    # 0 if present in baseline AND present in recent (persistence)
    # NaN if absent in baseline (not at risk)
    bs = prab_baseline[s]
    rc = prab_recent[s]

    # R pr_change = 2*p_recent - p_baseline
    # R:  pr_extinct = 1 if pr_change == -1 (bs=1, rc=0)
    #                = 0 if pr_change == 2  (bs=0, rc=1  = colonization) OR
    #                     pr_change == 1  (bs=1, rc=1  = persistence)
    #                = NA otherwise (pr_change==0: never detected, or NaN in either)
    with np.errstate(invalid='ignore'):
        pr_change = 2 * rc - bs
        extinction = np.where(
            pr_change == -1, 1.0,
            np.where((pr_change == 2) | (pr_change == 1), 0.0, np.nan),
        )
        # Colonization analogue (not used in extinction model but kept for parity)
        colonization = np.where(
            pr_change == 2, 1.0,
            np.where((pr_change == -1) | (pr_change == 1), 0.0, np.nan),
        )

    for c in range(n_cells):
        # Skip cells with no sampling or no baseline presence/absence info
        if np.isnan(extinction[c]) and np.isnan(colonization[c]):
            continue
        if np.isnan(continent[c]) or np.isnan(sampling_total[c]):
            continue
        if np.isnan(TEI_bs[s, c]) or np.isnan(TEI_delta[s, c]):
            continue
        if np.isnan(PEI_bs[s, c]) or np.isnan(PEI_delta[s, c]):
            continue
        rows.append({
            'species': sp,
            'site': c,
            'extinction': extinction[c],
            'colonization': colonization[c],
            'continent': int(continent[c]),
            'sampling': sampling_total[c],   # R's `sampling` = sum over all 6 seasons
            'TEI_bs': TEI_bs[s, c],
            'TEI_delta': TEI_delta[s, c],
            'PEI_bs': PEI_bs[s, c],
            'PEI_delta': PEI_delta[s, c],
            'avgtemp_bs': avgtemp_bs[c],
            'avgtemp_delta': avgtemp_delta[c],
            'avgprecip_bs': avgprecip_bs[c],
            'avgprecip_delta': avgprecip_delta[c],
        })

dataGLMM = pd.DataFrame(rows)
print(f'  dataGLMM: {len(dataGLMM):,} rows')

# ---------------------------------------------------------------------------
# Scale continuous variables (z-score) — R uses `scale()` which is z-score by default
# R's `scale()` uses sample SD with Bessel's correction (ddof=1). Match that exactly.
# The R code scales across the ENTIRE dataGLMM (all species/cells combined).

def z(col):
    m = dataGLMM[col].mean()
    s = dataGLMM[col].std(ddof=1)   # ddof=1 matches R's scale()
    return (dataGLMM[col] - m) / s

dataGLMM['sc_sampling'] = z('sampling')
dataGLMM['sc_TEI_bs']    = z('TEI_bs')
dataGLMM['sc_TEI_delta'] = z('TEI_delta')
dataGLMM['sc_PEI_bs']    = z('PEI_bs')
dataGLMM['sc_PEI_delta'] = z('PEI_delta')
dataGLMM['sc_avgtemp_bs'] = z('avgtemp_bs')
dataGLMM['sc_avgtemp_delta'] = z('avgtemp_delta')
dataGLMM['sc_avgprecip_bs'] = z('avgprecip_bs')
dataGLMM['sc_avgprecip_delta'] = z('avgprecip_delta')

# R continent factor: 1=NA, 2=EUR → in R recoded to c("North America","Europe") with level order
dataGLMM['continent'] = dataGLMM['continent'].map({1: 'North America', 2: 'Europe'})
dataGLMM['continent'] = pd.Categorical(dataGLMM['continent'], categories=['North America', 'Europe'])

# Extinction subset — only rows with a defined extinction target
data_ext = dataGLMM[dataGLMM['extinction'].notna()].copy()
print(f'  extinction subset: {len(data_ext):,} rows')
print(f'    extinctions: {int((data_ext.extinction == 1).sum()):,}')
print(f'    persistences: {int((data_ext.extinction == 0).sum()):,}')
print(f'    species: {data_ext.species.nunique()}, cells: {data_ext.site.nunique()}')

# Save the assembled table for reuse
data_ext.to_parquet(OUT_DIR / 'dataGLMM_extinction.parquet')
