"""
Compare the Analysis results of several climate sources (e.g. CRU TS, the
climate data of Soroye et al. 2020, and ERA5) run on the same occurrences.

Inputs, per source: posterior_vb_summary.csv (Analysis 05b) and
dataGLMM_extinction.parquet (05a). Outputs:

  <output-dir>/coefficients.csv      one row per coefficient and source:
                                     mean, sd, 95% interval, model rows
  <output-dir>/forest_comparison.png all coefficients, the sources side by side,
                                     sc_TEI_delta (effect of warming) highlighted

  python compare_sources.py --source cru results/iberia/cru "CRU TS 3.24.01" \
      --source era5 results/iberia/era5 ERA5 --output-dir results/iberia/comparison
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

KEY = "sc_TEI_delta"
COLORS = ["#2b83ba", "#d7191c", "#1a9641", "#7b3294"]


def main() -> None:
    p = argparse.ArgumentParser(description="Compare Analysis results across climate sources")
    p.add_argument("--source", nargs=3, action="append", required=True, metavar=("ID", "DIR", "LABEL"))
    p.add_argument("--title", default="Effect of the climate data on the replication")
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for sid, d, label in a.source:
        s = pd.read_csv(Path(d) / "posterior_vb_summary.csv", index_col=0)
        n = len(pd.read_parquet(Path(d) / "dataGLMM_extinction.parquet"))
        for coef, r in s.iterrows():
            rows.append({"source": sid, "label": label, "coefficient": coef, "mean": r["mean"], "sd": r["sd"],
                         "low": r["mean"] - 1.96 * r["sd"], "high": r["mean"] + 1.96 * r["sd"], "model_rows": n})
    t = pd.DataFrame(rows)
    t.to_csv(a.output_dir / "coefficients.csv", index=False, float_format="%.4f")

    coefs = [c for c in t["coefficient"].unique() if c != "Intercept"]
    order = sorted(coefs, key=lambda c: t[(t.coefficient == c)]["mean"].iloc[0])
    srcs = [s[0] for s in a.source]
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(order) + 1.8))
    step = 0.6 / max(1, len(srcs) - 1) if len(srcs) > 1 else 0
    for i, c in enumerate(order):
        if c == KEY:
            ax.axhspan(i - 0.45, i + 0.45, color="#fff3c4", zorder=0)
        for j, sid in enumerate(srcs):
            r = t[(t.coefficient == c) & (t.source == sid)].iloc[0]
            y = i + 0.3 - j * step
            ax.errorbar(r["mean"], y, xerr=[[r["mean"] - r["low"]], [r["high"] - r["mean"]]],
                        fmt="o", color=COLORS[j % len(COLORS)], capsize=3,
                        label=f"{r['label']} ({r['model_rows']} rows)" if i == 0 else None)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(range(len(order)), order)
    ax.set_xlabel("Coefficient, posterior mean ± 95% interval (log-odds of local extinction)")
    ax.set_title(a.title)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(a.output_dir / "forest_comparison.png", dpi=150)

    for sid in srcs:
        r = t[(t.coefficient == KEY) & (t.source == sid)].iloc[0]
        print(f"{r['label']:>20s}: {KEY} = {r['mean']:+.3f} [{r['low']:+.2f}, {r['high']:+.2f}]  ({r['model_rows']} model rows)")


if __name__ == "__main__":
    main()
