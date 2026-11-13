# Comparison: the Analysis results of the climate sources side by side
# (same occurrences, same code; only the climate data differ).

rule comparison:
    input:
        expand(f"{RES}/{{source}}/posterior_vb_summary.csv", source=config["analysis"]["sources"]),
        expand(f"{RES}/{{source}}/dataGLMM_extinction.parquet", source=config["analysis"]["sources"]),
    output:
        f"{RES}/comparison/coefficients.csv",
        f"{RES}/comparison/forest_comparison.png",
    params:
        sources=" ".join(f"--source {s} {RES}/{s} {shlex.quote(config['climate'][s]['label'])}" for s in config["analysis"]["sources"]),
    shell:
        "python {W}/Comparison/compare_sources.py {params.sources} "
        "--title 'Iberian Bombus: the same analysis with two climate datasets' --output-dir {RES}/comparison"


# Same rows: every source restricted to the species x grid-cell rows common to
# all sources (re-standardised), refitted with Analysis 05b, and compared:
# separates the effect of the climate values from that of the coverage.

COMMON = f"{RES}/comparison/common_rows"


rule comparison_common_rows:
    input:
        expand(f"{RES}/{{source}}/dataGLMM_extinction.parquet", source=config["analysis"]["sources"]),
    output:
        expand(f"{COMMON}/{{source}}/dataGLMM_extinction.parquet", source=config["analysis"]["sources"]),
    params:
        sources=" ".join(f"--source {s} {RES}/{s}" for s in config["analysis"]["sources"]),
    shell:
        "python {W}/Comparison/common_rows.py {params.sources} --output-dir {COMMON}"


rule comparison_common_rows_fit:
    input:
        f"{COMMON}/{{source}}/dataGLMM_extinction.parquet",
    output:
        f"{COMMON}/{{source}}/logistic_summary.csv",
        f"{COMMON}/{{source}}/posterior_vb_summary.csv",
    shell:
        "python {W}/Analysis/05b_glmm_extinction.py --data {input} --seed " + str(config["analysis"]["seed"]) +
        " --output-dir {COMMON}/{wildcards.source}"


rule comparison_common:
    input:
        expand(f"{COMMON}/{{source}}/posterior_vb_summary.csv", source=config["analysis"]["sources"]),
    output:
        f"{COMMON}/coefficients.csv",
        f"{COMMON}/forest_comparison.png",
    params:
        sources=" ".join(f"--source {s} {COMMON}/{s} {shlex.quote(config['climate'][s]['label'])}" for s in config["analysis"]["sources"]),
    shell:
        "python {W}/Comparison/compare_sources.py {params.sources} "
        "--title 'Iberian Bombus: two climate datasets on the same rows' --output-dir {COMMON}"


# Climate sources that are another source restricted to a period
# (config climate.<id>.period_of: <source>), e.g. CRU TS on ERA5's years.

rule climate_period:
    input:
        lambda wc: climate_files(config["climate"][wc.source]["period_of"]),
    output:
        f"{DATA}/climate/{{source}}/{{source}}_tmp_monthly_{{y0}}_{{y1}}.nc",
        f"{DATA}/climate/{{source}}/{{source}}_tmn_monthly_{{y0}}_{{y1}}.nc",
        f"{DATA}/climate/{{source}}/{{source}}_tmx_monthly_{{y0}}_{{y1}}.nc",
        f"{DATA}/climate/{{source}}/{{source}}_pre_monthly_{{y0}}_{{y1}}.nc",
    wildcard_constraints:
        source="|".join(s for s, c in config["climate"].items() if "period_of" in c) or "NONE",
    params:
        src=lambda wc: config["climate"][wc.source]["period_of"],
    shell:
        "python {W}/Comparison/climate_period.py --input-dir {DATA}/climate/{params.src} --from {params.src} "
        "--output-dir {DATA}/climate/{wildcards.source} --to {wildcards.source} --years {wildcards.y0} {wildcards.y1}"
