"""
Phase 3 / Iberia adaptation of 01_clean_data.py

Differences from the Phase-2 script:
  - Input = GBIF download SIMPLE_CSV (tab-separated despite the .csv extension)
    obtained via the GBIF Occurrence Download API and pinned to a citable DOI.
    DOI: https://doi.org/10.15468/dl.3frmsq
    Citation: GBIF.org (2026-04-25) GBIF Occurrence Download
              https://doi.org/10.15468/dl.3frmsq
  - Species column has "Bombus X" prefix — strip it
  - Period is extended: we use the baseline and recent windows that align with
    Soroye (1901-1974 / 2000-2014), but GBIF Iberia's baseline coverage is thin
    before ~1920. We keep the identical period definition for consistency.
  - Continent is constant = 2 (Europe)
  - LYID comes from gbifID (each GBIF record = one independent report)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'reference' / 'Bumblebee_repo_wbombusdat'
GBIF_CSV = ROOT / 'data' / 'gbif_dl' / '0006204-260423192947929.csv'
KERR_SPP_CSV = REF / '0_data' / 'Kerr_et_al2015_spplist.csv'
ERR_OBS_CSV = REF / '0_data' / 'bombus_err_obs.csv'

OUT_DIR = ROOT / 'soroye_port' / 'outputs_iberia'
OUT_DIR.mkdir(exist_ok=True)
OUT_CLEAN = OUT_DIR / 'bombus_clean.csv'

# ---------------------------------------------------------------------------
# 1. Load raw GBIF

print('Loading GBIF Iberia data …')
gbif = pd.read_csv(GBIF_CSV, sep='\t', low_memory=False)
print(f'  raw: {len(gbif):,} rows')

# Rename columns to match Soroye's schema
gbif = gbif.rename(columns={
    'decimalLatitude':  'latitude',
    'decimalLongitude': 'longitude',
    'year':             'year_',
    'gbifID':           'LYID',
    'stateProvince':    'state_prov',
    'countryCode':      'country',
})
# Strip "Bombus " prefix and lowercase
gbif['species'] = (
    gbif['species']
    .astype(str)
    .str.replace(r'^Bombus\s+', '', regex=True)
    .str.lower()
)
# Force numeric year
gbif['year_'] = pd.to_numeric(gbif['year_'], errors='coerce')

# ---------------------------------------------------------------------------
# 2. Clean (mirror of script 01)

drop_species = {
    'x.virginica', 'megachile_sculpturalis', 'fernaldaepsithyrus',
    'subterraneobombus', 'psithyrus', 'laesobombus', 'allopsithyrus',
}

bombus_clean = (
    gbif
    .dropna(subset=['latitude', 'longitude', 'species'])
    .query('year_ >= 1901 and year_ < 2015')
    .loc[lambda d: ~d['species'].isin(drop_species)]
    .copy()
)
print(f'  after basic cleaning: {len(bombus_clean):,} rows')

# ---------------------------------------------------------------------------
# 3. Continent (ALL = Europe) + period

bombus_clean['continent'] = 2   # Iberia is in Europe

def assign_period(year: float) -> float:
    if 1901 <= year < 1975: return 0
    if 1975 <= year < 1987: return 1
    if 1987 <= year < 2000: return 2
    if 2000 <= year < 2015: return 3
    return np.nan

bombus_clean['timeperiod'] = bombus_clean['year_'].apply(assign_period)

# ---------------------------------------------------------------------------
# 4. Species synonyms (same table as Soroye)

synonyms = {
    'ashtoni': 'bohemicus',
    'californicus': 'fervidus',
    'moderatus': 'cryptarum',
    'sonorus': 'pensylvanicus',
    'alboanalis': 'jonellus',
    'wilmattae': 'ephippiatus',
    'volucelloides': 'melaleucus',
    'soroensis': 'soroeensis',
    'sichelii': 'sicheli',
    'wurfleni': 'wurflenii',
    'bannitus': 'muscorum',
    'mocsaryi': 'laesus',
}
bombus_clean['species'] = bombus_clean['species'].replace(synonyms)

# ---------------------------------------------------------------------------
# 5. Filter to Kerr 2015 species list

kerr = pd.read_csv(KERR_SPP_CSV)
kerr_species = set(kerr['species'].astype(str).str.lower().unique())
print(f'  Kerr species total: {len(kerr_species)}')

bombus_clean = bombus_clean[bombus_clean['species'].isin(kerr_species)].copy()
print(f'  after Kerr filter: {len(bombus_clean):,} rows  ({bombus_clean["species"].nunique()} species)')

# ---------------------------------------------------------------------------
# 6. Remove erroneous obs (apply the same table)

err_obs = pd.read_csv(ERR_OBS_CSV, na_values=[''])

kept_parts = []
for _, row in err_obs.iterrows():
    species = row['species']
    excl_cont = row['exclude_from_cont']
    excl_state_raw = row['exclude_from_state']
    excl_states = (
        [s.strip() for s in str(excl_state_raw).split(',')]
        if pd.notna(excl_state_raw) else []
    )

    subset = bombus_clean[bombus_clean['species'] == species].copy()
    if pd.notna(excl_cont):
        subset = subset[subset['continent'] != excl_cont]
    if excl_states:
        keep = subset['state_prov'].isna() | ~subset['state_prov'].isin(excl_states)
        subset = subset[keep]
    kept_parts.append(subset)

species_in_err = set(err_obs['species'].astype(str).str.lower().unique())
kept_parts.append(bombus_clean[~bombus_clean['species'].isin(species_in_err)])

bombus_clean = pd.concat(kept_parts, ignore_index=True)
print(f'  after err-obs removal: {len(bombus_clean):,} rows')

# ---------------------------------------------------------------------------
# 7. Rename + add season + drop middle periods

bombus_clean = bombus_clean.rename(columns={'year_': 'year', 'timeperiod': 'period'})
bombus_clean = bombus_clean[bombus_clean['period'].isin([0, 3])].copy()

def assign_season(year: float) -> float:
    if 1901 <= year <= 1924: return 1
    if 1925 <= year <= 1949: return 2
    if 1950 <= year <= 1974: return 3
    if 2000 <= year <= 2004: return 1
    if 2005 <= year <= 2009: return 2
    if 2010 <= year <= 2014: return 3
    return np.nan

bombus_clean['season'] = bombus_clean['year'].apply(assign_season)
bombus_clean['period_season'] = (
    bombus_clean['period'].astype(int).astype(str)
    + '_' + bombus_clean['season'].astype(int).astype(str)
)

cols = ['species', 'latitude', 'longitude', 'year', 'LYID',
        'continent', 'period', 'season', 'period_season']
bombus_clean = bombus_clean[cols].reset_index(drop=True)

bombus_clean.to_csv(OUT_CLEAN, index=False)
print(f'\nSaved → {OUT_CLEAN}  ({len(bombus_clean):,} rows)')

print('\nPer-period/season summary:')
print(bombus_clean.groupby('period_season').agg(
    nspp=('species', 'nunique'),
    nLYID=('LYID', 'nunique'),
    n_records=('species', 'size'),
).to_string())
print(f'\nSpecies: {bombus_clean["species"].nunique()}')
