# GBIF_Preprocessing: clean the occurrences (Kerr et al. 2015 species list,
# synonyms, erroneous observations, periods) and grid them on the 100 km
# equal-area grid: presence/absence per species and period, sampling effort.
# Soroye port scripts 01-03. Species tables come from Soroye's Figshare bundle.
# Run on its own: snakemake --cores 1 gbif_preprocessing

FIGSHARE_ZIP = os.environ.get("FIGSHARE_ZIP", "reference/Bumblebee_repo.zip")
FIGSHARE_TABLES = "reference/.figshare_tables_extracted"
RUN_SUB = config["run_subdir"]          # under soroye_port/
RUN = f"soroye_port/{RUN_SUB}"


rule gbif_preprocessing:
    input:
        f"{RUN}/presence_absence.npz",
        f"{RUN}/sampling_continent.npz",


# Only the species tables (0_data) are needed: Kerr species list, erroneous observations.
rule figshare_tables:
    input:
        FIGSHARE_ZIP,
    output:
        touch(FIGSHARE_TABLES),
    shell:
        "unzip -o -q {input} 'Bumblebee_repo_wbombusdat/0_data/*' -d reference"


rule gbif_clean:
    input:
        GBIF_OCC,
        FIGSHARE_TABLES,
    output:
        f"{RUN}/bombus_clean.csv",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} GBIF_CSV=../{GBIF_OCC} python 01_clean_data_iberia.py"


rule gbif_presence_absence:
    input:
        f"{RUN}/bombus_clean.csv",
    output:
        f"{RUN}/presence_absence.npz",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} python 02_presence_absence.py"


rule gbif_sampling:
    input:
        f"{RUN}/bombus_clean.csv",
    output:
        f"{RUN}/sampling_continent.npz",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} python 03_sampling_continent.py"
