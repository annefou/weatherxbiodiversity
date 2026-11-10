# Analysis: combine the monthly climate with the gridded occurrences
# (per-species thermal / precipitation exposure, TEI / PEI), build the model
# table and fit the mixed-effects regression. Soroye port scripts 04, 05a, 05b.
# The climate source is set in the `climate` section of the config; any source
# in the common climate input format works (workflows/CLIMATE_INPUT.md).
# Run on its own: snakemake --cores 1 analysis

CLIMATE = config["climate"]
CLIMATE_DIR = CLIMATE["dir"]
# Climate files produced inside this workflow (ERA5); another source's files
# must already be in CLIMATE_DIR.
CLIMATE_INPUT = ERA5_CLIMATE if CLIMATE["source"] == "era5" else []
CLIMATE_ENV = (
    f"CLIMATE_SOURCE={CLIMATE['source']} CLIMATE_DIR=../{CLIMATE_DIR} "
    f"BASELINE_YEARS={CLIMATE['baseline_years'][0]}-{CLIMATE['baseline_years'][1]} "
    f"RECENT_YEARS={CLIMATE['recent_years'][0]}-{CLIMATE['recent_years'][1]}"
)


rule analysis:
    input:
        f"{RUN}/posterior_vb_summary.csv",


rule climate_exposure:
    input:
        f"{RUN}/presence_absence.npz",
        CLIMATE_INPUT,
    output:
        f"{RUN}/climate_tei_pei.npz",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} {CLIMATE_ENV} python 04_climate_tei_pei.py"


rule model_table:
    input:
        f"{RUN}/presence_absence.npz",
        f"{RUN}/sampling_continent.npz",
        f"{RUN}/climate_tei_pei.npz",
    output:
        f"{RUN}/dataGLMM_extinction.parquet",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} python 05a_build_dataGLMM.py"


rule regression:
    input:
        f"{RUN}/dataGLMM_extinction.parquet",
    output:
        f"{RUN}/posterior_vb_summary.csv",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} python 05b_regression_statsmodels.py"
