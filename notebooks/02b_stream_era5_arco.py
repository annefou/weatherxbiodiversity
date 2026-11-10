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
# # Step 2b: Stream ERA5 daily maximum temperature from ECMWF's ARCO Zarr store
#
# A faster alternative to `02_download_era5.py` and `../download_era5_daily.py`,
# which queue CDS requests and take about 27 h for 1959–2024. Here, nothing is
# requested from CDS: only the Zarr chunks covering the Iberian box are read
# from the geo-chunked (time-series optimised) ERA5 single-levels store hosted
# by ECMWF. The full period takes about a minute.
#
# The output is the same field as `02_download_era5.py`: the **monthly maximum
# of daily maximum** 2 m temperature. Daily maximum is computed from hourly
# `t2m` over UTC days, which matches the CDS
# `derived-era5-single-levels-daily-statistics` request (`daily_maximum`,
# `1_hourly`, `utc+00:00`). For 2020 the two agree to within 0.00024 K.
#
# ## Data specification
#
# | Parameter | Value |
# |-----------|-------|
# | Store | `arco.datastores.ecmwf.int/cadl-arco-geo-002/.../sfc/geoChunked.zarr` |
# | Variable | `t2m`, hourly, from 1940 |
# | Region | Iberian Peninsula (36–44°N, 10°W–4°E) |
# | Period | 1959–2024 |
# | Resolution | 0.25° (~25 km) |
#
# ## Prerequisites
#
# - Your CDS API key (the `key:` line in `~/.cdsapirc`, from your profile at
#   https://cds.climate.copernicus.eu/). Set `CDSAPI_KEY` to override. The key
#   is sent as a Bearer token and never printed.
#
# Run as a notebook (`jupytext --to notebook`) or as a script
# (`python 02b_stream_era5_arco.py`). `ERA5_START` / `ERA5_END` environment
# variables override the period.

# %%
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

# %% [markdown]
# ## Configuration

# %%
DATA = Path("../data") if Path("../data").exists() else Path("data")

STORE_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-002/arco/"
    "reanalysis_era5_single_levels/sfc/geoChunked.zarr"
)
AREA = [44, -10, 36, 4]  # [N, W, S, E] — same box as 02_download_era5.py
START = int(os.environ.get("ERA5_START", 1959))
END = int(os.environ.get("ERA5_END", 2024))

OUTFILE = DATA / "era5_iberia_monthly_tmax_arco.nc"
CACHE = DATA / "era5_arco_daily"  # per-chunk daily maxima, so a rerun resumes
CACHE.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ## 1. Open the store
#
# Opening is lazy: only the metadata is read. The CDS key comes from
# `CDSAPI_KEY` or `~/.cdsapirc`.

# %%
def cds_api_key() -> str:
    key = os.environ.get("CDSAPI_KEY")
    if key:
        return key.strip()
    rc = Path(os.environ.get("CDSAPI_RC", Path.home() / ".cdsapirc"))
    if rc.exists():
        for line in rc.read_text().splitlines():
            if line.strip().startswith("key:"):
                return line.split(":", 1)[1].strip()
    raise SystemExit(
        "No CDS API key found. Set CDSAPI_KEY or add 'key: <your key>' to "
        "~/.cdsapirc (get it from your profile at "
        "https://cds.climate.copernicus.eu/)."
    )


ds = xr.open_zarr(
    STORE_URL,
    consolidated=True,
    chunks=None,  # lazy indexing; explicit blocks are loaded below
    storage_options={"headers": {"Authorization": f"Bearer {cds_api_key()}"}},
)
t2m = ds["t2m"]
tchunk = t2m.encoding["chunks"][0]  # 67584 h = 2816 days
times = pd.DatetimeIndex(ds["time"].values)
print(f"t2m {dict(t2m.sizes)}, chunks {t2m.encoding['chunks']}, "
      f"{times[0]:%Y-%m-%d} .. {times[-1]:%Y-%m-%d}")

# %% [markdown]
# ## 2. Select Iberia and the period
#
# The store's latitudes increase and its longitudes run from −180 to 180,
# despite a `stored_direction: decreasing` attribute on latitude. Both
# orders, and 0..360 longitudes, are handled.

# %%
def iberia(da: xr.DataArray) -> xr.DataArray:
    north, west, south, east = AREA
    lat = da.latitude.values
    lat_slice = slice(south, north) if lat[0] < lat[-1] else slice(north, south)
    da = da.sel(latitude=lat_slice)
    if da.longitude.values.min() < 0:
        return da.sel(longitude=slice(west, east))
    west_part = da.sel(longitude=slice(west % 360, 360))
    east_part = da.sel(longitude=slice(0, east))
    west_part = west_part.assign_coords(longitude=west_part.longitude - 360)
    return xr.concat([west_part, east_part], dim="longitude")


region = iberia(t2m)

i0 = times.searchsorted(pd.Timestamp(f"{START}-01-01"))
i1 = times.searchsorted(pd.Timestamp(f"{END + 1}-01-01"))
if i1 <= i0:
    raise SystemExit(f"No data for {START}-{END}")

# Daily max by reshaping (day, 24 h, ...) needs a complete hourly axis
# starting at 00 UTC.
step = np.diff(times[i0:i1].values).astype("timedelta64[h]")
if not (step == np.timedelta64(1, "h")).all():
    raise SystemExit("Hourly time axis has gaps in the requested period")
if times[i0].hour != 0 or (i1 - i0) % 24:
    raise SystemExit("Requested period is not aligned to whole UTC days")
if tchunk % 24 or times[0].hour != 0:
    raise SystemExit("Store time chunks are not aligned to UTC days")

print(f"ERA5 t2m {times[i0]:%Y-%m-%d} .. {times[i1 - 1]:%Y-%m-%d}, "
      f"{region.sizes['latitude']} x {region.sizes['longitude']} grid")

# %% [markdown]
# ## 3. Daily maximum, one storage time chunk at a time
#
# Iterating over the store's own time chunks fetches every chunk exactly once.
# Each chunk's daily maxima are cached, so an interrupted run resumes.

# %%
daily_parts = []
first_chunk, last_chunk = i0 // tchunk, (i1 - 1) // tchunk
for k in range(first_chunk, last_chunk + 1):
    a, b = max(i0, k * tchunk), min(i1, (k + 1) * tchunk)
    part = CACHE / f"tmax_daily_{times[a]:%Y%m%d}_{times[b - 1]:%Y%m%d}.nc"
    label = (f"  chunk {k - first_chunk + 1}/{last_chunk - first_chunk + 1} "
             f"{times[a]:%Y-%m-%d}..{times[b - 1]:%Y-%m-%d}")
    if part.exists():
        print(f"{label}: cached")
    else:
        print(f"{label}: streaming...", end=" ", flush=True)
        hourly = region.isel(time=slice(a, b)).load()
        vals = hourly.values.reshape(-1, 24, *hourly.shape[1:]).max(axis=1)
        daily = xr.DataArray(
            vals,
            dims=("time", "latitude", "longitude"),
            coords={
                "time": hourly.time.values[::24],
                "latitude": hourly.latitude.values,
                "longitude": hourly.longitude.values,
            },
            name="tmax_daily",
            attrs={"units": "K"},
        )
        tmp = part.with_suffix(".nc.tmp")
        daily.to_netcdf(tmp)
        tmp.rename(part)
        print(f"done ({daily.sizes['time']} days)")
    daily_parts.append(part)

# %% [markdown]
# ## 4. Monthly maximum of daily maximum
#
# The hottest day in each month at each grid cell, in °C, as in
# `02_download_era5.py`.

# %%
daily = xr.concat([xr.open_dataarray(f) for f in daily_parts], dim="time").load() - 273.15

monthly = daily.resample(time="1ME").max()
monthly.name = "monthly_tmax"
monthly.attrs = {
    "units": "degC",
    "long_name": "Monthly maximum of daily maximum 2m temperature",
    "source": f"ERA5 reanalysis-era5-single-levels t2m, ECMWF ARCO Zarr {STORE_URL}",
    "region": "Iberian Peninsula (36-44N, 10W-4E)",
    "original_variable": "2m_temperature",
    "aggregation": "monthly max of daily max (hourly basis, UTC days)",
}

OUTFILE.parent.mkdir(parents=True, exist_ok=True)
monthly.to_netcdf(OUTFILE)
print(
    f"Saved {OUTFILE} ({OUTFILE.stat().st_size / 1e6:.1f} MB): "
    f"{monthly.sizes['time']} months, "
    f"Jul mean {float(monthly.sel(time=monthly.time.dt.month == 7).mean()):.1f} °C, "
    f"Jan mean {float(monthly.sel(time=monthly.time.dt.month == 1).mean()):.1f} °C"
)
