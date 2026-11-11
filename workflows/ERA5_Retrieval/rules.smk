# ERA5_Retrieval: stream hourly ERA5 from ECMWF's ARCO Zarr store and save
# daily or monthly statistics. Parameters: the `era5` section of the config.
# Run on its own: snakemake --cores 1 era5_download

import json

ERA5 = config["era5"]
ERA5_START, ERA5_END = ERA5["years"]
ERA5_FREQ = ERA5.get("frequency", "monthly")
if ERA5_FREQ == "monthly":
    ERA5_FILES = [
        f"{ERA5['output_dir']}/era5_{var}_{stat}_monthly_{ERA5_START}_{ERA5_END}.nc"
        for var, stats in ERA5["variables"].items() for stat in stats
    ]
else:
    ERA5_FILES = [
        f"{ERA5['output_dir']}/era5_{var}_{stat}_daily_{year}.nc"
        for var, stats in ERA5["variables"].items() for stat in stats
        for year in range(ERA5_START, ERA5_END + 1)
    ]


def era5_region():
    if ERA5["area"] == "occurrences":
        return f"--occurrences {GBIF_OCC} --buffer {ERA5.get('buffer', 1.0)}"
    n, w, s, e = ERA5["area"]
    return f"--area {n} {w} {s} {e}"


rule era5_download:
    input:
        ERA5_FILES,


rule era5_retrieve:
    input:
        GBIF_OCC if ERA5["area"] == "occurrences" else [],
    output:
        ERA5_FILES,
    params:
        variables=json.dumps(ERA5["variables"]),
        region=era5_region(),
        credentials=ERA5["credentials_file"],
    shell:
        # The CDS credentials file is required (recommended over ~/.cdsapirc).
        "test -f {params.credentials} || {{ echo 'Missing {params.credentials}: copy "
        "credentials/cds_credentials.example.json to it and put your CDS API key in it "
        "(https://cds.climate.copernicus.eu/profile).' >&2; exit 1; }}; "
        "python workflows/ERA5_Retrieval/era5_retrieve.py --frequency " + ERA5_FREQ +
        " --variables '{params.variables}' "
        f"--years {ERA5_START} {ERA5_END} {{params.region}} "
        f"--credentials-file {ERA5['credentials_file']} --output-dir {ERA5['output_dir']}"
