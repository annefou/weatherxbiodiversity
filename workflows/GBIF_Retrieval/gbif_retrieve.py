"""
Generic GBIF occurrence retrieval.

Two modes:
  * --download-key KEY   fetch an existing GBIF download (public, no login).
  * otherwise            submit a new download for the given filters, wait for
                         GBIF to prepare it, then fetch it. Needs a credentials
                         file (--credentials-file) with "user", "password", "email".

Filters for a new download:
  --taxon-key         GBIF taxon key (any rank: species, genus, family, ...)
  --countries         ISO country codes, e.g. "ES PT" or "ES,PT"
  --has-coordinate / --no-has-coordinate              (default: required)
  --has-geospatial-issue / --no-has-geospatial-issue  (default: excluded)

Output (in --output-dir):
  <name>.csv            occurrences, GBIF SIMPLE_CSV (tab-separated)
  <name>.metadata.json  key, DOI, citation, licence, record count, query
where <name> is --output-name, or the download key by default.

Every GBIF download gets a DOI, so the result is always citable.
"""

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

API = "https://api.gbif.org/v1"


def predicate(taxon_key, countries, has_coordinate, has_geospatial_issue) -> dict:
    preds = [{"type": "equals", "key": "TAXON_KEY", "value": str(taxon_key)}]
    if countries:
        preds.append({"type": "in", "key": "COUNTRY", "values": countries})
    preds.append({"type": "equals", "key": "HAS_COORDINATE", "value": str(has_coordinate).lower()})
    preds.append({"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE",
                  "value": str(has_geospatial_issue).lower()})
    return {"type": "and", "predicates": preds}


def read_credentials(path: Path) -> dict:
    try:
        creds = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"Cannot read GBIF credentials file {path}: {e}")
    missing = [k for k in ("user", "password", "email") if not creds.get(k)]
    if missing:
        sys.exit(f"GBIF credentials file {path} lacks: {', '.join(missing)}")
    return creds


def submit(pred: dict, creds: dict, poll_interval: int, poll_timeout: int) -> str:
    body = {"creator": creds["user"], "notificationAddresses": [creds["email"]],
            "sendNotification": True, "format": "SIMPLE_CSV", "predicate": pred}
    r = requests.post(f"{API}/occurrence/download/request",
                      auth=(creds["user"], creds["password"]), json=body, timeout=60)
    r.raise_for_status()
    key = r.text.strip()
    print(f"Submitted GBIF download {key}; waiting for GBIF to prepare it ...", flush=True)
    t0 = time.monotonic()
    while time.monotonic() - t0 < poll_timeout:
        status = requests.get(f"{API}/occurrence/download/{key}", timeout=30).json()["status"]
        print(f"  [{int(time.monotonic() - t0):>5d}s] {status}", flush=True)
        if status == "SUCCEEDED":
            return key
        if status in ("KILLED", "FAILED", "CANCELLED"):
            sys.exit(f"GBIF download {key} ended with status {status}")
        time.sleep(poll_interval)
    sys.exit(f"GBIF download {key} not ready after {poll_timeout} s; "
             f"re-run later with --download-key {key}")


def fetch(key: str, outdir: Path, name: str | None = None) -> None:
    info = requests.get(f"{API}/occurrence/download/{key}", timeout=30)
    info.raise_for_status()
    info = info.json()
    if info.get("status") != "SUCCEEDED":
        sys.exit(f"GBIF download {key} is not available (status {info.get('status')})")

    outdir.mkdir(parents=True, exist_ok=True)
    zpath = outdir / f"{key}.zip"
    print(f"Fetching GBIF download {key} (DOI {info.get('doi')}) ...", flush=True)
    with requests.get(info["downloadLink"], stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(zpath, "wb") as f:
            for block in r.iter_content(1 << 20):
                f.write(block)
    name = name or key
    with zipfile.ZipFile(zpath) as z, open(outdir / f"{name}.csv", "wb") as out:
        out.write(z.read(f"{key}.csv"))
    zpath.unlink()

    meta = {
        "download_key": key,
        "doi": info.get("doi"),
        "doi_url": f"https://doi.org/{info.get('doi')}",
        "citation": f"GBIF.org ({info.get('created', '')[:10]}) GBIF Occurrence Download "
                    f"https://doi.org/{info.get('doi')}",
        "license": info.get("license"),
        "total_records": info.get("totalRecords"),
        "created": info.get("created"),
        "predicate": info.get("request", {}).get("predicate"),
    }
    (outdir / f"{name}.metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved {outdir / f'{name}.csv'} ({meta['total_records']} records)")
    print(f"Cite: {meta['citation']}")


def main() -> None:
    p = argparse.ArgumentParser(description="Generic GBIF occurrence retrieval")
    p.add_argument("--download-key", help="existing GBIF download key (no login needed)")
    p.add_argument("--credentials-file", type=Path,
                   help='JSON with "user", "password", "email" (new downloads only)')
    p.add_argument("--taxon-key", type=int, help="GBIF taxon key, e.g. 1340278 (Bombus)")
    p.add_argument("--countries", nargs="*", default=[],
                   help='ISO codes, e.g. "ES PT" or "ES,PT"')
    p.add_argument("--has-coordinate", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--has-geospatial-issue", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--output-dir", type=Path, default=Path("data/gbif_dl"))
    p.add_argument("--output-name", help="file name stem (default: the download key)")
    p.add_argument("--poll-interval-sec", type=int, default=30)
    p.add_argument("--poll-timeout-sec", type=int, default=3600)
    a = p.parse_args()

    key = a.download_key
    if not key:
        if a.taxon_key is None or a.credentials_file is None:
            p.error("without --download-key, --taxon-key and --credentials-file are required")
        countries = [c.strip().upper() for arg in a.countries for c in arg.split(",") if c.strip()]
        pred = predicate(a.taxon_key, countries, a.has_coordinate, a.has_geospatial_issue)
        print("Filters:", json.dumps(pred))
        key = submit(pred, read_credentials(a.credentials_file),
                     a.poll_interval_sec, a.poll_timeout_sec)
    fetch(key, a.output_dir, a.output_name)


if __name__ == "__main__":
    main()
