# %% [markdown]
# Mints a citable GBIF download DOI for the requested data.
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
# Or provide a JSON file with `--credentials-file gbif_credentials.json`:
#
# ```json
# {"user": "your_gbif_username", "password": "your_password", "email": "your.email@example.com"}
# ```
# Environment variables take precedence over values in the JSON file.
#
# The download itself is asynchronous on GBIF's side; this script submits
# the query then polls for completion (5–30 min typical).
#
# > [!WARNING]
# > This script does **not** download the occurrence data. It mints the
# > DOI and writes the metadata (to the --output-meta path)
# > only. Pass the metadata file to 01-download.py to download and unpack the data.

# %%
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

# %% [markdown]
# ## Configuration

# %%
parser = argparse.ArgumentParser(
    description="Submit a parameterized GBIF occurrence download."
)
parser.add_argument(
    "--credentials-file",
    type=Path,
    help="JSON file containing GBIF user, password, and email.",
)
parser.add_argument("--genus", help="Genus name recorded in metadata.")
parser.add_argument("--genus-key", type=int, help="GBIF taxon key for the genus.")
parser.add_argument("--countries", nargs="+", help="Country codes to include.")
parser.add_argument(
    "--has-coordinate",
    action=argparse.BooleanOptionalAction,
    default=True,
    help="Require coordinates (default: enabled).",
)
parser.add_argument(
    "--has-geospatial-issue",
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Include records with geospatial issues (default: disabled).",
)
parser.add_argument(
    "--output-meta",
    type=Path,
    default="metadata.json",
    help="File name for output metadata file.",
)
parser.add_argument(
    "--poll-interval-sec",
    type=int,
    default=30,
    help="Seconds between status checks (default: 30).",
)
parser.add_argument(
    "--poll-timeout-sec",
    type=int,
    default=60 * 60,
    help="Maximum wait in seconds (default: 3600).",
)

args = parser.parse_args()
args.countries = [
    country.strip()
    for value in args.countries
    for country in value.split(",")
    if country.strip()
]

META_FILE = args.output_meta

GBIF_API = "https://api.gbif.org/v1"
POLL_INTERVAL_SEC = args.poll_interval_sec
POLL_TIMEOUT_SEC = args.poll_timeout_sec

PREDICATE = {
    "type": "and",
    "predicates": [
        {"type": "equals", "key": "GENUS_KEY", "value": str(args.genus_key)},
        {"type": "in", "key": "COUNTRY", "values": args.countries},
        {
            "type": "equals",
            "key": "HAS_COORDINATE",
            "value": str(args.has_coordinate).lower(),
        },
        {
            "type": "equals",
            "key": "HAS_GEOSPATIAL_ISSUE",
            "value": str(args.has_geospatial_issue).lower(),
        },
    ],
}

# %%
file_credentials = {}
if args.credentials_file:
    try:
        file_credentials = json.loads(args.credentials_file.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Could not read credentials file: {exc}")
    if not isinstance(file_credentials, dict):
        parser.error("Credentials file must contain a JSON object.")

user = os.environ.get("GBIF_USER") or file_credentials.get("user")
pwd = os.environ.get("GBIF_PWD") or file_credentials.get("password")
email = os.environ.get("GBIF_EMAIL") or file_credentials.get("email")
if not (user and pwd and email):
    parser.error(
        "Provide user, password, and email via --credentials-file or GBIF_USER, GBIF_PWD, and GBIF_EMAIL."
    )

# %% [markdown]
# ## 1. Submit the download request

# %%
request_body = {
    "creator": user,
    "notificationAddresses": [email],
    "sendNotification": True,
    "format": "DWCA",
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
        "genus": args.genus,
        "genusKey": args.genus_key,
        "countries": args.countries,
        "hasCoordinate": args.has_coordinate,
        "hasGeospatialIssue": args.has_geospatial_issue,
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
        f"GBIF.org ({created[:10]}) GBIF Occurrence Download " f"https://doi.org/{doi}"
    ),
}
META_FILE.write_text(json.dumps(metadata, indent=2, default=str))
print(f"\nMetadata saved: {META_FILE}")
print(f"Citation:       {metadata['citation']}")
