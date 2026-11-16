"""
Centres (latitude, longitude) of the study grid cells that hold records, as a
points table for era5_retrieve.py --occurrences: ERA5 is then fetched only for
the store tiles around these cells instead of whole boxes (useful for studies
spread over large areas, e.g. two continents).

Input: presence_absence.npz from Analysis 02 (cells with records in the
baseline or recent period) and the study grid (CEA, as in Analysis 04).

Output: a tab-separated table with columns decimalLatitude, decimalLongitude.

Example:
  python grid_cells.py --presence-absence presence_absence.npz \
      --grid-resolution-m 100000 --grid-bbox -20037507 20062493 -5263885 6336115 \
      --output grid_cells.tsv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

# Same equal-area projection as Analysis 02-04 (Soroye et al. 2020).
CEA_CRS = "+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84"


def main() -> None:
    p = argparse.ArgumentParser(description="Grid cell centres with records, as ERA5 retrieval points")
    p.add_argument("--presence-absence", type=Path, required=True)
    p.add_argument("--grid-resolution-m", type=float, required=True)
    p.add_argument("--grid-bbox", type=float, nargs=4, required=True,
                   metavar=("XMIN", "XMAX", "YMIN", "YMAX"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    res = a.grid_resolution_m
    x_min, x_max, y_min, y_max = a.grid_bbox
    n_x = int(round((x_max - x_min) / res))
    n_y = int(round((y_max - y_min) / res))
    xx, yy = np.meshgrid(x_min + (np.arange(n_x) + 0.5) * res,
                         y_max - (np.arange(n_y) + 0.5) * res)
    lon, lat = Transformer.from_crs(CEA_CRS, "EPSG:4326", always_xy=True).transform(xx.ravel(), yy.ravel())

    pa = np.load(a.presence_absence, allow_pickle=True)
    used = (pa["sprich_baseline"] > 0) | (pa["sprich_recent"] > 0)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"decimalLatitude": lat[used], "decimalLongitude": lon[used]}).to_csv(
        a.output, sep="\t", index=False)
    print(f"{used.sum()} grid cells with records -> {a.output}")


if __name__ == "__main__":
    main()
