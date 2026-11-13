# Soroye et al. (2020) replication for Iberian Bombus: GBIF + climate -> analysis.
#
# The same scripts as the ARC (WeatherXBiodiversity_Soroye2020 on DataHUB), one
# Snakemake file per step under workflows/<Step>/rules.smk, with the parameters
# in config/iberia.yaml:
#   GBIF_Retrieval      existing GBIF download (key/DOI), or a new request
#   GBIF_Preprocessing  generic cleaning of the occurrence table
#   ERA5_Retrieval      monthly ERA5 statistics from ECMWF's ARCO store
#   ERA5_Preprocessing  monthly tmp / tmn / tmx / pre (common climate input)
#   Analysis            study records, presence/absence, sampling, TEI/PEI,
#                       GLMM, forest plot (one run per climate source)
#
# Usage (with pixi):
#   pixi run snakemake --cores 1             # everything
#   pixi run snakemake --cores 1 -n          # dry run
#   pixi run snakemake --cores 1 gbif_preprocessing   # one step
#
# Inputs: studies/soroye2020/ (study tables, in the repository); data/ (downloads);
# results/<study>/ (outputs). Credentials (credentials/*.json, git-ignored):
# CDS API key for ERA5; GBIF account only for a new GBIF download.

import json

configfile: "config/iberia.yaml"

DATA = "data"
RES = f"results/{config['study']}"
W = "workflows"
STUDY = config["study_tables"]


def climate_files(source):
    y0, y1 = config["climate"][source]["years"]
    return [f"{DATA}/climate/{source}/{source}_{v}_monthly_{y0}_{y1}.nc" for v in ("tmp", "tmn", "tmx", "pre")]


include: f"{W}/GBIF_Retrieval/rules.smk"
include: f"{W}/GBIF_Preprocessing/rules.smk"
include: f"{W}/ERA5_Retrieval/rules.smk"
include: f"{W}/ERA5_Preprocessing/rules.smk"
include: f"{W}/Analysis/rules.smk"


rule all:
    input:
        expand(f"{RES}/{{source}}/posterior_vb_summary.csv", source=config["analysis"]["sources"]),
        expand(f"{RES}/{{source}}/forest.png", source=config["analysis"]["sources"]),
