"""
Metadata of an EXISTING GBIF occurrence download, by download key or DOI.

Alternative to 00-submit-request.py for reusing a published download (e.g. the
pinned download of a study): no new request, no GBIF account needed. Writes the
same metadata.json as 00-submit-request.py, which 01-download.py then uses to
fetch and unpack the archive.

  python 00-existing-download.py --download 10.15468/dl.3frmsq --output-meta metadata.json
  python 00-existing-download.py --download 0006204-260423192947929
"""
import argparse
import json
from pathlib import Path

import requests

GBIF_API = "https://api.gbif.org/v1"

parser = argparse.ArgumentParser(description="Metadata of an existing GBIF download (key or DOI).")
parser.add_argument("--download", required=True,
                    help="GBIF download key (e.g. 0006204-260423192947929) or DOI (e.g. 10.15468/dl.3frmsq)")
parser.add_argument("--output-meta", type=Path, default=Path("metadata.json"))
args = parser.parse_args()

ref = args.download.removeprefix("https://doi.org/").removeprefix("doi:")
r = requests.get(f"{GBIF_API}/occurrence/download/{ref}", timeout=60)
r.raise_for_status()
d = r.json()
if d.get("status") != "SUCCEEDED":
    raise SystemExit(f"GBIF download {ref} is not available (status {d.get('status')})")

request = d.get("request", {})
metadata = {
    "query": {
        "source": "GBIF Download API (api.gbif.org/v1/occurrence/download), existing download",
        "format": request.get("format"),
        "predicate": request.get("predicate"),
    },
    "download": {
        "key": d["key"],
        "doi": d["doi"],
        "doi_url": f"https://doi.org/{d['doi']}",
        "download_url": d["downloadLink"],
        "license": d.get("license"),
        "created": d.get("created"),
        "total_records": d.get("totalRecords"),
    },
    "citation": f"GBIF.org ({str(d.get('created'))[:10]}) GBIF Occurrence Download https://doi.org/{d['doi']}",
}
args.output_meta.write_text(json.dumps(metadata, indent=2, default=str))
print(f"Metadata saved: {args.output_meta}")
print(f"Citation:       {metadata['citation']}")
print(f"Format:         {request.get('format')}, {d.get('totalRecords')} records")
