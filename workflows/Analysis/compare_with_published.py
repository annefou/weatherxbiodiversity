"""
Compare re-generated regression coefficients with the published ones.

Both inputs are posterior_vb_summary.csv files (columns: mean, sd, z, p_2sided;
one row per fixed effect). Writes a small report and prints it:
  identical  |diff| < 1e-9
  close      |diff of mean| <= tol (default 0.01) and same sign
  DIFFERENT  otherwise
Exit status is 0 in all cases: the report is the result.
"""

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("rerun", type=Path)
    p.add_argument("published", type=Path)
    p.add_argument("--tol", type=float, default=0.01)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()

    new = pd.read_csv(a.rerun, index_col=0)
    old = pd.read_csv(a.published, index_col=0)
    terms = old.index.union(new.index, sort=False)
    rows = []
    for t in terms:
        if t not in new.index or t not in old.index:
            rows.append((t, old["mean"].get(t), new["mean"].get(t), None, "MISSING"))
            continue
        d = abs(new.at[t, "mean"] - old.at[t, "mean"])
        same_sign = (new.at[t, "mean"] > 0) == (old.at[t, "mean"] > 0)
        verdict = ("identical" if d < 1e-9 and abs(new.at[t, "sd"] - old.at[t, "sd"]) < 1e-9
                   else "close" if d <= a.tol and same_sign else "DIFFERENT")
        rows.append((t, old.at[t, "mean"], new.at[t, "mean"], d, verdict))

    rep = pd.DataFrame(rows, columns=["term", "published", "rerun", "abs_diff", "verdict"])
    counts = rep["verdict"].value_counts().to_dict()
    text = (f"Re-run {a.rerun}\nvs published {a.published}\n\n"
            + rep.to_string(index=False, float_format=lambda x: f"{x:+.6f}")
            + f"\n\nSummary: {counts}\n")
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
