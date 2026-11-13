"""
Step 05: Bayesian binomial GLMM of extinction via bambi (optional path).

Port of Soroye et al. (2020) script 5 (5_binomialGLMM4Presence.R,
pglmm_ext_linear at line 338):

  extinction ~ continent + sc_sampling
    + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta
    + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta
    + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta
    + (1|species)
  family = bernoulli

The formula and family are fixed by the paper; the sampling settings and
the RNG seed are parameters. Outputs: posterior_summary.csv, posterior.nc
"""
from __future__ import annotations

from pathlib import Path
import argparse
import os
import sys
import tempfile

import pandas as pd

os.environ.setdefault(
    'PYTENSOR_FLAGS',
    f'base_compiledir={Path(tempfile.gettempdir()) / "pytensor_compiledir"}',
)

FORMULA = (
    'extinction ~ continent + sc_sampling'
    ' + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta'
    ' + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta'
    ' + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta'
    ' + (1|species)'
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bayesian GLMM of extinction (bambi)")
    p.add_argument("--data", type=Path, required=True,
                   help="dataGLMM_extinction.parquet from step 05a")
    p.add_argument("--seed", type=int, required=True,
                   help="RNG seed for MCMC sampling (required for reproducibility)")
    p.add_argument("--draws", type=int, required=True)
    p.add_argument("--tune", type=int, required=True)
    p.add_argument("--chains", type=int, required=True)
    p.add_argument("--target-accept", type=float, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    a = parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    data_ext = pd.read_parquet(a.data)
    print(f'Data: {len(data_ext):,} rows, {data_ext["species"].nunique()} species, {data_ext["site"].nunique()} cells')

    try:
        import bambi as bmb
        import arviz as az
    except ModuleNotFoundError as e:
        sys.exit(
            f"{e.name} is not installed — it is an optional dependency of the "
            "Bayesian path. Install with: micromamba install -c conda-forge bambi"
        )

    formula = FORMULA
    if data_ext['continent'].nunique() < 2:
        print('  continent is constant — dropping from formula')
        formula = formula.replace('continent + ', '')

    print('\nFitting Bayesian GLMM via bambi …')
    model = bmb.Model(formula, data_ext, family='bernoulli')
    print(model)

    idata = model.fit(
        draws=a.draws, tune=a.tune, chains=a.chains,
        target_accept=a.target_accept, seed=a.seed,
        progressbar=False, idata_kwargs={'log_likelihood': False},
    )

    try:  # arviz >= 1.0 renamed hdi_prob -> ci_prob
        summary = az.summary(idata, ci_prob=0.95, ci_kind='hdi')
    except TypeError:
        summary = az.summary(idata, hdi_prob=0.95)
    print('\n=== Posterior summary ===')
    print(summary.to_string())

    summary.to_csv(a.output_dir / 'posterior_summary.csv')

    lo = next(c for c in summary.columns if 'lb' in c or '2.5' in c)
    hi = next(c for c in summary.columns if 'ub' in c or '97.5' in c)
    key_row = summary.loc['sc_TEI_delta']
    print(f"\n=== KEY TARGET COEFFICIENT ===")
    print(f"sc_TEI_delta posterior mean: {key_row['mean']:.4f}")
    print(f"  95% HDI: [{key_row[lo]:.4f}, {key_row[hi]:.4f}]")
    print(f"  sign: {'POSITIVE (consistent with Soroye)' if key_row['mean'] > 0 else 'NEGATIVE (contradicts Soroye)'}")

    idata.to_netcdf(a.output_dir / 'posterior.nc')
    print(f"\nSaved posterior summary + netcdf to {a.output_dir}")


if __name__ == '__main__':
    main()
