"""
Python port of Soroye et al. (2020) — script 5 (Bayesian path).

Source: 5_binomialGLMM4Presence.R  (pglmm_ext_linear at line 338)

R formula:
  extinction ~ continent + sc_sampling
    + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta
    + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta
    + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta
  random = ~ species
  family = categorical (binomial)

In Python via bambi/pymc:
  extinction ~ continent + sc_sampling
    + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta
    + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta
    + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta
    + (1|species)
  family = bernoulli

The model-data assembly (dataGLMM → dataGLMM_extinction.parquet) lives in
05a_build_dataGLMM.py and runs here by import, so this script and 05b
start from exactly the same table. bambi is an optional dependency: it is
not in environment.yml and not needed for the published numbers, which
come from 05b (statsmodels VB).
"""
from __future__ import annotations

import importlib.util as _ilu
from pathlib import Path
import sys

_spec = _ilu.spec_from_file_location(
    'build_dataglmm', Path(__file__).with_name('05a_build_dataGLMM.py'))
_dataglmm = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_dataglmm)

data_ext = _dataglmm.data_ext
OUT_DIR = _dataglmm.OUT_DIR

# ---------------------------------------------------------------------------
# Run the Bayesian GLMM via bambi

try:
    import bambi as bmb
    import arviz as az
except ModuleNotFoundError as e:
    sys.exit(
        f"{e.name} is not installed — it is an optional dependency of the "
        "Bayesian path (not in environment.yml; the published results come "
        "from 05b_regression_statsmodels.py). Install it with: "
        "micromamba install -c conda-forge bambi"
    )

print('\nFitting Bayesian GLMM via bambi …')

formula = (
    'extinction ~ continent + sc_sampling'
    ' + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta'
    ' + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta'
    ' + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta'
    ' + (1|species)'
)
# If `continent` is constant in the subset (e.g. Iberia-only run), drop it
# from the formula — otherwise the design matrix is singular.
if data_ext['continent'].nunique() < 2:
    print('  continent is constant — dropping from formula')
    formula = formula.replace('continent + ', '')

model = bmb.Model(formula, data_ext, family='bernoulli')
print(model)

# MCMC: smaller than R's 155000 for faster run; pymc draws are post-burn
idata = model.fit(
    draws=2000, tune=1000, chains=2, target_accept=0.95,
    progressbar=True, idata_kwargs={'log_likelihood': False},
)

# ---------------------------------------------------------------------------
# Report posterior means and 95% credible intervals

summary = az.summary(idata, hdi_prob=0.95)
print('\n=== Posterior summary ===')
print(summary.to_string())

# Persist the fit output
summary.to_csv(OUT_DIR / 'posterior_summary.csv')

# Extract TEI_delta row (our key coefficient to compare with Soroye's paper)
key_row = summary.loc['sc_TEI_delta']
print(f"\n=== KEY TARGET COEFFICIENT ===")
print(f"sc_TEI_delta posterior mean: {key_row['mean']:.4f}")
print(f"  95% HDI: [{key_row['hdi_2.5%']:.4f}, {key_row['hdi_97.5%']:.4f}]")
print(f"  sign: {'POSITIVE (consistent with Soroye)' if key_row['mean'] > 0 else 'NEGATIVE (contradicts Soroye)'}")

# Save raw posterior for later analysis
idata.to_netcdf(OUT_DIR / 'posterior.nc')
print(f"\nSaved posterior summary + netcdf to {OUT_DIR}")
