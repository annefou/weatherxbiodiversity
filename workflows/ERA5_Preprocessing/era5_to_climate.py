"""
ERA5 preprocessing for the Soroye et al. (2020) climate step.

Turns the generic monthly ERA5 statistics from ERA5_Retrieval into the four
monthly variables the exposure indices of Soroye et al. (2020) use:

  tmp  monthly mean temperature            <- t2m mean            (K -> degC)
  tmn  monthly mean of daily minimum       <- t2m daily_min_mean  (K -> degC)
  tmx  monthly mean of daily maximum       <- t2m daily_max_mean  (K -> degC)
  pre  monthly total precipitation         <- tp sum              (m -> mm)

Inputs, either
  the four files explicitly (as handed over by the ERA5_Retrieval CWL tool):
    --t2m-mean F --t2m-daily-min-mean F --t2m-daily-max-mean F --tp-sum F
  or a directory with the retrieval's file names:
    --input-dir D --years START END

Output: <output-dir>/era5_{tmp,tmn,tmx,pre}_monthly_<start>_<end>.nc,
dims (time, lat, lon); <start>/<end> are the first and last year in the data.
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
LONG_NAME = {
    "tmp": "monthly mean 2m temperature",
    "tmn": "monthly mean of daily minimum 2m temperature",
    "tmx": "monthly mean of daily maximum 2m temperature",
    "pre": "monthly total precipitation",
}


def main() -> None:
    p = argparse.ArgumentParser(description="ERA5 monthly statistics -> tmp/tmn/tmx/pre")
    p.add_argument("--t2m-mean", type=Path, help="era5_t2m_mean_monthly_*.nc")
    p.add_argument("--t2m-daily-min-mean", type=Path, help="era5_t2m_daily_min_mean_monthly_*.nc")
    p.add_argument("--t2m-daily-max-mean", type=Path, help="era5_t2m_daily_max_mean_monthly_*.nc")
    p.add_argument("--tp-sum", type=Path, help="era5_tp_sum_monthly_*.nc")
    p.add_argument("--input-dir", type=Path, help="alternative: directory with the four files")
    p.add_argument("--years", nargs=2, type=int, metavar=("START", "END"),
                   help="with --input-dir: years in the file names")
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()

    explicit = {"tmp": a.t2m_mean, "tmn": a.t2m_daily_min_mean,
                "tmx": a.t2m_daily_max_mean, "pre": a.tp_sum}
    if all(explicit.values()):
        sources = explicit
    elif a.input_dir and a.years and not any(explicit.values()):
        start, end = a.years
        sources = {out: a.input_dir / f"era5_{var}_{stat}_monthly_{start}_{end}.nc"
                   for out, (var, stat, *_) in MAPPING.items()}
    else:
        p.error("give all four files (--t2m-mean, --t2m-daily-min-mean, "
                "--t2m-daily-max-mean, --tp-sum), or --input-dir with --years")

    data = {out: xr.open_dataarray(src) for out, src in sources.items()}
    times = {out: tuple(da["time"].values) for out, da in data.items()}
    if len(set(times.values())) != 1:
        raise SystemExit("The four input files do not cover the same months")
    years = data["tmp"]["time"].dt.year.values
    start, end = int(years.min()), int(years.max())
    a.output_dir.mkdir(parents=True, exist_ok=True)

    for out_var, (var, stat, offset, scale, units) in MAPPING.items():
        da = data[out_var]
        out = ((da + offset) * scale).astype("float32").rename(out_var)
        out.attrs = {
            "units": units,
            "long_name": LONG_NAME[out_var],
            "source": f"{sources[out_var].name}: {da.attrs.get('source', '')}",
            "definition": "monthly climate variable of the Soroye et al. (2020) exposure indices",
        }
        f = a.output_dir / f"era5_{out_var}_monthly_{start}_{end}.nc"
        out.to_netcdf(f)
        print(f"Saved {f}: {out_var} <- {var} {stat}, "
              f"range {float(out.min()):.1f}..{float(out.max()):.1f} {units}")


if __name__ == "__main__":
    main()
