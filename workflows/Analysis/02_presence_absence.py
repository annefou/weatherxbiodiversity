"""
Presence/absence matrices for the Soroye et al. (2020) extinction-replication
analysis: cleaned occurrence records -> per-species grid cells.

Port of soroye_port/02_presence_absence.py, parameterized: inputs, output
directory, grid and study periods are all passed explicitly. The replication
method stays in code: the CEA projection of the original raster, the 3
seasons per period, and the "any species seen = sampled cell" rule that
turns presences into presence/absence (R script 2, lines 156-164).

Grid: the original raster is 100 km on Lambert Azimuthal Equal Area
(CEA, EPSG-adjacent proj4 from the R script), bounded in meters. Studies
may give the extent in lat/lon degrees instead; it is converted with the
same projection.

Builds, as <output-dir>/presence_absence.npz:
  - per-season species x cell presence matrices (1/NaN), baseline and recent
  - period-level richness (sum of species presences per cell)
  - presence/absence: cells where any species was ever seen get explicit 0
    for species not observed there
  - period-level presence/absence (max across the 3 seasons)

Example (published case):
  python 02_presence_absence.py --records clean_records.csv \
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

# CEA projection of the original R raster:
# proj_cea_wsg = "+proj=cea +lon_0=0 +lat_ts=0 +x_0=0 +y_0=0 +datum=WGS84
#                 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0"
TRANSFORMER = Transformer.from_crs('EPSG:4326', '+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84', always_xy=True)

parser = argparse.ArgumentParser(description="Presence/absence matrices on a grid for the replication analysis.")
parser.add_argument("--records", type=Path, required=True,
                    help="Cleaned records CSV from step 01 (species, latitude, longitude, period, season, period_season).")
parser.add_argument("--grid-resolution-m", type=int, required=True,
                    help="Grid cell size, in CRS meters (published: 100000).")
region = parser.add_mutually_exclusive_group(required=True)
region.add_argument("--bbox-latlon", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                    help="Grid extent in lat/lon degrees, converted to the projection.")
region.add_argument("--grid-bbox", nargs=4, type=float, metavar=("X_MIN", "X_MAX", "Y_MIN", "Y_MAX"),
                    help="Grid extent in projection meters (published raster bounds).")
parser.add_argument("--period-baseline", type=int, required=True,
                    help="Period label of the baseline (published: 0 = 1901-1974).")
parser.add_argument("--period-recent", type=int, required=True,
                    help="Period label of the recent window (published: 3 = 2000-2014).")
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()

OUT_NPZ = args.output_dir / "presence_absence.npz"
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

# ---------------------------------------------------------------------------
# Build CEA grid

def build_cea_grid():
    n_x = int((X_MAX - X_MIN) // RES_M)         # columns
    n_y = int((Y_MAX - Y_MIN) // RES_M)         # rows
    # Top-left corner origin (raster convention)
    x_edges = np.linspace(X_MIN, X_MIN + n_x * RES_M, n_x + 1)
    y_edges = np.linspace(Y_MAX, Y_MAX - n_y * RES_M, n_y + 1)  # descending
    return n_x, n_y, x_edges, y_edges

def cell_ids(lon: np.ndarray, lat: np.ndarray, n_x: int, n_y: int) -> np.ndarray:
    """Return flat cell index (row*n_x + col) or -1 if outside bounds."""
    x, y = TRANSFORMER.transform(lon, lat)
    col = np.floor((x - X_MIN) / RES_M).astype(int)
    row = np.floor((Y_MAX - y) / RES_M).astype(int)   # y decreases downward
    valid = (col >= 0) & (col < n_x) & (row >= 0) & (row < n_y)
    return np.where(valid, row * n_x + col, -1)

# ---------------------------------------------------------------------------
# Main

print('Loading cleaned records …')
df = pd.read_csv(args.records)
print(f'  {len(df):,} rows, {df["species"].nunique()} species')

n_x, n_y, x_edges, y_edges = build_cea_grid()
n_cells = n_x * n_y
print(f'CEA grid: {n_x} × {n_y} = {n_cells:,} cells')

print('Projecting points → cell IDs …')
df['cell'] = cell_ids(df['longitude'].values, df['latitude'].values, n_x, n_y)
df = df[df['cell'] >= 0].copy()
print(f'  {len(df):,} rows mapped to grid')

species_list = sorted(df['species'].unique())
seasons = sorted(df['season'].unique())
period_seasons = [f'{p}_{s}' for p in (args.period_baseline, args.period_recent) for s in seasons]

# ---------------------------------------------------------------------------
# Per-season presence matrix  [species × cell] 1/NaN
# Shape: len(species) × n_cells — stored as a dict per period_season

print('\nBuilding presence matrices per (species × period_season) …')

# Pre-compute (cell, species, period_season) presence using groupby
presence_key = df.groupby(['period_season', 'species', 'cell']).size().reset_index(name='n_obs')

# pre = dict[period_season] → 2D array [species_idx × cell_idx] with 1 or NaN
pre = {}
for ps in period_seasons:
    sub = presence_key[presence_key['period_season'] == ps]
    mat = np.full((len(species_list), n_cells), np.nan, dtype=np.float32)
    for _, row in sub.iterrows():
        spp_idx = species_list.index(row['species'])
        mat[spp_idx, int(row['cell'])] = 1.0
    pre[ps] = mat
    print(f'  {ps}: {(mat == 1).sum():,} species×cell presences')

# ---------------------------------------------------------------------------
# Species richness per period
# R line 141: per-period stack using min across 3 seasons
# (min of 1/NaN = 1 if ever present, NaN if never)
# Then sum across species = richness

print('\nComputing species richness per period …')

def per_period_min(season_arrays):
    """min across seasons with na.rm=True: present if ever present."""
    stacked = np.stack(season_arrays, axis=0)  # shape (n_seasons, spp, cells)
    with np.errstate(invalid='ignore'):
        # na.rm=T means: if any is 1, return 1; if all NaN, return NaN
        any_pres = np.nanmin(stacked, axis=0)
    return any_pres  # (spp, cells), 1 or NaN

bs_seasons = [pre[f'{args.period_baseline}_{s}'] for s in seasons]
rc_seasons = [pre[f'{args.period_recent}_{s}'] for s in seasons]
pr_baseline = per_period_min(bs_seasons)
pr_recent   = per_period_min(rc_seasons)

# species richness per period (sum of species presence counts per cell)
sprich_baseline = np.nansum(pr_baseline, axis=0)  # 1D cells
sprich_recent   = np.nansum(pr_recent, axis=0)
sprich_baseline[sprich_baseline == 0] = np.nan
sprich_recent[sprich_recent == 0] = np.nan

print(f'  cells with any presence baseline: {np.isfinite(sprich_baseline).sum():,}')
print(f'  cells with any presence recent:   {np.isfinite(sprich_recent).sum():,}')

# ---------------------------------------------------------------------------
# Presence/absence (prab) — R lines 156–164
# "zero for species where at least 1 other species was seen"
# i.e. cell sampled for the genus → species not observed → 0 (not NaN)

print('\nBuilding presence/absence (threshold = any species seen) …')

# total richness summed across all periods/seasons of presence counts per cell
total_rich_cells = np.zeros(n_cells, dtype=float)
for ps in period_seasons:
    total_rich_cells += np.nansum(pre[ps], axis=0)
sampled_anywhere = total_rich_cells > 0   # boolean per cell

prab = {}
for ps in period_seasons:
    p = pre[ps].copy()
    # For cells sampled anywhere: fill NaN with 0
    # Broadcast: p shape (spp, cells); sampled_anywhere shape (cells,)
    mask = sampled_anywhere[np.newaxis, :] & np.isnan(p)
    p[mask] = 0.0
    prab[ps] = p
    print(f'  {ps}: {int((p == 0).sum()):,} inferred absences; {int((p == 1).sum()):,} presences')

# Per-period prab: max across seasons (presence in ANY season = present)
def per_period_max(prab_season_list):
    stacked = np.stack(prab_season_list, axis=0)  # (n_seasons, spp, cells)
    with np.errstate(invalid='ignore'):
        m = np.nanmax(stacked, axis=0)            # 1 if any present, 0 if all absent, NaN if all NaN
    return m

prab_baseline = per_period_max([prab[f'{args.period_baseline}_{s}'] for s in seasons])
prab_recent   = per_period_max([prab[f'{args.period_recent}_{s}'] for s in seasons])

# ---------------------------------------------------------------------------
# Save everything as an .npz

np.savez_compressed(
    OUT_NPZ,
    species=np.array(species_list),
    period_seasons=np.array(period_seasons),
    pre_baseline_seasons=np.stack(bs_seasons),
    pre_recent_seasons=np.stack(rc_seasons),
    prab_baseline_seasons=np.stack([prab[f'{args.period_baseline}_{s}'] for s in seasons]),
    prab_recent_seasons=np.stack([prab[f'{args.period_recent}_{s}'] for s in seasons]),
    prab_baseline=prab_baseline,
    prab_recent=prab_recent,
    sprich_baseline=sprich_baseline,
    sprich_recent=sprich_recent,
    n_x=n_x, n_y=n_y,
    x_edges=x_edges, y_edges=y_edges,
)
print(f'\nSaved presence/absence arrays → {OUT_NPZ}')

# Quick summary table — cells occupied per species per period
print('\nPer-species cell counts (sample of 10 species):')
for i, spp in enumerate(species_list[:10]):
    n_bs = int((prab_baseline[i] == 1).sum())
    n_rc = int((prab_recent[i] == 1).sum())
    print(f'  {spp:<30} baseline={n_bs:4d}  recent={n_rc:4d}')
print(f'  ... ({len(species_list)} species total)')
