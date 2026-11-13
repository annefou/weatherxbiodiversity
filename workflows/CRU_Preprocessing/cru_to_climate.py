"""
CRU TS 3.24.01 -> common climate input format.

Joins the decadal files from CRU_Retrieval into one monthly file per variable,
as the Analysis reads them (same layout as ERA5_Preprocessing):

  <output-dir>/cru_{tmp,tmn,tmx,pre}_monthly_<start>_<end>.nc
  dims (time, lat, lon); units degC (tmp, tmn, tmx), mm (pre)

CRU TS already holds the variables of Soroye et al. (2020): monthly mean (tmp),
mean daily minimum (tmn) and maximum (tmx) temperature in degrees Celsius, and
monthly precipitation (pre) in mm; no conversion is needed. Decades absent from
the input (e.g. 1981-1990 in Soroye et al.'s deposit) stay absent.

  python cru_to_climate.py --input-dir data/cru --output-dir data/climate/cru
"""
from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

UNITS = {"tmp": "degC", "tmn": "degC", "tmx": "degC", "pre": "mm"}
LONG_NAME = {
    "tmp": "monthly mean 2m temperature",
    "tmn": "monthly mean of daily minimum 2m temperature",
    "tmx": "monthly mean of daily maximum 2m temperature",
    "pre": "monthly total precipitation",
}


def main() -> None:
    p = argparse.ArgumentParser(description="CRU TS decadal files -> cru_<var>_monthly_<start>_<end>.nc")
    p.add_argument("--input-dir", type=Path, required=True, help="cropped files from CRU_Retrieval")
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    for var, units in UNITS.items():
        files = sorted(a.input_dir.glob(f"cru_ts3.24.01.*.{var}.dat.nc"))
        if not files:
            raise SystemExit(f"No CRU files for {var} in {a.input_dir}")
        da = xr.concat([xr.open_dataarray(f) for f in files], dim="time").sortby("time")
        years = da["time"].dt.year.values
        start, end = int(years.min()), int(years.max())
        out = da.astype("float32").rename(var)
        out.attrs = {"units": units, "long_name": LONG_NAME[var],
                     "source": "CRU TS 3.24.01 (University of East Anglia), decades: "
                               + ", ".join(f.name.split(".")[2] + "-" + f.name.split(".")[3] for f in files)}
        f = a.output_dir / f"cru_{var}_monthly_{start}_{end}.nc"
        out.to_netcdf(f)
        print(f"Saved {f}: {len(files)} decadal files, {out.sizes['time']} months, "
              f"range {float(out.min()):.1f}..{float(out.max()):.1f} {units}")


if __name__ == "__main__":
    main()
