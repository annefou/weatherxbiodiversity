"""
Fallback: run the same regression using statsmodels GLM with a fixed-effects
approximation. Soroye's R code at line 267 says "pglmm_ext_nophylo results
similar to lme4 models", so a frequentist GLM/GLMM is an adequate approximation
while the pytensor-based Bayesian MCMC is blocked by macOS CLT issues.

Starts with a plain logistic (no random effect) and then tries MixedLM with
species random intercept.
"""
from __future__ import annotations

from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
import os as _os
OUT_DIR = ROOT / 'soroye_port' / _os.environ.get('OUT_SUBDIR', 'outputs')

data_ext = pd.read_parquet(OUT_DIR / 'dataGLMM_extinction.parquet')
print(f'Data: {len(data_ext):,} rows, {data_ext["species"].nunique()} species, {data_ext["site"].nunique()} cells')
print(f'Extinction rate: {data_ext["extinction"].mean():.3f}')

FORMULA = (
    'extinction ~ continent + sc_sampling'
    ' + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta'
    ' + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta'
    ' + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta'
)
# If continent is constant in this dataset (e.g. Iberia), drop it
if data_ext['continent'].nunique() < 2:
    print('  continent is constant — dropping from formula')
    FORMULA = FORMULA.replace('continent + ', '')

# ---------------------------------------------------------------------------
# 1. Plain logistic regression (no random effect) — fast, reference
print('\n=== 1) Plain logistic regression (no species random effect) ===')
try:
    glm = smf.logit(FORMULA, data=data_ext).fit(disp=False, maxiter=200)
    print(glm.summary().tables[1])
except Exception as e:
    print(f'  Plain logistic failed: {e}')
    glm = None

# ---------------------------------------------------------------------------
# 2. BinomialBayesMixedGLM (Laplace / variational) with species random effect
print('\n=== 2) statsmodels BinomialBayesMixedGLM (species random effect) ===')
try:
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    # Build design matrix manually from FORMULA using patsy via glm's exog if available
    # Use smf.glm to get the fixed-effect design (no random)
    md0 = smf.glm(FORMULA, data=data_ext, family=sm.families.Binomial())
    exog = md0.exog
    exog_names = md0.exog_names
    print(f'  Fixed effects ({len(exog_names)}): {exog_names}')

    # species → integer codes → one-hot
    spp_codes = data_ext['species'].astype('category').cat.codes.values
    n_spp = len(data_ext['species'].astype('category').cat.categories)
    # ident array so each species is a separate group for the random effect
    exog_vc = {'species': {f's{i}': (spp_codes == i).astype(float) for i in range(n_spp)}}
    ident = np.zeros(n_spp, dtype=int)

    # BinomialBayesMixedGLM expects exog_vc as a special format — easier to use from_formula
    md = BinomialBayesMixedGLM.from_formula(
        FORMULA,
        vc_formulas={'species': '0 + C(species)'},
        data=data_ext,
    )
    print('  Fitting variational Bayes (fast approximation) …')
    vb_result = md.fit_vb()
    print(f'\n  Fixed effects:')
    coef_df = pd.DataFrame({
        'mean': vb_result.fe_mean,
        'sd':   vb_result.fe_sd,
    }, index=exog_names)
    coef_df['z']     = coef_df['mean'] / coef_df['sd']
    coef_df['p_2sided'] = 2 * (1 - __import__('scipy.stats', fromlist=['norm']).norm.cdf(coef_df['z'].abs()))
    print(coef_df.round(4).to_string())
    coef_df.to_csv(OUT_DIR / 'posterior_vb_summary.csv')
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'  Mixed Bayesian failed: {e}')
    vb_result = None

# ---------------------------------------------------------------------------
# Key coefficient report
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
    print(f'  95% approx CI: [{m - 1.96*s:.4f}, {m + 1.96*s:.4f}]')
    print(f'  direction: {"POSITIVE — consistent with Soroye" if m > 0 else "NEGATIVE — contradicts Soroye"}')

print('\nDone.')
