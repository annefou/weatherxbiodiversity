# Snakefile — Soroye et al. (2020) replication for Iberian Bombus, with ERA5
#
# One Snakemake file per step under workflows/ (mirrors the GitLab ARC):
#   GBIF_Retrieval      download occurrences (GBIF download key / DOI, or new request)
#   ERA5_Retrieval      download monthly ERA5 statistics (ECMWF ARCO Zarr store)
#   GBIF_Preprocessing  clean + grid the occurrences          (scripts 01-03)
#   ERA5_Preprocessing  monthly tmp / tmn / tmx / pre
#   Analysis            exposure indices + regression          (scripts 04, 05a, 05b)
# Parameters: config/phase3_iberia.yaml. Credentials: credentials/*.json.
#
# Usage (inside `pixi shell`, or prefix with `pixi run`):
#   snakemake --cores 1                       # all steps
#   snakemake --cores 1 gbif_download         # one step: gbif_download, era5_download,
#                                             #   gbif_preprocessing, era5_preprocessing, analysis
#   snakemake --cores 1 -n                    # dry run
#
# Results: soroye_port/<run_subdir>/posterior_vb_summary.csv (gitignored).
#
# Manual input: Soroye's Figshare bundle, https://doi.org/10.6084/m9.figshare.9956471
# (~1.1 GB; only its species tables are used). Figshare refuses scripted downloads:
# download it in a browser and save it as reference/Bumblebee_repo.zip,
# or set FIGSHARE_ZIP=/path/to/Bumblebee_repo.zip.

import os

configfile: "config/phase3_iberia.yaml"

include: "workflows/GBIF_Retrieval/rules.smk"
include: "workflows/ERA5_Retrieval/rules.smk"
include: "workflows/GBIF_Preprocessing/rules.smk"
include: "workflows/ERA5_Preprocessing/rules.smk"
include: "workflows/Analysis/rules.smk"


rule all:
    default_target: True
    input:
        f"{RUN}/posterior_vb_summary.csv",
