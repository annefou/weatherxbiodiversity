"""
Generic cleaning of a GBIF occurrence download: GBIF_Retrieval output ->
a plain occurrence table, for any taxon and any area.

Input: the GBIF_Retrieval occurrence table (DWCA occurrence.txt, or a
SIMPLE_CSV download; both tab-separated) with the columns gbifID,
decimalLatitude, decimalLongitude, year, species, genus, countryCode, stateProvince.

Steps:
  1. keep the needed columns and rename them;
  2. species names: strip each record's genus and lowercase ("Bombus
     terrestris" -> "terrestris");
  3. drop records without coordinates, species or year, and records outside
     --years (START <= year < END), if given;
  4. optional taxonomic curation, each from a data file of the study:
     --drop-species (taxa removed), --synonyms (merged into valid names),
     --species-list (only these species kept).

Output: <output-dir>/occurrences_clean.csv with columns species, latitude,
longitude, year, LYID (= gbifID, one GBIF record = one report), country,
state_prov.

Example (Iberian Bombus, Soroye et al. 2020 replication):
  python clean_occurrences.py --occurrences occurrence.txt \
      --years 1901 2015 --drop-species bombus_drop_species.tsv \
      --synonyms bombus_synonyms.tsv --species-list Kerr_et_al2015_spplist.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

COLUMNS = {   # GBIF column -> output column
    'species':          'species',
    'genus':            'genus',
    'decimalLatitude':  'latitude',
    'decimalLongitude': 'longitude',
    'year':             'year',
    'gbifID':           'LYID',
    'countryCode':      'country',
    'stateProvince':    'state_prov',
}

parser = argparse.ArgumentParser(description="Clean a GBIF occurrence download (any taxon, any area).")
parser.add_argument("--occurrences", type=Path, required=True,
                    help="GBIF DWCA occurrence.txt or SIMPLE_CSV (tab-separated).")
parser.add_argument("--years", nargs=2, type=int, metavar=("START", "END"),
                    help="Keep START <= year < END (default: all years).")
parser.add_argument("--drop-species", type=Path,
                    help="TSV 'species<TAB>reason' (comment lines with #); these taxa are removed.")
parser.add_argument("--synonyms", type=Path,
                    help="TSV 'from<TAB>to<TAB>note' (comment lines with #); merged into valid names.")
parser.add_argument("--species-list", type=Path,
                    help="CSV with a 'species' column; records of other species are dropped.")
parser.add_argument("--output-dir", type=Path, default=Path("results"))
args = parser.parse_args()

OUT = args.output_dir / "occurrences_clean.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load, keep and rename the needed columns

print(f'Loading occurrences from {args.occurrences} …')
raw = pd.read_csv(args.occurrences, sep='\t', low_memory=False)
print(f'  raw: {len(raw):,} rows, {raw.shape[1]} columns')
missing = [c for c in COLUMNS if c not in raw.columns]
if missing:
    raise SystemExit(f"Missing GBIF columns in {args.occurrences}: {missing}")
occ = raw[list(COLUMNS)].rename(columns=COLUMNS)

# ---------------------------------------------------------------------------
# 2. Species names without the record's genus, lowercase

occ['species'] = [
    re.sub(rf'^{re.escape(str(g))}\s+', '', str(s)).lower()
    for s, g in zip(occ['species'], occ['genus'])
]
occ.loc[raw['species'].isna(), 'species'] = pd.NA
occ['year'] = pd.to_numeric(occ['year'], errors='coerce')

# ---------------------------------------------------------------------------
# 3. Coordinates, species, years

drop_species = (
    set(pd.read_csv(args.drop_species, sep='\t', comment='#')['species'].astype(str).str.lower())
    if args.drop_species else set()
)
clean = occ.dropna(subset=['latitude', 'longitude', 'species', 'year'])
if args.years:
    start, end = args.years
    clean = clean[(clean['year'] >= start) & (clean['year'] < end)]
clean = clean[~clean['species'].isin(drop_species)].copy()
print(f'  after coordinates/species/years/drop-species: {len(clean):,} rows')

# ---------------------------------------------------------------------------
# 4. Synonyms, species list

if args.synonyms:
    synonyms = dict(pd.read_csv(args.synonyms, sep='\t', comment='#')[['from', 'to']]
                    .to_records(index=False))
    clean['species'] = clean['species'].replace(synonyms)

if args.species_list:
    keep = set(pd.read_csv(args.species_list)['species'].astype(str).str.lower().unique())
    clean = clean[clean['species'].isin(keep)].copy()
    print(f'  after species list ({len(keep)} species): {len(clean):,} rows')

clean = clean.drop(columns='genus').reset_index(drop=True)
clean.to_csv(OUT, index=False)
print(f'\nSaved → {OUT}  ({len(clean):,} rows, {clean["species"].nunique()} species)')
