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
        sources=" ".join(f"--source {s} {RES}/{s} '{config['climate'][s]['label']}'" for s in config["analysis"]["sources"]),
    shell:
        "python {W}/Comparison/compare_sources.py {params.sources} "
        "--title 'Iberian Bombus: the same analysis with two climate datasets' --output-dir {RES}/comparison"
