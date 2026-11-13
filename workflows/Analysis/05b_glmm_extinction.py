"""
Step 05b: GLMM of extinction (the published path) via statsmodels.

Ports 05b_regression_statsmodels.py (Soroye et al. 2020 replication):
plain logistic + BinomialBayesMixedGLM (variational Bayes) with a
species random intercept. Fixed by the paper: formula, family,
variational fit; only inputs/outputs are parameters.

Outputs (fixed names): logistic_summary.csv, posterior_vb_summary.csv
"""
from __future__ import annotations

from pathlib import Path
import argparse
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import norm

FORMULA = (
    'extinction ~ continent + sc_sampling'
    ' + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta'
    ' + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta'
    ' + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta'
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extinction GLMM (statsmodels VB)")
    p.add_argument("--data", type=Path, required=True,
                   help="dataGLMM_extinction.parquet from step 05a")
    p.add_argument("--seed", type=int, required=True,
                   help="RNG seed for the variational Bayes fit (required for reproducibility)")
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    a = parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    data_ext = pd.read_parquet(a.data)
    print(f'Data: {len(data_ext):,} rows, {data_ext["species"].nunique()} species, {data_ext["site"].nunique()} cells')
    print(f'Extinction rate: {data_ext["extinction"].mean():.3f}')

    formula = FORMULA
    if data_ext['continent'].nunique() < 2:
        print('  continent is constant — dropping from formula')
        formula = formula.replace('continent + ', '')

    print('\n=== 1) Plain logistic regression (no species random effect) ===')
    try:
        glm = smf.logit(formula, data=data_ext).fit(disp=False, maxiter=200)
        print(glm.summary().tables[1])
        pd.DataFrame({
            'coef': glm.params, 'std_err': glm.bse,
            'z': glm.tvalues, 'pvalues': glm.pvalues,
        }).to_csv(a.output_dir / 'logistic_summary.csv')
    except Exception as e:
        print(f'  Plain logistic failed: {e}')
        glm = None

    print('\n=== 2) statsmodels BinomialBayesMixedGLM (species random effect) ===')
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

        md0 = smf.glm(formula, data=data_ext, family=sm.families.Binomial())
        exog_names = md0.exog_names
        print(f'  Fixed effects ({len(exog_names)}): {exog_names}')

        md = BinomialBayesMixedGLM.from_formula(
            formula,
            vc_formulas={'species': '0 + C(species)'},
            data=data_ext,
        )
        print('  Fitting variational Bayes (fast approximation) …')
        vb_result = md.fit_vb(rng=a.seed)
        print('\n  Fixed effects:')
        coef_df = pd.DataFrame({
            'mean': vb_result.fe_mean,
            'sd': vb_result.fe_sd,
        }, index=exog_names)
        coef_df['z'] = coef_df['mean'] / coef_df['sd']
        coef_df['p_2sided'] = 2 * (1 - norm.cdf(coef_df['z'].abs()))
        print(coef_df.round(4).to_string())
        coef_df.to_csv(a.output_dir / 'posterior_vb_summary.csv')
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'  Mixed Bayesian failed: {e}')
        vb_result = None

    if glm is not None:
        coef = glm.params.get('sc_TEI_delta', np.nan)
        pval = glm.pvalues.get('sc_TEI_delta', np.nan)
        print(f'\n=== PLAIN LOGIT — sc_TEI_delta ===')
        print(f'  coef: {coef:+.4f}  p = {pval:.4g}')
        print(f'  direction: {"POSITIVE — consistent with Soroye" if coef > 0 else "NEGATIVE — contradicts Soroye"}')

    if vb_result is not None:
        fe_names = list(md.exog_names)
        idx = fe_names.index('sc_TEI_delta')
        m = vb_result.fe_mean[idx]
        s = vb_result.fe_sd[idx]
        print(f'\n=== VB MIXED MODEL — sc_TEI_delta ===')
        print(f'  posterior mean: {m:+.4f}   sd: {s:.4f}')
        print(f'  95% approx CI: [{m - 1.96 * s:.4f}, {m + 1.96 * s:.4f}]')
        print(f'  direction: {"POSITIVE — consistent with Soroye" if m > 0 else "NEGATIVE — contradicts Soroye"}')

    print('\nDone.')


if __name__ == '__main__':
    main()
