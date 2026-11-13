
import argparse
import json
import sys
import zipfile
import requests
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--metadata_file", type=Path, default= "metadata.json", help = "Path to a metadata.json file provided by GBIF download request.")
parser.add_argument("--output_dir", type=Path, default= "gbif_data", help = "Path to store the download and unzipped GBIF data")

args = parser.parse_args()
metadata_file = args.metadata_file
output_dir = args.output_dir

with open(metadata_file) as f:
    metadata = json.load(f)

url = metadata["download"]["download_url"]

print(f"Downloading: {url}")

response = requests.get(url, stream=True, timeout=120)
response.raise_for_status()

zip_path = Path("gbif_download.zip")

with zip_path.open("wb") as f:
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if chunk:
            f.write(chunk)

print("Download completed.")

# Extract archive

output_dir.mkdir(exist_ok=True)

with zipfile.ZipFile(zip_path, "r") as archive:
    archive.extractall(output_dir)

print(f"Extracted files to: {output_dir}")

# Remove ZIP after extraction
zip_path.unlink()

print("ZIP archive removed.")
