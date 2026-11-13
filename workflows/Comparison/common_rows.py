"""
Model tables of several climate sources restricted to their common rows.

The sources differ in coverage (CRU TS is land-only, so coastal grid cells
have no CRU value; the ERA5 boxes cover them), so their model tables
(dataGLMM_extinction.parquet, Analysis 05a) do not hold exactly the same
species x grid-cell rows. This keeps, for every source, only the rows
(species, site) present in all sources, and re-standardises the predictors
(sc_*) within those rows, as Analysis 05a does over its whole table (z-score,
ddof=1). Fitting these tables with Analysis 05b separates the effect of the
climate values from that of the coverage.

  python common_rows.py --source cru results/iberia/cru --source era5 results/iberia/era5 \
      --output-dir results/iberia/comparison/common_rows
writes <output-dir>/<source>/dataGLMM_extinction.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

KEY = ["species", "site"]
PREDICTORS = ["sampling", "TEI_bs", "TEI_delta", "PEI_bs", "PEI_delta",
              "avgtemp_bs", "avgtemp_delta", "avgprecip_bs", "avgprecip_delta"]


def main() -> None:
    p = argparse.ArgumentParser(description="Restrict model tables to the rows common to all sources")
    p.add_argument("--source", nargs=2, action="append", required=True, metavar=("ID", "DIR"))
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()

    tables = {sid: pd.read_parquet(Path(d) / "dataGLMM_extinction.parquet") for sid, d in a.source}
    common = None
    for t in tables.values():
        keys = set(map(tuple, t[KEY].itertuples(index=False)))
        common = keys if common is None else common & keys
    print(f"common rows: {len(common)} " + ", ".join(f"({sid}: {len(t)})" for sid, t in tables.items()))

    for sid, t in tables.items():
        keep = [k in common for k in map(tuple, t[KEY].itertuples(index=False))]
        sub = t[keep].copy().reset_index(drop=True)
        for col in PREDICTORS:
            sub[f"sc_{col}"] = (sub[col] - sub[col].mean()) / sub[col].std(ddof=1)
        out = a.output_dir / sid
        out.mkdir(parents=True, exist_ok=True)
        sub.to_parquet(out / "dataGLMM_extinction.parquet")
        print(f"  {sid}: {len(sub)} rows -> {out / 'dataGLMM_extinction.parquet'}")


if __name__ == "__main__":
    main()
