# GBIF_Retrieval: occurrences from GBIF, by download key (DOI) or new request.
# Parameters: the `gbif` section of the config.

GBIF = config["gbif"]
GBIF_OCC = f"{GBIF['output_dir']}/occurrences.csv"
GBIF_META = f"{GBIF['output_dir']}/occurrences.metadata.json"


def gbif_args():
    if GBIF.get("download_key"):
        return f"--download-key {GBIF['download_key']}"
    return " ".join([
        f"--taxon-key {GBIF['taxon_key']}",
        "--countries " + " ".join(GBIF.get("countries", [])),
        "--has-coordinate" if GBIF.get("has_coordinate", True) else "--no-has-coordinate",
        "--has-geospatial-issue" if GBIF.get("has_geospatial_issue", False) else "--no-has-geospatial-issue",
        f"--credentials-file {GBIF['credentials_file']}",
        f"--poll-interval-sec {GBIF.get('poll_interval_sec', 30)}",
        f"--poll-timeout-sec {GBIF.get('poll_timeout_sec', 3600)}",
    ])


rule gbif_retrieval:
    output:
        GBIF_OCC,
        GBIF_META,
    params:
        args=gbif_args(),
    shell:
        "python workflows/GBIF_Retrieval/gbif_retrieve.py {params.args} "
        f"--output-dir {GBIF['output_dir']} --output-name occurrences"
