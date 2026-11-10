# Analysis: combine the monthly ERA5 climate with the gridded occurrences
# (per-species thermal / precipitation exposure, TEI / PEI), build the model
# table and fit the mixed-effects regression. Soroye port scripts 04, 05a, 05b.
# Run on its own: snakemake --cores 1 analysis


rule analysis:
    input:
        f"{RUN}/posterior_vb_summary.csv",


rule climate_exposure:
    input:
        f"{RUN}/presence_absence.npz",
        ERA5_CLIMATE,
    output:
        f"{RUN}/climate_tei_pei.npz",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} CLIMATE_SOURCE=era5 "
        f"ERA5_CLIMATE_DIR=../{ERA5_CLIMATE_DIR} python 04_climate_tei_pei.py"


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
