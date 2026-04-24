"""
Python port of Soroye et al. (2020) — script 1.

Source: 1_Cleandata_and_makeMCPs.R (lines 1–165)
        In particular, lines 27–104 handle the cleaning.
        The MCP-shapefile part (lines 105+) is only used for CPI/TEI
        computation inputs elsewhere — not needed for the core regression.

Outputs: bombus_clean.csv (cleaned observations with continent, period, season columns)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'reference' / 'Bumblebee_repo_wbombusdat'
BOMBUS_CSV = REF / '0_data' / 'bombus_ogdata.csv'
KERR_SPP_CSV = REF / '0_data' / 'Kerr_et_al2015_spplist.csv'
ERR_OBS_CSV = REF / '0_data' / 'bombus_err_obs.csv'

OUT_DIR = ROOT / 'soroye_port' / 'outputs'
OUT_DIR.mkdir(exist_ok=True)
OUT_CLEAN = OUT_DIR / 'bombus_clean.csv'

# ---------------------------------------------------------------------------
# 1. Load raw data (R line 32: readRDS(bombus_ogdata.RDS))

print('Loading raw bombus data …')
bombus_full = pd.read_csv(
    BOMBUS_CSV,
    index_col=0,
    low_memory=False,  # mixed dtypes in 'state_prov'
)
print(f'  raw: {len(bombus_full):,} rows')

# ---------------------------------------------------------------------------
# 2. Clean: remove incomplete obs and non-bombus (R lines 35–49)

drop_species = {
    'x.virginica',
    'megachile_sculpturalis',
    'fernaldaepsithyrus',
    'subterraneobombus',
    'psithyrus',
    'laesobombus',
    'allopsithyrus',
}

# Force year_ numeric — raw file has strings like '9999.0' for NA
bombus_full['year_'] = pd.to_numeric(bombus_full['year_'], errors='coerce')

bombus_clean = (
    bombus_full
    .assign(species=lambda d: d['species'].astype(str).str.lower())
    .dropna(subset=['latitude', 'longitude', 'species', 'CountryISO'])
    .query('year_ >= 1901 and year_ < 2015')
    .loc[lambda d: ~d['species'].isin(drop_species)]
    .copy()
)
print(f'  after basic cleaning: {len(bombus_clean):,} rows')

# ---------------------------------------------------------------------------
# 3. Continent + period (R lines 51–57)

# observations are already clipped to NA and EUR in source data
bombus_clean['continent'] = np.where(bombus_clean['longitude'] < -25, 1, 2)  # 1=NA, 2=EUR

def assign_period(year: float) -> float:
    if 1901 <= year < 1975:
        return 0
    if 1975 <= year < 1987:
        return 1
    if 1987 <= year < 2000:
        return 2
    if 2000 <= year < 2015:
        return 3
    return np.nan

bombus_clean['timeperiod'] = bombus_clean['year_'].apply(assign_period)

# ---------------------------------------------------------------------------
# 4. Merge species synonyms to IUCN-valid classifications (R lines 60–72)

synonyms = {
    'ashtoni': 'bohemicus',
    'californicus': 'fervidus',
    'moderatus': 'cryptarum',
    'sonorus': 'pensylvanicus',
    'alboanalis': 'jonellus',
    'wilmattae': 'ephippiatus',
    'volucelloides': 'melaleucus',
    'soroensis': 'soroeensis',   # typo
    'sichelii': 'sicheli',       # typo
    'wurfleni': 'wurflenii',     # typo
    'bannitus': 'muscorum',
    'mocsaryi': 'laesus',
}
bombus_clean['species'] = bombus_clean['species'].replace(synonyms)

# ---------------------------------------------------------------------------
# 5. Filter to Kerr 2015 species list (R lines 75–76)

kerr = pd.read_csv(KERR_SPP_CSV)
kerr_species = set(kerr['species'].astype(str).str.lower().unique())
print(f'  Kerr 2015 species count: {len(kerr_species)}')

bombus_clean = bombus_clean[bombus_clean['species'].isin(kerr_species)].copy()
print(f'  after Kerr species filter: {len(bombus_clean):,} rows')

# ---------------------------------------------------------------------------
# 6. Remove erroneous observations per bombus_err_obs.csv (R lines 80–92)

err_obs = pd.read_csv(ERR_OBS_CSV, na_values=[''])

kept_parts = []
for _, row in err_obs.iterrows():
    species = row['species']
    excl_cont = row['exclude_from_cont']          # numeric or NA
    excl_state_raw = row['exclude_from_state']     # "Texas, Oklahoma" or NA
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

# Species NOT in err_obs_table are kept verbatim
species_in_err = set(err_obs['species'].astype(str).str.lower().unique())
kept_parts.append(bombus_clean[~bombus_clean['species'].isin(species_in_err)])

bombus_clean = pd.concat(kept_parts, ignore_index=True)
print(f'  after err-obs removal: {len(bombus_clean):,} rows')

# ---------------------------------------------------------------------------
# 7. Rename columns + add season + drop middle periods (R lines 115–126)

bombus_clean = bombus_clean.rename(columns={'year_': 'year', 'timeperiod': 'period'})

# only keep baseline (period=0) and recent (period=3); drop middle
bombus_clean = bombus_clean[bombus_clean['period'].isin([0, 3])].copy()

def assign_season(year: float) -> float:
    # baseline sub-periods
    if 1901 <= year <= 1924: return 1
    if 1925 <= year <= 1949: return 2
    if 1950 <= year <= 1974: return 3
    # recent sub-periods
    if 2000 <= year <= 2004: return 1
    if 2005 <= year <= 2009: return 2
    if 2010 <= year <= 2014: return 3
    return np.nan

bombus_clean['season'] = bombus_clean['year'].apply(assign_season)
bombus_clean['period_season'] = (
    bombus_clean['period'].astype(int).astype(str)
    + '_' + bombus_clean['season'].astype(int).astype(str)
)

# Keep only the cols needed downstream
cols = ['species', 'latitude', 'longitude', 'year', 'LYID',
        'continent', 'period', 'season', 'period_season']
bombus_clean = bombus_clean[cols].reset_index(drop=True)

# ---------------------------------------------------------------------------
# 8. Save

bombus_clean.to_csv(OUT_CLEAN, index=False)
print(f'\nSaved: {OUT_CLEAN}  ({len(bombus_clean):,} rows)')

# Summary for sanity
print('\nPer period/season:')
print(bombus_clean.groupby('period_season').agg(
    nspp=('species', 'nunique'),
    nLYID=('LYID', 'nunique'),
    n_records=('species', 'size'),
).to_string())

print(f'\nTotal unique species: {bombus_clean["species"].nunique()}')
print(f'Continents: {sorted(bombus_clean["continent"].unique())}')
