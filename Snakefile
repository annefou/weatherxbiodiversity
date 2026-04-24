# Snakefile — Soroye et al. (2020) replication for Iberian Bombus
#
# The full replication happens in `soroye_port/`, which is a faithful Python
# port of Soroye's R scripts. This Snakefile orchestrates the upstream data
# download + the port's Phase-3 (Iberia) run.
#
# Usage:
#   snakemake --cores 1                  # run everything
#   snakemake --cores 1 -n               # dry run
#   snakemake --cores 1 soroye_port/phase3_forest.png

NOTEBOOKS = "notebooks"
DATA = "data"
RESULTS = "results"
PORT = "soroye_port"

rule all:
    input:
        f"{PORT}/phase3_forest.png",
        f"{PORT}/outputs_iberia/posterior_vb_summary.csv",


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


rule download_era5_daily:
    output:
        directory(f"{DATA}/era5_daily_max"),
    shell:
        "python download_era5_daily.py"


# --------- Phase 3: apply the Python port to Iberia data ---------

rule port_clean:
    input:
        f"{DATA}/gbif_bombus_iberia.csv",
    output:
        f"{PORT}/outputs_iberia/bombus_clean.csv",
    shell:
        f"cd {PORT} && python 01_clean_data_iberia.py"


rule port_presence:
    input:
        f"{PORT}/outputs_iberia/bombus_clean.csv",
    output:
        f"{PORT}/outputs_iberia/presence_absence.npz",
    shell:
        f"cd {PORT} && OUT_SUBDIR=outputs_iberia python 02_presence_absence.py"


rule port_sampling:
    input:
        f"{PORT}/outputs_iberia/bombus_clean.csv",
    output:
        f"{PORT}/outputs_iberia/sampling_continent.npz",
    shell:
        f"cd {PORT} && OUT_SUBDIR=outputs_iberia python 03_sampling_continent.py"


rule port_climate:
    input:
        f"{PORT}/outputs_iberia/presence_absence.npz",
    output:
        f"{PORT}/outputs_iberia/climate_tei_pei.npz",
    shell:
        f"cd {PORT} && OUT_SUBDIR=outputs_iberia python 04_climate_tei_pei.py"


rule port_regression:
    input:
        f"{PORT}/outputs_iberia/presence_absence.npz",
        f"{PORT}/outputs_iberia/sampling_continent.npz",
        f"{PORT}/outputs_iberia/climate_tei_pei.npz",
    output:
        f"{PORT}/outputs_iberia/posterior_vb_summary.csv",
        f"{PORT}/outputs_iberia/dataGLMM_extinction.parquet",
    shell:
        f"cd {PORT} && OUT_SUBDIR=outputs_iberia python 05b_regression_statsmodels.py"


rule port_plot:
    input:
        f"{PORT}/outputs_iberia/posterior_vb_summary.csv",
    output:
        f"{PORT}/phase3_forest.png",
    shell:
        f"cd {PORT} && python plot_forest.py"
