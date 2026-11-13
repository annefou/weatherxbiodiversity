"""
Study records for the Soroye et al. (2020) extinction-replication analysis:
cleaned GBIF occurrences (GBIF_Preprocessing) -> presence records with the
study's continent, period and season definitions.

  1. continent code assigned to all records (Soroye: 2 = Europe);
  2. erroneous observations removed (Soroye's table: per species, records on
     a continent and/or in given states/provinces);
  3. periods (0: 1901-1974, 1: 1975-1986, 2: 1987-1999, 3: 2000-2014); only
     the baseline (0) and recent (3) periods are kept;
  4. seasons: 25-year blocks in the baseline, 5-year blocks in the recent
     period.

Input: occurrences_clean.csv from GBIF_Preprocessing (species, latitude,
longitude, year, LYID, country, state_prov).

Output: <output-dir>/clean_records.csv with columns species, latitude,
longitude, year, LYID, continent, period, season, period_season.

Example (published Iberian Bombus case):
  python 01_study_records.py --occurrences occurrences_clean.csv \
      --err-obs bombus_err_obs.csv --continent 2 --output-dir out
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(description="Continent, erroneous observations, periods and seasons (Soroye et al. 2020).")
parser.add_argument("--occurrences", type=Path, required=True,
                    help="occurrences_clean.csv from GBIF_Preprocessing.")
parser.add_argument("--err-obs", type=Path, required=True,
                    help="CSV of erroneous observations (species, exclude_from_cont, exclude_from_state).")
parser.add_argument("--continent", type=int, required=True,
                    help="Continent code assigned to all records (Soroye: 2 = Europe); used by the err-obs exclusions.")
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()

OUT_CLEAN = args.output_dir / "clean_records.csv"
OUT_CLEAN.parent.mkdir(parents=True, exist_ok=True)

clean = pd.read_csv(args.occurrences)
print(f'Loaded {len(clean):,} cleaned occurrences from {args.occurrences}')

# ---------------------------------------------------------------------------
# 1. Continent + period

clean['continent'] = args.continent

def assign_period(year: float) -> float:
    if 1901 <= year < 1975: return 0
    if 1975 <= year < 1987: return 1
    if 1987 <= year < 2000: return 2
    if 2000 <= year < 2015: return 3
    return np.nan

clean['period'] = clean['year'].apply(assign_period)

# ---------------------------------------------------------------------------
# 2. Remove erroneous obs

err_obs = pd.read_csv(args.err_obs, na_values=[''])

kept_parts = []
for _, row in err_obs.iterrows():
    species = row['species']
    excl_cont = row['exclude_from_cont']
    excl_state_raw = row['exclude_from_state']
    excl_states = (
        [s.strip() for s in str(excl_state_raw).split(',')]
        if pd.notna(excl_state_raw) else []
    )

    subset = clean[clean['species'] == species].copy()
    if pd.notna(excl_cont):
        subset = subset[subset['continent'] != excl_cont]
    if excl_states:
        keep = subset['state_prov'].isna() | ~subset['state_prov'].isin(excl_states)
        subset = subset[keep]
    kept_parts.append(subset)

species_in_err = set(err_obs['species'].astype(str).str.lower().unique())
kept_parts.append(clean[~clean['species'].isin(species_in_err)])

clean = pd.concat(kept_parts, ignore_index=True)
print(f'  after err-obs removal: {len(clean):,} rows')

# ---------------------------------------------------------------------------
# 3. Keep baseline and recent periods, add seasons

clean = clean[clean['period'].isin([0, 3])].copy()

def assign_season(year: float) -> float:
    if 1901 <= year <= 1924: return 1
    if 1925 <= year <= 1949: return 2
    if 1950 <= year <= 1974: return 3
    if 2000 <= year <= 2004: return 1
    if 2005 <= year <= 2009: return 2
    if 2010 <= year <= 2014: return 3
    return np.nan

clean['season'] = clean['year'].apply(assign_season)
clean['period_season'] = (
    clean['period'].astype(int).astype(str)
    + '_' + clean['season'].astype(int).astype(str)
)

cols = ['species', 'latitude', 'longitude', 'year', 'LYID',
        'continent', 'period', 'season', 'period_season']
clean = clean[cols].reset_index(drop=True)

clean.to_csv(OUT_CLEAN, index=False)
print(f'\nSaved → {OUT_CLEAN}  ({len(clean):,} rows)')

print('\nPer-period/season summary:')
print(clean.groupby('period_season').agg(
    nspp=('species', 'nunique'),
    nLYID=('LYID', 'nunique'),
    n_records=('species', 'size'),
).to_string())
print(f'\nSpecies: {clean["species"].nunique()}')
