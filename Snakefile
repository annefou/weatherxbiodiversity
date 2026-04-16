# Snakefile — Soroye et al. (2020) replication for Iberian Bombus
#
# Runs the full pipeline: GBIF download → ERA5 download → climate departure → spatial join
#
# Usage:
#   snakemake --cores 1                  # run everything
#   snakemake --cores 1 -n               # dry run (show what would be done)
#   snakemake --cores 1 results/soroye_replication_iberia.png  # specific target
#
# Each step is a Jupytext notebook (.py percent format) that can also be
# opened interactively in JupyterLab.

NOTEBOOKS = "notebooks"
DATA = "data"
RESULTS = "results"

rule all:
    input:
        f"{RESULTS}/soroye_replication_iberia.png",
        f"{RESULTS}/soroye_replication_summary.json",
        f"{RESULTS}/climate_departure_map.png",


rule download_gbif:
    output:
        f"{DATA}/gbif_bombus_iberia.csv",
        f"{DATA}/gbif_bombus_iberia_metadata.json",
    log:
        f"{RESULTS}/logs/01_download_gbif.log",
    shell:
        """
        cd {NOTEBOOKS} && jupytext --to notebook --execute 01_download_gbif.py 2>&1 | tee ../{log}
        """


rule download_era5:
    output:
        f"{DATA}/era5_iberia_monthly_tmax.nc",
    log:
        f"{RESULTS}/logs/02_download_era5.log",
    shell:
        """
        cd {NOTEBOOKS} && jupytext --to notebook --execute 02_download_era5.py 2>&1 | tee ../{log}
        """


rule climate_departure:
    input:
        f"{DATA}/era5_iberia_monthly_tmax.nc",
    output:
        f"{DATA}/era5_iberia_climate_departure.nc",
        f"{RESULTS}/climate_departure_map.png",
    log:
        f"{RESULTS}/logs/03_climate_departure.log",
    shell:
        """
        cd {NOTEBOOKS} && jupytext --to notebook --execute 03_climate_departure.py 2>&1 | tee ../{log}
        """


rule soroye_replication:
    input:
        f"{DATA}/gbif_bombus_iberia.csv",
        f"{DATA}/era5_iberia_climate_departure.nc",
    output:
        f"{RESULTS}/soroye_replication_species_cells.csv",
        f"{RESULTS}/soroye_replication_summary.json",
        f"{RESULTS}/soroye_replication_iberia.png",
    log:
        f"{RESULTS}/logs/04_soroye_replication.log",
    shell:
        """
        cd {NOTEBOOKS} && jupytext --to notebook --execute 04_soroye_replication.py 2>&1 | tee ../{log}
        """
