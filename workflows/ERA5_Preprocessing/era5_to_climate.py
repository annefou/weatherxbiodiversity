"""
ERA5 preprocessing for the Soroye et al. (2020) climate step.

Turns the generic monthly ERA5 statistics from ERA5_Retrieval into the four
monthly variables the exposure indices use, with CRU TS 3.24.01 definitions:

  tmp  monthly mean temperature            <- t2m mean            (K -> degC)
  tmn  monthly mean of daily minimum       <- t2m daily_min_mean  (K -> degC)
  tmx  monthly mean of daily maximum       <- t2m daily_max_mean  (K -> degC)
  pre  monthly total precipitation         <- tp sum              (m -> mm)

Output: <output-dir>/era5_{tmp,tmn,tmx,pre}_monthly_<start>_<end>.nc,
dims (time, lat, lon), read by soroye_port/04_climate_tei_pei.py with
CLIMATE_SOURCE=era5.
"""

import argparse
from pathlib import Path

import xarray as xr

MAPPING = {   # output variable: (ERA5 variable, statistic, offset, scale, units)
    "tmp": ("t2m", "mean", -273.15, 1.0, "degC"),
    "tmn": ("t2m", "daily_min_mean", -273.15, 1.0, "degC"),
    "tmx": ("t2m", "daily_max_mean", -273.15, 1.0, "degC"),
    "pre": ("tp", "sum", 0.0, 1000.0, "mm"),
}


def main() -> None:
    p = argparse.ArgumentParser(description="ERA5 monthly statistics -> tmp/tmn/tmx/pre")
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--years", nargs=2, type=int, required=True, metavar=("START", "END"))
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    start, end = a.years
    a.output_dir.mkdir(parents=True, exist_ok=True)

    for out_var, (var, stat, offset, scale, units) in MAPPING.items():
        src = a.input_dir / f"era5_{var}_{stat}_monthly_{start}_{end}.nc"
        da = xr.open_dataarray(src)
        out = ((da + offset) * scale).astype("float32").rename(out_var)
        out.attrs = {
            "units": units,
            "long_name": {"tmp": "monthly mean 2m temperature",
                          "tmn": "monthly mean of daily minimum 2m temperature",
                          "tmx": "monthly mean of daily maximum 2m temperature",
                          "pre": "monthly total precipitation"}[out_var],
            "source": f"{src.name}: {da.attrs.get('source', '')}",
            "definition": "CRU TS 3.24.01 equivalent",
        }
        f = a.output_dir / f"era5_{out_var}_monthly_{start}_{end}.nc"
        out.to_netcdf(f)
        print(f"Saved {f}: {out_var} <- {var} {stat}, "
              f"range {float(out.min()):.1f}..{float(out.max()):.1f} {units}")


if __name__ == "__main__":
    main()
