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
# # Step 1b: Mint a citable GBIF download DOI for Phase 3
#
# This is the *citable* counterpart of `01_download_gbif.py`. The earlier
# notebook used the GBIF **search** API (preview-only, no DOI). For the
# FORRT Replication Study we need a permanent snapshot via the GBIF
# **download** API, which mints a `10.15468/dl.XXXXX` DOI.
#
# ## Requirements
#
# Set GBIF credentials in the shell before running:
#
# ```bash
# export GBIF_USER='your_gbif_username'
# export GBIF_PWD='your_password'
# export GBIF_EMAIL='your.email@example.com'
# ```
#
# The download itself is asynchronous on GBIF's side; this script submits
# the query then polls for completion (5–30 min typical).

# %%
import json
import os
import sys
import time
from pathlib import Path

import requests

# %% [markdown]
# ## Configuration

# %%
OUTDIR = Path("../data") if Path("../data").exists() else Path("data")
OUTDIR.mkdir(exist_ok=True)
META_FILE = OUTDIR / "gbif_bombus_iberia_metadata.json"

GBIF_API = "https://api.gbif.org/v1"
POLL_INTERVAL_SEC = 30
POLL_TIMEOUT_SEC = 60 * 60  # 1 hour

# Same query as 01_download_gbif.py
PREDICATE = {
    "type": "and",
    "predicates": [
        {"type": "equals", "key": "GENUS_KEY", "value": "1340278"},
        {"type": "in", "key": "COUNTRY", "values": ["ES", "PT"]},
        {"type": "equals", "key": "HAS_COORDINATE", "value": "true"},
        {"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE", "value": "false"},
    ],
}

# %%
user = os.environ.get("GBIF_USER")
pwd = os.environ.get("GBIF_PWD")
email = os.environ.get("GBIF_EMAIL")
if not (user and pwd and email):
    sys.exit("Set GBIF_USER, GBIF_PWD, GBIF_EMAIL in the environment first.")

# %% [markdown]
# ## 1. Submit the download request

# %%
request_body = {
    "creator": user,
    "notificationAddresses": [email],
    "sendNotification": True,
    "format": "SIMPLE_CSV",
    "predicate": PREDICATE,
}

print("Submitting GBIF download request...")
resp = requests.post(
    f"{GBIF_API}/occurrence/download/request",
    auth=(user, pwd),
    json=request_body,
    headers={"Content-Type": "application/json"},
    timeout=60,
)
resp.raise_for_status()
download_key = resp.text.strip()
print(f"Download key: {download_key}")
print(f"Status URL:   {GBIF_API}/occurrence/download/{download_key}")

# %% [markdown]
# ## 2. Poll until SUCCEEDED

# %%
start = time.time()
status = None
while time.time() - start < POLL_TIMEOUT_SEC:
    info = requests.get(
        f"{GBIF_API}/occurrence/download/{download_key}", timeout=30
    ).json()
    status = info.get("status")
    elapsed = int(time.time() - start)
    print(f"  [{elapsed:>4d}s] status={status}")
    if status in ("SUCCEEDED", "KILLED", "FAILED", "CANCELLED"):
        break
    time.sleep(POLL_INTERVAL_SEC)

if status != "SUCCEEDED":
    sys.exit(f"Download did not succeed (status={status}).")

# %% [markdown]
# ## 3. Extract DOI and save metadata

# %%
doi = info.get("doi")
total_records = info.get("totalRecords")
download_url = info.get("downloadLink")
license_used = info.get("license")
created = info.get("created")

print()
print(f"Download succeeded.")
print(f"  DOI:           https://doi.org/{doi}")
print(f"  Total records: {total_records:,}")
print(f"  License:       {license_used}")
print(f"  Download URL:  {download_url}")

# %%
metadata = {
    "query": {
        "genus": "Bombus",
        "genusKey": 1340278,
        "countries": ["ES", "PT"],
        "hasCoordinate": True,
        "hasGeospatialIssue": False,
        "source": "GBIF Download API (api.gbif.org/v1/occurrence/download)",
        "predicate": PREDICATE,
    },
    "download": {
        "key": download_key,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "download_url": download_url,
        "license": license_used,
        "created": created,
        "total_records": total_records,
        "creator": user,
    },
    "citation": (
        f"GBIF.org ({created[:10]}) GBIF Occurrence Download "
        f"https://doi.org/{doi}"
    ),
}
META_FILE.write_text(json.dumps(metadata, indent=2, default=str))
print(f"\nMetadata saved: {META_FILE}")
print(f"Citation:       {metadata['citation']}")
