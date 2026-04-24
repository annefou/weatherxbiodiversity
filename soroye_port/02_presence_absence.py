"""
Python port of Soroye et al. (2020) — script 2.

Source: 2_CalcSpeciesPr_Rich.R

Builds:
  - 100km CEA grid spanning NA + EUR
  - Per-species presence raster for each (period, season) — value = 1 where
    occurrences exist, NaN elsewhere
  - Species richness per period (sum across species of per-season max)
  - Presence/absence (prab): cells with ANY species observed anywhere get
    explicit 0 for species without observations in that cell
  - Period-level prab (max across the 3 seasons) per species
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

# ---------------------------------------------------------------------------
# Config

ROOT = Path(__file__).resolve().parent.parent
SOROYE_PORT = ROOT / 'soroye_port'
import os as _os
OUT_DIR = SOROYE_PORT / _os.environ.get('OUT_SUBDIR', 'outputs')
IN_CSV = OUT_DIR / 'bombus_clean.csv'

# CEA grid bounds (from script 2 line 41)
RES_M = 100_000       # 100 km cell size
X_MIN, X_MAX = -20_037_507, 20_062_493
Y_MIN, Y_MAX = -5_263_885, 6_336_115

# ---------------------------------------------------------------------------
# Build 100km CEA grid

def build_cea_grid():
    n_x = (X_MAX - X_MIN) // RES_M          # columns
    n_y = (Y_MAX - Y_MIN) // RES_M          # rows
    # Top-left corner origin (raster convention)
    x_edges = np.linspace(X_MIN, X_MIN + n_x * RES_M, n_x + 1)
    y_edges = np.linspace(Y_MAX, Y_MAX - n_y * RES_M, n_y + 1)  # descending
    return n_x, n_y, x_edges, y_edges

# ---------------------------------------------------------------------------
# WGS84 lonlat → CEA meters (proj4 string from the R script line 17)

# proj_cea_wsg = "+proj=cea +lon_0=0 +lat_ts=0 +x_0=0 +y_0=0 +datum=WGS84
#                 +units=m +no_defs +ellps=WGS84 +towgs84=0,0,0"
transformer = Transformer.from_crs('EPSG:4326', '+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84', always_xy=True)

def cell_ids(lon: np.ndarray, lat: np.ndarray, n_x: int, n_y: int) -> np.ndarray:
    """Return flat cell index (row*n_x + col) or -1 if outside bounds."""
    x, y = transformer.transform(lon, lat)
    col = np.floor((x - X_MIN) / RES_M).astype(int)
    row = np.floor((Y_MAX - y) / RES_M).astype(int)   # y decreases downward
    valid = (col >= 0) & (col < n_x) & (row >= 0) & (row < n_y)
    return np.where(valid, row * n_x + col, -1)

# ---------------------------------------------------------------------------
# Main

print('Loading cleaned bombus data …')
df = pd.read_csv(IN_CSV)
print(f'  {len(df):,} rows, {df["species"].nunique()} species')

n_x, n_y, x_edges, y_edges = build_cea_grid()
n_cells = n_x * n_y
print(f'CEA grid: {n_x} × {n_y} = {n_cells:,} cells')

print('Projecting points → cell IDs …')
df['cell'] = cell_ids(df['longitude'].values, df['latitude'].values, n_x, n_y)
df = df[df['cell'] >= 0].copy()
print(f'  {len(df):,} rows mapped to grid')

species_list = sorted(df['species'].unique())
period_seasons = ['0_1', '0_2', '0_3', '3_1', '3_2', '3_3']

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
# R line 141: beedat_pr_period = per-period stack using min across 3 seasons
# (min of 1/NaN = 1 if ever present, NaN if never)
# Then sum across species = richness

print('\nComputing species richness per period …')

def per_period_min(season_arrays):
    """min across seasons with na.rm=True: present if ever present."""
    stacked = np.stack(season_arrays, axis=0)  # shape (3, spp, cells)
    with np.errstate(invalid='ignore'):
        # na.rm=T means: if any is 1, return 1; if all NaN, return NaN
        # Actually min(1, NaN, na.rm=T) = 1, so it reduces to "any"
        any_pres = np.nanmin(stacked, axis=0)
    return any_pres  # (spp, cells), 1 or NaN

beedat_pr_baseline = per_period_min([pre['0_1'], pre['0_2'], pre['0_3']])
beedat_pr_recent   = per_period_min([pre['3_1'], pre['3_2'], pre['3_3']])

# species richness per period (sum of species presence counts per cell)
sprich_baseline = np.nansum(beedat_pr_baseline, axis=0)  # 1D cells
sprich_recent   = np.nansum(beedat_pr_recent, axis=0)
sprich_baseline[sprich_baseline == 0] = np.nan
sprich_recent[sprich_recent == 0] = np.nan

print(f'  cells with any presence baseline: {np.isfinite(sprich_baseline).sum():,}')
print(f'  cells with any presence recent:   {np.isfinite(sprich_recent).sum():,}')

# ---------------------------------------------------------------------------
# Presence/absence (prab) — R lines 156–164
# "zero for species where at least 1 other species was seen"
# i.e. cell sampled for bumblebees → species not observed → 0 (not NaN)

print('\nBuilding presence/absence (threshold = any species seen) …')

# total sprich = sum across all periods/seasons of presence counts per cell
total_sprich_cells = np.zeros(n_cells, dtype=float)
for ps in period_seasons:
    total_sprich_cells += np.nansum(pre[ps], axis=0)
sampled_anywhere = total_sprich_cells > 0   # boolean per cell

prab = {}
for ps in period_seasons:
    p = pre[ps].copy()
    # For cells sampled anywhere: fill NaN with 0
    # Broadcast: p shape (spp, cells); sampled_anywhere shape (cells,)
    mask = sampled_anywhere[np.newaxis, :] & np.isnan(p)
    p[mask] = 0.0
    prab[ps] = p
    print(f'  {ps}: {int((p == 0).sum()):,} inferred absences; {int((p == 1).sum()):,} presences')

# Per-period prab: max across 3 seasons (presence in ANY season = present)
def per_period_max(prab_season_list):
    stacked = np.stack(prab_season_list, axis=0)  # (3, spp, cells)
    with np.errstate(invalid='ignore'):
        m = np.nanmax(stacked, axis=0)            # 1 if any present, 0 if all absent, NaN if all NaN
    return m

prab_baseline = per_period_max([prab['0_1'], prab['0_2'], prab['0_3']])
prab_recent   = per_period_max([prab['3_1'], prab['3_2'], prab['3_3']])

# ---------------------------------------------------------------------------
# Save everything as an .npz

np.savez_compressed(
    OUT_DIR / 'presence_absence.npz',
    species=np.array(species_list),
    period_seasons=np.array(period_seasons),
    pre_baseline_seasons=np.stack([pre['0_1'], pre['0_2'], pre['0_3']]),
    pre_recent_seasons=np.stack([pre['3_1'], pre['3_2'], pre['3_3']]),
    prab_baseline_seasons=np.stack([prab['0_1'], prab['0_2'], prab['0_3']]),
    prab_recent_seasons=np.stack([prab['3_1'], prab['3_2'], prab['3_3']]),
    prab_baseline=prab_baseline,
    prab_recent=prab_recent,
    sprich_baseline=sprich_baseline,
    sprich_recent=sprich_recent,
    n_x=n_x, n_y=n_y,
    x_edges=x_edges, y_edges=y_edges,
)
print(f'\nSaved presence/absence arrays → {OUT_DIR / "presence_absence.npz"}')

# Quick summary table — cells occupied per species per period
print('\nPer-species cell counts (sample of 10 species):')
for i, spp in enumerate(species_list[:10]):
    n_bs = int((prab_baseline[i] == 1).sum())
    n_rc = int((prab_recent[i] == 1).sum())
    print(f'  {spp:<30} baseline={n_bs:4d}  recent={n_rc:4d}')
print(f'  ... ({len(species_list)} species total)')
