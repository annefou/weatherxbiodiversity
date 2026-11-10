# Snakefile — Soroye et al. (2020) replication for Iberian Bombus (Phase 3)
#
# One folder per workflow step under workflows/, each with its own rules.smk:
#   GBIF_Retrieval      occurrences from GBIF (download key / DOI, or new request)
#   ERA5_Retrieval      monthly statistics from hourly ERA5 (ECMWF ARCO Zarr)
#   GBIF_Preprocessing  clean + grid the occurrences
#   Analysis            climate x occurrences -> exposure indices -> regression
#                       -> comparison with the published coefficients
# Parameters: config/phase3_iberia.yaml. Credentials: credentials/*.json.
#
# Usage (inside `pixi shell`, or prefix with `pixi run`):
#   snakemake --cores 1                    # retrieve, preprocess, analyse, compare
#   snakemake --cores 1 era5_retrieval     # ERA5 monthly statistics (CDS key needed)
#   snakemake --cores 1 -n                 # dry run
#
# Re-runs are written to soroye_port/run/phase3/ (gitignored); the committed
# published results in soroye_port/outputs_iberia/ are never overwritten.
#
# One manual input: Soroye's Figshare bundle, https://doi.org/10.6084/m9.figshare.9956471
# (~1.1 GB, CRU TS + species tables). Figshare refuses scripted downloads:
# download it in a browser and save it as reference/Bumblebee_repo.zip,
# or set FIGSHARE_ZIP=/path/to/Bumblebee_repo.zip.

import os

configfile: "config/phase3_iberia.yaml"

FIGSHARE_ZIP = os.environ.get("FIGSHARE_ZIP", "reference/Bumblebee_repo.zip")
FIGSHARE_OK = "reference/.figshare_extracted"

include: "workflows/GBIF_Retrieval/rules.smk"
include: "workflows/ERA5_Retrieval/rules.smk"
include: "workflows/GBIF_Preprocessing/rules.smk"
include: "workflows/Analysis/rules.smk"


rule all:
    default_target: True
    input:
        f"{RUN}/comparison_with_published.txt",


# Extract only what the port reads: tables (0_data) and CRU TS (0_ClimateData).
rule figshare_extract:
    input:
        FIGSHARE_ZIP,
    output:
        touch(FIGSHARE_OK),
    shell:
        "unzip -o -q {input} 'Bumblebee_repo_wbombusdat/0_data/*' "
        "'Bumblebee_repo_wbombusdat/0_ClimateData/*' -d reference"
