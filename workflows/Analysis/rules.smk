# Analysis: combine monthly climate with the gridded occurrences (per-species
# thermal / precipitation exposure, TEI / PEI), build the model table, fit the
# mixed-effects regression, and compare with the published coefficients.
# Uses the Soroye port scripts 04, 05a, 05b. Climate: CRU TS (Figshare bundle).

PUBLISHED = "soroye_port/outputs_iberia/posterior_vb_summary.csv"   # committed


rule climate_exposure:
    input:
        f"{RUN}/presence_absence.npz",
        FIGSHARE_OK,                     # CRU TS 3.24.01 monthly tmp/tmn/tmx/pre
    output:
        f"{RUN}/climate_tei_pei.npz",
    shell:
        f"cd soroye_port && OUT_SUBDIR={RUN_SUB} python 04_climate_tei_pei.py"


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


rule compare_with_published:
    input:
        rerun=f"{RUN}/posterior_vb_summary.csv",
        published=PUBLISHED,
    output:
        f"{RUN}/comparison_with_published.txt",
    shell:
        "python workflows/Analysis/compare_with_published.py {input.rerun} {input.published} "
        "--report {output}"
