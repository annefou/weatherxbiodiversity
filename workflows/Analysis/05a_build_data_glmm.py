"""
Step 05a: assemble the model data table (dataGLMM) from the outputs of
steps 02, 03 and 04, and save it as dataGLMM_extinction.parquet.

Shared predecessor of both regressors:
  - 05b (statsmodels VB — the published path)
  - 05  (Bayesian GLMM via bambi — optional)

Port of Soroye et al. (2020) model-data assembly (5_binomialGLMM4Presence.R,
lines 85–116), parameterized as a CWL tool: all inputs/outputs are CLI
parameters, method constants stay in the code.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Assemble dataGLMM extinction table")
    p.add_argument("--presence-absence", type=Path, required=True,
                   help="presence_absence.npz from step 02")
    p.add_argument("--sampling-continent", type=Path, required=True,
                   help="sampling_continent.npz from step 03")
    p.add_argument("--climate-tei-pei", type=Path, required=True,
                   help="climate_tei_pei.npz from step 04")
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    a = parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    print('Loading intermediate data …')
    pa = np.load(a.presence_absence, allow_pickle=True)
    sc = np.load(a.sampling_continent, allow_pickle=True)
    cl = np.load(a.climate_tei_pei, allow_pickle=True)

    species_list = list(pa['species'])
    prab_baseline = pa['prab_baseline']   # (n_spp, n_cells) — 1/0/NaN
    prab_recent = pa['prab_recent']

    sampling_total = sc['samp_total']     # sum of all 6 season rasters (matches R)
    continent = sc['continent']           # (n_cells,) — 1 NA or 2 EUR

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

    print('\nAssembling dataGLMM …')
    rows = []
    for s, sp in enumerate(species_list):
        bs = prab_baseline[s]
        rc = prab_recent[s]

        # R pr_change = 2*p_recent - p_baseline
        with np.errstate(invalid='ignore'):
            pr_change = 2 * rc - bs
            extinction = np.where(
                pr_change == -1, 1.0,
                np.where((pr_change == 2) | (pr_change == 1), 0.0, np.nan),
            )
            colonization = np.where(
                pr_change == 2, 1.0,
                np.where((pr_change == -1) | (pr_change == 1), 0.0, np.nan),
            )

        for c in range(n_cells):
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
                'sampling': sampling_total[c],
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

    # z-score across the ENTIRE table; R scale() uses ddof=1
    def z(col):
        m = dataGLMM[col].mean()
        s = dataGLMM[col].std(ddof=1)
        return (dataGLMM[col] - m) / s

    dataGLMM['sc_sampling'] = z('sampling')
    dataGLMM['sc_TEI_bs'] = z('TEI_bs')
    dataGLMM['sc_TEI_delta'] = z('TEI_delta')
    dataGLMM['sc_PEI_bs'] = z('PEI_bs')
    dataGLMM['sc_PEI_delta'] = z('PEI_delta')
    dataGLMM['sc_avgtemp_bs'] = z('avgtemp_bs')
    dataGLMM['sc_avgtemp_delta'] = z('avgtemp_delta')
    dataGLMM['sc_avgprecip_bs'] = z('avgprecip_bs')
    dataGLMM['sc_avgprecip_delta'] = z('avgprecip_delta')

    dataGLMM['continent'] = dataGLMM['continent'].map({1: 'North America', 2: 'Europe'})
    dataGLMM['continent'] = pd.Categorical(dataGLMM['continent'],
                                           categories=['North America', 'Europe'])

    data_ext = dataGLMM[dataGLMM['extinction'].notna()].copy()
    print(f'  extinction subset: {len(data_ext):,} rows')
    print(f'    extinctions: {int((data_ext.extinction == 1).sum()):,}')
    print(f'    persistences: {int((data_ext.extinction == 0).sum()):,}')
    print(f'    species: {data_ext.species.nunique()}, cells: {data_ext.site.nunique()}')

    data_ext.to_parquet(a.output_dir / 'dataGLMM_extinction.parquet')


if __name__ == '__main__':
    main()
