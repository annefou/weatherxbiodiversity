# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Step 1: Download Bombus Occurrence Records from GBIF
#
# This notebook downloads wild bumblebee (*Bombus*) occurrence records
# from the [Global Biodiversity Information Facility (GBIF)](https://www.gbif.org/)
# for the Iberian Peninsula (Spain and Portugal).
#
# ## Context
#
# We are replicating the European subset of
# [Soroye, Newbold & Kerr (2020)](https://doi.org/10.1126/science.aax8591),
# who showed that increasing frequency of temperatures exceeding historical
# baselines predicts local extinction of *Bombus* species. The original study
# compiled occurrence data from multiple European datasets; here we test
# whether the same analysis can be reproduced using open GBIF data alone.
#
# ## Data specification
#
# | Parameter | Value |
# |-----------|-------|
# | Taxon | Genus *Bombus* (GBIF key: 1340278) |
# | Region | Spain (ES) + Portugal (PT) |
# | Coordinates | Georeferenced records only |
# | Quality | No geospatial issues |
# | Format | Darwin Core fields via GBIF REST API |
#
# **Note**: For a citable dataset, use the GBIF download API to obtain a DOI.
# This notebook uses the search API for development/preview purposes.

# %%
import requests
import pandas as pd
import json
import os
import time
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# %% [markdown]
# ## Configuration

# %%
OUTDIR = Path("../data")
OUTDIR.mkdir(exist_ok=True)

GBIF_API = "https://api.gbif.org/v1"
GENUS_KEY = 1340278  # Bombus
COUNTRIES = ["ES", "PT"]

# Robust HTTP session with retries
session = requests.Session()
retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

# %% [markdown]
# ## 1. Check data availability

# %%
print("Bombus occurrence records in GBIF (with coordinates):\n")
total_available = 0
for country in COUNTRIES:
    resp = session.get(f"{GBIF_API}/occurrence/search", params={
        "genusKey": GENUS_KEY, "country": country,
        "hasCoordinate": "true", "limit": 1,
    })
    count = resp.json()["count"]
    total_available += count
    print(f"  {country}: {count:,}")
print(f"\n  Total: {total_available:,}")

# %% [markdown]
# ## 2. Download records
#
# The GBIF search API returns max 300 records per request.
# We paginate through all results with a 0.5 s delay to respect rate limits.

# %%
all_records = []
for country in COUNTRIES:
    offset = 0
    while True:
        try:
            resp = session.get(f"{GBIF_API}/occurrence/search", params={
                "genusKey": GENUS_KEY, "country": country,
                "hasCoordinate": "true", "hasGeospatialIssue": "false",
                "limit": 300, "offset": offset,
            }, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"  Error at {country} offset {offset}: {e}, retrying...")
            time.sleep(5)
            continue

        data = resp.json()
        records = data.get("results", [])
        if not records:
            break

        for r in records:
            all_records.append({
                "gbifID": r.get("gbifID"),
                "species": r.get("species", ""),
                "scientificName": r.get("scientificName", ""),
                "decimalLatitude": r.get("decimalLatitude"),
                "decimalLongitude": r.get("decimalLongitude"),
                "coordinateUncertaintyInMeters": r.get("coordinateUncertaintyInMeters"),
                "year": r.get("year"),
                "month": r.get("month"),
                "day": r.get("day"),
                "eventDate": r.get("eventDate", ""),
                "countryCode": r.get("countryCode", ""),
                "stateProvince": r.get("stateProvince", ""),
                "basisOfRecord": r.get("basisOfRecord", ""),
                "datasetKey": r.get("datasetKey", ""),
                "issue": "|".join(r.get("issues", [])),
            })

        offset += 300
        if data.get("endOfRecords", False):
            break
        if offset >= 100000:
            break
        time.sleep(0.5)

    print(f"  {country}: {len([r for r in all_records if r['countryCode'] == country])} records")

print(f"\nTotal downloaded: {len(all_records)}")

# %% [markdown]
# ## 3. Quality summary

# %%
df = pd.DataFrame(all_records)

print(f"Unique species: {df['species'].nunique()}")
print(f"Year range: {df['year'].min():.0f} – {df['year'].max():.0f}")
print(f"Records with year: {df['year'].notna().sum()}")
print(f"\nBy country: {df['countryCode'].value_counts().to_dict()}")

print("\nRecords by decade:")
df["decade"] = (df["year"] // 10 * 10).astype("Int64")
for decade, count in df.groupby("decade").size().items():
    print(f"  {decade}s: {count:>6}")

print("\nTop 10 species:")
for sp, count in df["species"].value_counts().head(10).items():
    name = sp if sp else "(unidentified)"
    print(f"  {name}: {count}")

print(f"\nBasis of record:")
for bor, count in df["basisOfRecord"].value_counts().items():
    print(f"  {bor}: {count}")

# %% [markdown]
# ## 4. Save outputs

# %%
outfile = OUTDIR / "gbif_bombus_iberia.csv"
df.drop(columns=["decade"]).to_csv(outfile, index=False)
print(f"Saved: {outfile} ({outfile.stat().st_size / 1e6:.1f} MB)")

metadata = {
    "query": {
        "genus": "Bombus",
        "genusKey": GENUS_KEY,
        "countries": COUNTRIES,
        "hasCoordinate": True,
        "hasGeospatialIssue": False,
        "source": "GBIF REST API (api.gbif.org/v1)",
        "date_accessed": pd.Timestamp.now().isoformat(),
    },
    "summary": {
        "total_records": len(df),
        "unique_species": int(df["species"].nunique()),
        "year_range": [int(df["year"].min()), int(df["year"].max())],
    },
    "citation": "GBIF.org. GBIF Occurrence Download. https://doi.org/10.15468/dl.XXXXXX",
    "note": "Preview via search API. For publication, use GBIF download API for a citable DOI.",
}
meta_file = OUTDIR / "gbif_bombus_iberia_metadata.json"
with open(meta_file, "w") as f:
    json.dump(metadata, f, indent=2, default=str)
print(f"Metadata: {meta_file}")
