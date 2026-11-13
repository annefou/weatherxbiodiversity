"""
Sampling effort + continent for the Soroye et al. (2020) extinction-replication
analysis: cleaned occurrence records -> per-cell sampling counts.

Port of soroye_port/03_sampling_continent.py, parameterized: inputs, output
directory, grid and study periods are all passed explicitly (same flags as
step 02, so the two grids cannot drift apart). The replication method stays
in code: sampling = count of distinct records (LYIDs) per cell, cells sampled
in other seasons get explicit 0, and the period totals are sums over the
seasons (R script 3, lines 49-65).

Builds, as <output-dir>/sampling_continent.npz:
  - per-season sampling rasters (distinct records per cell, 1/0/NaN)
  - period-level baseline/recent sampling (sum over seasons)
  - total sampling across all seasons
  - per-cell mean continent code (1=NA, 2=EUR), from the records

Example (published case):
  python 03_sampling_continent.py --records clean_records.csv \
      --grid-resolution-m 100000 \
      --grid-bbox -20037507 20062493 -5263885 6336115 \
      --period-baseline 0 --period-recent 3 --output-dir out
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

# CEA projection of the original R raster (see step 02).
TRANSFORMER = Transformer.from_crs('EPSG:4326', '+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84', always_xy=True)

parser = argparse.ArgumentParser(description="Sampling effort + continent rasters for the replication analysis.")
parser.add_argument("--records", type=Path, required=True,
                    help="Cleaned records CSV from step 01.")
parser.add_argument("--grid-resolution-m", type=int, required=True,
                    help="Grid cell size, in CRS meters (published: 100000).")
region = parser.add_mutually_exclusive_group(required=True)
region.add_argument("--bbox-latlon", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                    help="Grid extent in lat/lon degrees, converted to the projection.")
region.add_argument("--grid-bbox", nargs=4, type=float, metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"),
                    help="Grid extent in projection meters (published raster bounds).")
parser.add_argument("--period-baseline", type=int, required=True)
parser.add_argument("--period-recent", type=int, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()

OUT_NPZ = args.output_dir / "sampling_continent.npz"
OUT_NPZ.parent.mkdir(parents=True, exist_ok=True)

if args.grid_bbox:
    X_MIN, X_MAX, Y_MIN, Y_MAX = args.grid_bbox
else:
    n, w, s, e = args.bbox_latlon
    x_min, _ = TRANSFORMER.transform(w, n)
    x_max, _ = TRANSFORMER.transform(e, s)
    _, y_max = TRANSFORMER.transform(w, n)
    _, y_min = TRANSFORMER.transform(e, s)
    X_MIN, X_MAX, Y_MIN, Y_MAX = float(x_min), float(x_max), float(y_min), float(y_max)
RES_M = args.grid_resolution_m

def cell_ids(lon, lat, n_x, n_y):
    x, y = TRANSFORMER.transform(lon, lat)
    col = np.floor((x - X_MIN) / RES_M).astype(int)
    row = np.floor((Y_MAX - y) / RES_M).astype(int)
    valid = (col >= 0) & (col < n_x) & (row >= 0) & (row < n_y)
    return np.where(valid, row * n_x + col, -1)

# ---------------------------------------------------------------------------
# Load

print('Loading cleaned records …')
df = pd.read_csv(args.records)

# match R script 3 line 27: unique rows on (continent, lon, lat, period_season, species, record id)
lyid_df = df.groupby(
    ['continent', 'longitude', 'latitude', 'period_season', 'species', 'LYID']
).size().reset_index(name='nobs')
print(f'  unique record rows: {len(lyid_df):,}')

n_x = int((X_MAX - X_MIN) // RES_M)
n_y = int((Y_MAX - Y_MIN) // RES_M)
n_cells = n_x * n_y
print(f'Grid: {n_x} × {n_y} = {n_cells:,} cells')

# ---------------------------------------------------------------------------
# Assign each record row to a cell
lyid_df['cell'] = cell_ids(lyid_df['longitude'].values, lyid_df['latitude'].values, n_x, n_y)
lyid_df = lyid_df[lyid_df['cell'] >= 0].copy()

# ---------------------------------------------------------------------------
# Per (period_season, cell) count of distinct records
# R line 49: rasterize with field=1 and fun="count"

print('Computing sampling per season …')

seasons = sorted(df['season'].unique())
period_seasons = [f'{p}_{s}' for p in (args.period_baseline, args.period_recent) for s in seasons]

samp_seasons = {}
for ps in period_seasons:
    sub = lyid_df[lyid_df['period_season'] == ps]
    count = np.full(n_cells, np.nan, dtype=np.float32)
    if len(sub) > 0:
        cell_counts = sub.groupby('cell').size()
        count[cell_counts.index.values] = cell_counts.values.astype(np.float32)
    samp_seasons[ps] = count

# R lines 55-60: for cells sampled in OTHER seasons but NaN here, set to 0
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
# Sum across seasons in each period
# R line 65: stackApply with indices=c(1,1,1,2,2,2), fun=sum

bs = [samp_seasons[f'{args.period_baseline}_{s}'] for s in seasons]
rc = [samp_seasons[f'{args.period_recent}_{s}'] for s in seasons]
samp_baseline = np.nansum(np.stack(bs, axis=0), axis=0)
samp_recent = np.nansum(np.stack(rc, axis=0), axis=0)

# Only keep where at least one season had sampling (the sum of NaNs produces 0 otherwise)
any_bs = ~np.isnan(np.stack(bs, axis=0)).all(axis=0)
any_rc = ~np.isnan(np.stack(rc, axis=0)).all(axis=0)
samp_baseline[~any_bs] = np.nan
samp_recent[~any_rc] = np.nan

print(f'\nBaseline sampling: {int(np.isfinite(samp_baseline).sum()):,} cells, total records {int(np.nansum(samp_baseline)):,}')
print(f'Recent sampling:   {int(np.isfinite(samp_recent).sum()):,} cells, total records {int(np.nansum(samp_recent)):,}')

# ---------------------------------------------------------------------------
# Continent raster (R lines 76-82)
# rasterize(beedat_pts, quad_cea, field="continent", fun=mean)

print('\nBuilding continent raster …')
continent = np.full(n_cells, np.nan, dtype=np.float32)
agg = lyid_df.groupby('cell')['continent'].mean()
continent[agg.index.values] = agg.values.astype(np.float32)
print(f'  cells with continent assigned: {int(np.isfinite(continent).sum()):,}')
n_na_cells = int((continent == 1).sum())
n_eu_cells = int((continent == 2).sum())
n_mix = int(((continent > 1) & (continent < 2)).sum())
print(f'  code 1: {n_na_cells:,}  code 2: {n_eu_cells:,}  mixed: {n_mix}')

# ---------------------------------------------------------------------------
# Save

# Total sampling = sum across all period_seasons
# R (5_binomialGLMM4Presence.R line 27): stackApply(..., rep(1, 6), sum)
samp_stack = np.stack([samp_seasons[ps] for ps in period_seasons], axis=0)
samp_total = np.nansum(samp_stack, axis=0)
# cells with no sampling anywhere → NaN (R: `sampling[sampling == 0] <- NA`)
samp_total[samp_total == 0] = np.nan
print(f'Total sampling (all seasons): cells with sampling = {int(np.isfinite(samp_total).sum()):,}, total records = {int(np.nansum(samp_total)):,}')

np.savez_compressed(
    OUT_NPZ,
    samp_baseline=samp_baseline,
    samp_recent=samp_recent,
    samp_total=samp_total,
    samp_seasons=samp_stack,
    period_seasons=np.array(period_seasons),
    continent=continent,
    n_x=n_x, n_y=n_y,
)
print(f'\nSaved → {OUT_NPZ}')
