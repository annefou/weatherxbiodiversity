# GBIF_Preprocessing: clean the occurrences and grid them (100 km equal-area):
# presence/absence per species and period, sampling effort per cell.
# Uses the Soroye port scripts 01-03 (soroye_port/). Output: soroye_port/run/phase3/.

RUN = "soroye_port/run/phase3"          # relative to soroye_port/: run/phase3
RUN_SUB = "run/phase3"


rule gbif_clean:
    input:
        GBIF_OCC,
        FIGSHARE_OK,                     # Kerr species list, erroneous-observations table
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
