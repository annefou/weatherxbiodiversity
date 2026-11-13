# Analysis (Soroye et al. 2020): 01 study records, 02 presence/absence, 03
# sampling effort (climate-independent, results/<study>/common/), then for each
# climate source in config analysis.sources: 04 climate normals and TEI/PEI,
# 05a model table, 05b GLMM (variational Bayes), 06 forest plot
# (results/<study>/<source>/).

AN = config["analysis"]
GRID = (f"--grid-resolution-m {AN['grid_resolution_m']} --grid-bbox {' '.join(map(str, AN['grid_bbox']))} "
        f"--period-baseline {AN['period_baseline']} --period-recent {AN['period_recent']}")
A = f"{W}/Analysis"


rule analysis_01_study_records:
    input:
        occurrences=f"{RES}/gbif/occurrences_clean.csv",
        err_obs=f"{STUDY}/bombus_err_obs.csv",
    output:
        f"{RES}/common/clean_records.csv",
    shell:
        "python {A}/01_study_records.py --occurrences {input.occurrences} --err-obs {input.err_obs} "
        f"--continent {AN['continent']} --output-dir {RES}/common"


rule analysis_02_presence_absence:
    input:
        f"{RES}/common/clean_records.csv",
    output:
        f"{RES}/common/presence_absence.npz",
    shell:
        f"python {{A}}/02_presence_absence.py --records {{input}} {GRID} --output-dir {RES}/common"


rule analysis_03_sampling_continent:
    input:
        f"{RES}/common/clean_records.csv",
    output:
        f"{RES}/common/sampling_continent.npz",
    shell:
        f"python {{A}}/03_sampling_continent.py --records {{input}} {GRID} --output-dir {RES}/common"


rule analysis_04_climate_tei_pei:
    input:
        pa=f"{RES}/common/presence_absence.npz",
        climate=lambda wc: climate_files(wc.source),
    output:
        f"{RES}/{{source}}/climate_tei_pei.npz",
    params:
        climate_dir=lambda wc: f"{DATA}/climate/{wc.source}",
        years=f"--years-baseline {AN['years_baseline'][0]} {AN['years_baseline'][1]} "
              f"--years-recent {AN['years_recent'][0]} {AN['years_recent'][1]}",
        grid=f"--grid-resolution-m {AN['grid_resolution_m']} --grid-bbox {' '.join(map(str, AN['grid_bbox']))}",
    shell:
        "python {A}/04_climate_tei_pei.py --presence-absence {input.pa} --climate-dir {params.climate_dir} "
        "--climate-source {wildcards.source} {params.years} {params.grid} --output-dir {RES}/{wildcards.source}"


rule analysis_05a_build_data_glmm:
    input:
        pa=f"{RES}/common/presence_absence.npz",
        sampling=f"{RES}/common/sampling_continent.npz",
        climate=f"{RES}/{{source}}/climate_tei_pei.npz",
    output:
        f"{RES}/{{source}}/dataGLMM_extinction.parquet",
    shell:
        "python {A}/05a_build_data_glmm.py --presence-absence {input.pa} --sampling-continent {input.sampling} "
        "--climate-tei-pei {input.climate} --output-dir {RES}/{wildcards.source}"


rule analysis_05b_glmm_extinction:
    input:
        f"{RES}/{{source}}/dataGLMM_extinction.parquet",
    output:
        f"{RES}/{{source}}/logistic_summary.csv",
        f"{RES}/{{source}}/posterior_vb_summary.csv",
    shell:
        "python {A}/05b_glmm_extinction.py --data {input} --seed " + str(AN["seed"]) +
        " --output-dir {RES}/{wildcards.source}"


rule analysis_06_forest_plot:
    input:
        f"{RES}/{{source}}/posterior_vb_summary.csv",
    output:
        f"{RES}/{{source}}/forest.png",
    params:
        title=lambda wc: config["climate"][wc.source]["plot_title"],
        subtitle=lambda wc: config["climate"][wc.source]["plot_subtitle"],
        color=lambda wc: config["climate"][wc.source]["plot_color"],
    shell:
        "python {A}/06_forest_plot.py --summary {input} --title '{params.title}' "
        "--subtitle '{params.subtitle}' --color '{params.color}' --output-dir {RES}/{wildcards.source}"
