# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Step 2: Download ERA5 Daily Maximum Temperature from CDS
#
# This notebook downloads ERA5 daily maximum 2 m temperature for the
# Iberian Peninsula from the Copernicus Climate Data Store (CDS).
#
# ## Why daily max, not monthly mean?
#
# [Soroye et al. (2020)](https://doi.org/10.1126/science.aax8591) used
# CRU TS monthly mean of daily maximum temperature. To replicate this,
# we need the daily maximum first, then aggregate to monthly statistics.
#
# The CDS product
# [`derived-era5-single-levels-daily-statistics`](https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics)
# provides server-side daily aggregation of hourly ERA5 data, so we
# download daily max T directly — no need to process hourly data ourselves.
#
# ## Data specification
#
# | Parameter | Value |
# |-----------|-------|
# | Product | `derived-era5-single-levels-daily-statistics` |
# | Variable | 2 m temperature, daily maximum |
# | Region | Iberian Peninsula (36–44°N, 10°W–4°E) |
# | Period | 1959–2024 |
# | Resolution | 0.25° (~25 km) |
# | Format | NetCDF |
#
# ## Prerequisites
#
# - A free CDS account: https://cds.climate.copernicus.eu/
# - CDS API key configured in `~/.cdsapirc`

# %%
import cdsapi
import xarray as xr
import os
from pathlib import Path

# %% [markdown]
# ## Configuration

# %%
OUTDIR = Path("../data/era5_daily_max")
OUTDIR.mkdir(parents=True, exist_ok=True)

AREA = [44, -10, 36, 4]  # [N, W, S, E]
YEARS = range(1959, 2025)

client = cdsapi.Client()

# %% [markdown]
# ## 1. Download daily max temperature by decade
#
# We split into decade-sized requests to stay within CDS limits.
# Each request takes ~2–5 minutes to process server-side.

# %%
decade_ranges = [
    (1959, 1969), (1970, 1979), (1980, 1989), (1990, 1999),
    (2000, 2009), (2010, 2019), (2020, 2024),
]

for start_yr, end_yr in decade_ranges:
    outfile = OUTDIR / f"era5_tmax_daily_{start_yr}_{end_yr}.nc"

    if outfile.exists():
        print(f"  {start_yr}–{end_yr}: already downloaded ({outfile.stat().st_size / 1e6:.1f} MB)")
        continue

    print(f"  {start_yr}–{end_yr}: requesting from CDS...")

    try:
        client.retrieve(
            "derived-era5-single-levels-daily-statistics",
            {
                "variable": ["2m_temperature"],
                "year": [str(y) for y in range(start_yr, end_yr + 1)],
                "month": [f"{m:02d}" for m in range(1, 13)],
                "day": [f"{d:02d}" for d in range(1, 32)],
                "daily_statistic": "daily_maximum",
                "time_zone": "utc+00:00",
                "frequency": "1_hourly",
                "data_format": "netcdf",
                "area": AREA,
            },
            str(outfile),
        )
        print(f"    Done: {outfile.stat().st_size / 1e6:.1f} MB")
    except Exception as e:
        print(f"    Failed: {e}")

# %% [markdown]
# ## 2. Combine and compute monthly max
#
# From daily max T, we compute the monthly maximum — the hottest day
# in each month at each grid cell. This is the closest equivalent to
# the CRU TS field used by Soroye et al.

# %%
import glob

files = sorted(OUTDIR.glob("era5_tmax_daily_*.nc"))
print(f"Found {len(files)} files")

if files:
    datasets = []
    for f in files:
        ds = xr.open_dataset(f)
        # The time dimension may be called 'valid_time' or 'time'
        time_dim = "valid_time" if "valid_time" in ds.dims else "time"
        datasets.append(ds)
        print(f"  {f.name}: {ds.sizes[time_dim]} days")

    combined = xr.concat(datasets, dim=time_dim).sortby(time_dim)

    # Find temperature variable
    t_var = [v for v in combined.data_vars
             if "temperature" in v.lower() or "t2m" in v.lower()][0]
    t2m_daily = combined[t_var]

    # Convert K → °C if needed
    if float(t2m_daily.isel({time_dim: 0}).mean()) > 200:
        t2m_daily = t2m_daily - 273.15

    print(f"\nDaily max T: {t2m_daily.sizes[time_dim]} days, "
          f"{t2m_daily.sizes['latitude']} × {t2m_daily.sizes['longitude']} grid")
    print(f"Range: {float(t2m_daily.min()):.1f} to {float(t2m_daily.max()):.1f} °C")

    # Monthly max of daily max
    monthly_tmax = t2m_daily.resample({time_dim: "1ME"}).max()
    monthly_tmax.name = "monthly_tmax"
    monthly_tmax.attrs = {
        "units": "degC",
        "long_name": "Monthly maximum of daily maximum 2m temperature",
        "source": "ERA5 derived-era5-single-levels-daily-statistics via CDS",
        "region": "Iberian Peninsula (36-44N, 10W-4E)",
        "original_variable": "2m_temperature",
        "aggregation": "monthly max of daily max (hourly basis)",
    }

    outfile = Path("../data/era5_iberia_monthly_tmax.nc")
    monthly_tmax.to_netcdf(outfile)
    print(f"\nSaved monthly max: {outfile} ({outfile.stat().st_size / 1e6:.1f} MB)")

    # Summary
    print(f"\nMonthly max temperature summary:")
    print(f"  Time: {str(monthly_tmax[time_dim].values[0])[:10]} to "
          f"{str(monthly_tmax[time_dim].values[-1])[:10]}")
    print(f"  Months: {monthly_tmax.sizes[time_dim]}")
    print(f"  Jul mean max: {float(monthly_tmax.sel({time_dim: monthly_tmax[time_dim].dt.month == 7}).mean()):.1f} °C")
    print(f"  Jan mean max: {float(monthly_tmax.sel({time_dim: monthly_tmax[time_dim].dt.month == 1}).mean()):.1f} °C")
else:
    print("No daily max files found. Run the download cells first.")
    print("If CDS daily stats product is unavailable, fall back to monthly means:")
    print("  See data/era5_iberia_monthly_t2m_combined.nc (already downloaded)")
