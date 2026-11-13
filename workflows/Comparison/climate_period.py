"""
A climate source restricted to a period: e.g. CRU TS cut to ERA5's years
(1940-2014), to separate the effect of the climate dataset from that of the
period (ERA5 starts in 1940, so its baseline climate is 1940-1974 instead of
1901-1974, and its "all years" climate limits are 1940-2014).

Reads <input-dir>/<from>_{tmp,tmn,tmx,pre}_monthly_*.nc (common climate input
format) and writes <output-dir>/<to>_{var}_monthly_<start>_<end>.nc.

  python climate_period.py --input-dir data/climate/cru --from cru \
      --output-dir data/climate/cru_1940 --to cru_1940 --years 1940 2014
"""
from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr


def main() -> None:
    p = argparse.ArgumentParser(description="Restrict a climate source to a period")
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--from", dest="src", required=True, help="file prefix of the input source")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--to", dest="dst", required=True, help="file prefix of the output source")
    p.add_argument("--years", nargs=2, type=int, required=True, metavar=("START", "END"))
    a = p.parse_args()
    y0, y1 = a.years
    a.output_dir.mkdir(parents=True, exist_ok=True)
    for var in ("tmp", "tmn", "tmx", "pre"):
        files = sorted(a.input_dir.glob(f"{a.src}_{var}_monthly_*.nc"))
        if len(files) != 1:
            raise SystemExit(f"expected one {a.src}_{var}_monthly_*.nc in {a.input_dir}, found {len(files)}")
        da = xr.open_dataarray(files[0])
        sub = da.sel(time=(da.time.dt.year >= y0) & (da.time.dt.year <= y1))
        sub.attrs["source"] = f"{da.attrs.get('source', files[0].name)}; restricted to {y0}-{y1}"
        out = a.output_dir / f"{a.dst}_{var}_monthly_{y0}_{y1}.nc"
        sub.to_netcdf(out)
        print(f"Saved {out}: {sub.sizes['time']} months")


if __name__ == "__main__":
    main()
