"""
Stream ERA5 2 m temperature for Iberia directly from ECMWF's ARCO Zarr
store and compute the monthly maximum of daily maximum temperature.

This is an alternative to `download_era5_daily.py` (CDS queue, ~27 h):
nothing is downloaded as files from CDS. Instead, only the Zarr chunks
covering the Iberian box are read from the geo-chunked (time-series
optimised) ERA5 single-levels store hosted by ECMWF:

    https://arco.datastores.ecmwf.int/cadl-arco-geo-002/arco/
        reanalysis_era5_single_levels/sfc/geoChunked.zarr

Daily maximum is computed from hourly `t2m` over UTC days, which matches
the CDS `derived-era5-single-levels-daily-statistics` request used in
`download_era5_daily.py` (daily_maximum, 1_hourly, utc+00:00).

Authentication uses your CDS API key (the `key:` in ~/.cdsapirc), sent as
a Bearer token. Set CDSAPI_KEY to override. The key is never printed.

The store is chunked (67584 h, 4 lat, 4 lon). We iterate over its time
chunks so every chunk is fetched exactly once; per-chunk daily maxima are
cached in data/era5_arco_daily/ so an interrupted run resumes.

Usage:
    python stream_era5_arco.py                     # 1959-2024
    python stream_era5_arco.py --start 2020 --end 2020
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

STORE_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-002/arco/"
    "reanalysis_era5_single_levels/sfc/geoChunked.zarr"
)
# [N, W, S, E] — same box as download_era5_daily.py
AREA = [44, -10, 36, 4]


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


def open_store() -> xr.Dataset:
    return xr.open_zarr(
        STORE_URL,
        consolidated=True,
        chunks=None,  # lazy indexing; we load explicit blocks ourselves
        storage_options={
            "headers": {"Authorization": f"Bearer {cds_api_key()}"}
        },
    )


def iberia(da: xr.DataArray) -> xr.DataArray:
    """Cut the AREA box. The geo-chunked store has increasing latitudes and
    longitudes in -180..180 (despite a `stored_direction: decreasing`
    attribute), but both orders and 0..360 longitudes are handled."""
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


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--start", type=int, default=1959)
    p.add_argument("--end", type=int, default=2024)
    p.add_argument("--out", default="data/era5_iberia_monthly_tmax_arco.nc")
    p.add_argument("--cache", default="data/era5_arco_daily")
    args = p.parse_args()

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    ds = open_store()
    t2m = ds["t2m"]
    tchunk = t2m.encoding["chunks"][0]  # 67584 h = 2816 days
    times = pd.DatetimeIndex(ds["time"].values)

    i0 = times.searchsorted(pd.Timestamp(f"{args.start}-01-01"))
    i1 = times.searchsorted(pd.Timestamp(f"{args.end + 1}-01-01"))
    if i1 <= i0:
        raise SystemExit(f"No data for {args.start}-{args.end}")

    # Daily max by reshaping (day, 24 h, ...) needs a complete hourly axis
    # starting at 00 UTC.
    step = np.diff(times[i0:i1].values).astype("timedelta64[h]")
    if not (step == np.timedelta64(1, "h")).all():
        raise SystemExit("Hourly time axis has gaps in the requested period")
    if times[i0].hour != 0 or (i1 - i0) % 24:
        raise SystemExit("Requested period is not aligned to whole UTC days")
    if tchunk % 24 or times[0].hour != 0:
        raise SystemExit("Store time chunks are not aligned to UTC days")

    region = iberia(t2m)
    print(
        f"ERA5 t2m {times[i0]:%Y-%m-%d} .. {times[i1 - 1]:%Y-%m-%d}, "
        f"{region.sizes['latitude']} x {region.sizes['longitude']} grid"
    )

    daily_parts = []
    first_chunk, last_chunk = i0 // tchunk, (i1 - 1) // tchunk
    for k in range(first_chunk, last_chunk + 1):
        a, b = max(i0, k * tchunk), min(i1, (k + 1) * tchunk)
        part = cache / f"tmax_daily_{times[a]:%Y%m%d}_{times[b - 1]:%Y%m%d}.nc"
        label = f"  chunk {k - first_chunk + 1}/{last_chunk - first_chunk + 1} "
        label += f"{times[a]:%Y-%m-%d}..{times[b - 1]:%Y-%m-%d}"
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

    daily = xr.concat(
        [xr.open_dataarray(f) for f in daily_parts], dim="time"
    ).load() - 273.15

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

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_netcdf(out)
    print(
        f"Saved {out} ({out.stat().st_size / 1e6:.1f} MB): "
        f"{monthly.sizes['time']} months, "
        f"Jul mean {float(monthly.sel(time=monthly.time.dt.month == 7).mean()):.1f} °C, "
        f"Jan mean {float(monthly.sel(time=monthly.time.dt.month == 1).mean()):.1f} °C"
    )


if __name__ == "__main__":
    main()
