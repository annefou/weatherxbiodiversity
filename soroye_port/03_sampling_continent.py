"""
Python port of Soroye et al. (2020) — script 3.

Source: 3_CalcSamplingEffort_Cont.R

Builds:
  - beedat_samp: raster per (period, season) — count of distinct LYID per cell
      * missing cells that were sampled in other seasons are set to 0 (not NaN)
  - beedat_samp_period: sum across 3 seasons per period (p1, p2)
  - beedat_continent: per-cell mean of continent code (1=NA, 2=EUR)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent
import os as _os
OUT_DIR = ROOT / 'soroye_port' / _os.environ.get('OUT_SUBDIR', 'outputs')
IN_CSV = OUT_DIR / 'bombus_clean.csv'

# Reuse grid config from script 02
RES_M = 100_000
X_MIN, X_MAX = -20_037_507, 20_062_493
Y_MIN, Y_MAX = -5_263_885, 6_336_115

transformer = Transformer.from_crs(
    'EPSG:4326', '+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84', always_xy=True,
)

def cell_ids(lon, lat, n_x, n_y):
    x, y = transformer.transform(lon, lat)
    col = np.floor((x - X_MIN) / RES_M).astype(int)
    row = np.floor((Y_MAX - y) / RES_M).astype(int)
    valid = (col >= 0) & (col < n_x) & (row >= 0) & (row < n_y)
    return np.where(valid, row * n_x + col, -1)

# ---------------------------------------------------------------------------
# Load

print('Loading cleaned data …')
df = pd.read_csv(IN_CSV)

# match R script 3 line 27: unique rows on (continent, lon, lat, period_season, species, LYID)
lyid_df = df.groupby(
    ['continent', 'longitude', 'latitude', 'period_season', 'species', 'LYID']
).size().reset_index(name='nobs')
print(f'  unique LYID rows: {len(lyid_df):,}')

n_x = (X_MAX - X_MIN) // RES_M
n_y = (Y_MAX - Y_MIN) // RES_M
n_cells = n_x * n_y
print(f'Grid: {n_x} × {n_y} = {n_cells:,} cells')

# ---------------------------------------------------------------------------
# Assign each LYID-level row to a cell
lyid_df['cell'] = cell_ids(lyid_df['longitude'].values, lyid_df['latitude'].values, n_x, n_y)
lyid_df = lyid_df[lyid_df['cell'] >= 0].copy()

# ---------------------------------------------------------------------------
# Per (period_season, cell) count of distinct LYIDs
# R line 49: rasterize with field=1 and fun="count" → counts of LYID points in cell

print('Computing sampling per season …')

period_seasons = ['0_1', '0_2', '0_3', '3_1', '3_2', '3_3']

samp_seasons = {}
for ps in period_seasons:
    sub = lyid_df[lyid_df['period_season'] == ps]
    count = np.full(n_cells, np.nan, dtype=np.float32)
    if len(sub) > 0:
        cell_counts = sub.groupby('cell').size()
        count[cell_counts.index.values] = cell_counts.values.astype(np.float32)
    samp_seasons[ps] = count

# R lines 55–60: for cells sampled in OTHER seasons but NaN here, set to 0
# beedat_sampallseason: cells with any sampling across all seasons
all_cells_counts = np.full(n_cells, np.nan, dtype=np.float32)
grouped_all = lyid_df.groupby('cell').size()
all_cells_counts[grouped_all.index.values] = grouped_all.values.astype(np.float32)

for ps in period_seasons:
    v = samp_seasons[ps]
    fill_mask = (all_cells_counts > 0) & np.isnan(v)
    v[fill_mask] = 0.0
    samp_seasons[ps] = v
    print(f'  {ps}: mean={np.nanmean(v):.2f}  nonzero={int((v > 0).sum()):,}  zeros={int((v == 0).sum()):,}')

# ---------------------------------------------------------------------------
# Sum across 3 seasons in each period
# R line 65: stackApply with indices=c(1,1,1,2,2,2), fun=sum

samp_baseline = np.nansum(
    np.stack([samp_seasons['0_1'], samp_seasons['0_2'], samp_seasons['0_3']], axis=0),
    axis=0,
)
samp_recent = np.nansum(
    np.stack([samp_seasons['3_1'], samp_seasons['3_2'], samp_seasons['3_3']], axis=0),
    axis=0,
)

# Only keep where at least one season had sampling (the sum of NaNs produces 0 otherwise)
any_bs = ~np.isnan(np.stack([samp_seasons['0_1'], samp_seasons['0_2'], samp_seasons['0_3']])).all(axis=0)
any_rc = ~np.isnan(np.stack([samp_seasons['3_1'], samp_seasons['3_2'], samp_seasons['3_3']])).all(axis=0)
samp_baseline[~any_bs] = np.nan
samp_recent[~any_rc] = np.nan

print(f'\nBaseline sampling: {int(np.isfinite(samp_baseline).sum()):,} cells, total LYIDs {int(np.nansum(samp_baseline)):,}')
print(f'Recent sampling:   {int(np.isfinite(samp_recent).sum()):,} cells, total LYIDs {int(np.nansum(samp_recent)):,}')

# ---------------------------------------------------------------------------
# Continent raster (R lines 76–82)
# rasterize(beedat_pts, quad_cea, field="continent", fun=mean)

print('\nBuilding continent raster …')
continent = np.full(n_cells, np.nan, dtype=np.float32)
# mean of continent per cell
agg = lyid_df.groupby('cell')['continent'].mean()
continent[agg.index.values] = agg.values.astype(np.float32)
print(f'  cells with continent assigned: {int(np.isfinite(continent).sum()):,}')
n_na_cells = int((continent == 1).sum())
n_eu_cells = int((continent == 2).sum())
n_mix = int(((continent > 1) & (continent < 2)).sum())
print(f'  NA (1): {n_na_cells:,}  EUR (2): {n_eu_cells:,}  mixed: {n_mix}')

# ---------------------------------------------------------------------------
# Save

# Total sampling = sum across all 6 period_seasons
# R line 27 (5_binomialGLMM4Presence.R):
#   sampling <- stackApply(read_rds(bombus_seasonsampling.RDS), rep(1, 6), sum)
# which sums all 6 season rasters into one total-sampling raster.
samp_stack = np.stack([samp_seasons[ps] for ps in period_seasons], axis=0)
samp_total = np.nansum(samp_stack, axis=0)
# cells with no sampling anywhere → NaN (R: `sampling[sampling == 0] <- NA`)
samp_total[samp_total == 0] = np.nan
print(f'Total sampling (all 6 seasons): cells with sampling = {int(np.isfinite(samp_total).sum()):,}, total LYIDs = {int(np.nansum(samp_total)):,}')

np.savez_compressed(
    OUT_DIR / 'sampling_continent.npz',
    samp_baseline=samp_baseline,
    samp_recent=samp_recent,
    samp_total=samp_total,            # ← new: sum of all 6 season rasters
    samp_seasons=samp_stack,
    period_seasons=np.array(period_seasons),
    continent=continent,
    n_x=n_x, n_y=n_y,
)
print(f'\nSaved → {OUT_DIR / "sampling_continent.npz"}')
