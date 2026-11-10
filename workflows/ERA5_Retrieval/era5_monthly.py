"""
Generic ERA5 retrieval: monthly statistics from hourly ERA5 single-level data,
streamed from ECMWF's ARCO Zarr store (geo-chunked, time-series optimised).

Any variable of the store, any years from 1940, any region:
  --area N W S E                 a box, or
  --occurrences CSV [--buffer]   only the store tiles (1 x 1 degree) within
                                 --buffer degrees of the points in CSV
                                 (columns decimalLatitude, decimalLongitude;
                                 tab-separated, as GBIF SIMPLE_CSV).

Monthly statistics (hourly data, UTC days):
  mean            monthly mean of hourly values
  sum             monthly total (accumulated variables, e.g. tp)
  daily_min_mean  monthly mean of daily minimum   (instantaneous variables only)
  daily_max_mean  monthly mean of daily maximum   (instantaneous variables only)
  daily_max_max   monthly maximum of daily maximum (instantaneous variables only)
Accumulated variables (GRIB stepType "accum", e.g. tp) hold the amount for the
hour ending at their time stamp, so each value is assigned to the month of t - 1 h.

Output: one NetCDF per (variable, statistic) in --outdir,
  era5_<var>_<stat>_monthly_<start>_<end>.nc, dims (time, lat, lon), in the
store's native units (e.g. K, m). Points outside the fetched tiles are NaN.

Authentication: CDS API key from --credentials-file (JSON {"key": "..."});
without it, CDSAPI_KEY or the `key:` line of ~/.cdsapirc.
The store rate-limits per key, so requests are sent one at a time, paced,
and retried with back-off on 403/429/5xx.

Example:
  python era5_monthly.py --variables '{"t2m": ["mean"], "tp": ["sum"]}' \
      --years 2000 2001 --area 44 -10 36 4 --credentials-file cds_credentials.json
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import zarr
from fsspec.implementations.http import HTTPFileSystem

STORE_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-002/arco/"
    "reanalysis_era5_single_levels/sfc/geoChunked.zarr"
)
DAILY_STATS = {"daily_min_mean", "daily_max_mean", "daily_max_max"}
ALL_STATS = {"mean", "sum"} | DAILY_STATS


class ThrottledHTTP(HTTPFileSystem):
    """One request at a time, at least MIN_INTERVAL apart, with back-off on
    the store's rate-limit responses (403, ~2 min cool-down)."""
    MIN_INTERVAL = 0.5
    RETRY = {403, 429, 500, 502, 503}

    def __init__(self, *a, **kw):
        self._last = 0.0
        super().__init__(*a, **kw)

    async def _cat_file(self, url, start=None, end=None, **kw):
        for attempt in range(8):
            gap = self.MIN_INTERVAL - (time.monotonic() - self._last)
            if gap > 0:
                await asyncio.sleep(gap)
            try:
                r = await super()._cat_file(url, start, end, **kw)
                self._last = time.monotonic()
                return r
            except Exception as e:
                self._last = time.monotonic()
                if getattr(e, "status", None) in self.RETRY and attempt < 7:
                    await asyncio.sleep(30 * (2 ** attempt))
                    continue
                raise


def cds_api_key(credentials_file: Path | None) -> str:
    """CDS API key from a credentials JSON file {"key": "..."}; without one,
    from CDSAPI_KEY or the `key:` line of ~/.cdsapirc."""
    if credentials_file is not None:
        try:
            key = json.loads(credentials_file.read_text()).get("key", "")
        except (OSError, json.JSONDecodeError) as e:
            raise SystemExit(f"Cannot read CDS credentials file {credentials_file}: {e}")
        if not key:
            raise SystemExit(f'CDS credentials file {credentials_file} lacks "key"')
        return key.strip()
    key = os.environ.get("CDSAPI_KEY")
    if key:
        return key.strip()
    rc = Path(os.environ.get("CDSAPI_RC", Path.home() / ".cdsapirc"))
    if rc.exists():
        for line in rc.read_text().splitlines():
            if line.strip().startswith("key:"):
                return line.split(":", 1)[1].strip()
    raise SystemExit("No CDS API key: pass --credentials-file with {\"key\": \"...\"} "
                     "(key from your profile at https://cds.climate.copernicus.eu/).")


def open_store(key: str) -> xr.Dataset:
    zarr.config.set({"async.concurrency": 1})
    fs = ThrottledHTTP(asynchronous=True, headers={"Authorization": f"Bearer {key}"})
    return xr.open_zarr(zarr.storage.FsspecStore(fs=fs, path=STORE_URL),
                        consolidated=True, chunks=None)


def select_tiles(lat_axis, lon_axis, tile, area=None, points=None, buffer=1.0):
    """Store tiles (i, j) covering a box or the points +/- buffer degrees."""
    step = lat_axis[1] - lat_axis[0]
    def tile_range(axis, lo, hi, size):
        i0 = int(np.floor((lo - axis[0]) / step)) // size
        i1 = int(np.floor((hi - axis[0]) / step)) // size
        return max(i0, 0), min(i1, (len(axis) - 1) // size)
    tiles = set()
    if area is not None:
        n, w, s, e = area
        ia, ib = tile_range(lat_axis, s, n, tile[0])
        ja, jb = tile_range(lon_axis, w, e, tile[1])
        tiles = {(i, j) for i in range(ia, ib + 1) for j in range(ja, jb + 1)}
    else:
        for lat, lon in points:
            ia, ib = tile_range(lat_axis, lat - buffer, lat + buffer, tile[0])
            ja, jb = tile_range(lon_axis, lon - buffer, lon + buffer, tile[1])
            tiles |= {(i, j) for i in range(ia, ib + 1) for j in range(ja, jb + 1)}
    return sorted(tiles)


def run_starts(labels):
    return np.flatnonzero(np.r_[True, labels[1:] != labels[:-1]])


def main() -> None:
    p = argparse.ArgumentParser(description="Generic ERA5 monthly retrieval (ARCO Zarr)")
    p.add_argument("--variables", required=True,
                   help='JSON {variable: [statistics]}, e.g. \'{"t2m": ["mean"]}\'')
    p.add_argument("--years", nargs=2, type=int, required=True, metavar=("START", "END"))
    region = p.add_mutually_exclusive_group(required=True)
    region.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"))
    region.add_argument("--occurrences", help="CSV with decimalLatitude/decimalLongitude")
    p.add_argument("--buffer", type=float, default=1.0, help="degrees around occurrences")
    p.add_argument("--credentials-file", type=Path, help='JSON {"key": "<CDS API key>"}')
    p.add_argument("--output-dir", default="data/era5_monthly")
    a = p.parse_args()

    variables = json.loads(a.variables)
    start, end = a.years
    for var, stats in variables.items():
        bad = set(stats) - ALL_STATS
        if bad:
            raise SystemExit(f"{var}: unknown statistics {sorted(bad)}; choose from {sorted(ALL_STATS)}")

    ds = open_store(cds_api_key(a.credentials_file))
    missing = [v for v in variables if v not in ds]
    if missing:
        raise SystemExit(f"Not in the store: {missing}. Available: {sorted(ds.data_vars)}")
    lat_axis, lon_axis = ds["latitude"].values, ds["longitude"].values
    assert lat_axis[0] < lat_axis[-1] and lon_axis[0] < lon_axis[-1]
    times = pd.DatetimeIndex(ds["time"].values)
    tchunk, tlat, tlon = ds[next(iter(variables))].encoding["chunks"]
    if tchunk % 24 or times[0].hour != 0:
        raise SystemExit("Store time chunks are not aligned to UTC days")
    accum = {v: ds[v].attrs.get("GRIB_stepType") == "accum" for v in variables}
    for v, stats in variables.items():
        if accum[v] and set(stats) & DAILY_STATS:
            raise SystemExit(f"{v} is accumulated: use 'sum' or 'mean', not daily statistics")

    if a.area is not None:
        tiles = select_tiles(lat_axis, lon_axis, (tlat, tlon), area=a.area)
    else:
        occ = pd.read_csv(a.occurrences, sep="\t",
                          usecols=["decimalLatitude", "decimalLongitude"]).dropna()
        pts = np.unique(np.round(occ.values, 2), axis=0)
        tiles = select_tiles(lat_axis, lon_axis, (tlat, tlon), points=pts, buffer=a.buffer)
    ti, tj = np.array([t[0] for t in tiles]), np.array([t[1] for t in tiles])
    i_lo, i_hi = ti.min() * tlat, (ti.max() + 1) * tlat
    j_lo, j_hi = tj.min() * tlon, (tj.max() + 1) * tlon
    print(f"{len(tiles)} store tiles, box lat {lat_axis[i_lo]:.2f}..{lat_axis[i_hi - 1]:.2f}, "
          f"lon {lon_axis[j_lo]:.2f}..{lon_axis[j_hi - 1]:.2f}", flush=True)

    i0 = times.searchsorted(pd.Timestamp(f"{start}-01-01"))
    i1 = times.searchsorted(pd.Timestamp(f"{end + 1}-01-01"))
    if i1 >= len(times):
        raise SystemExit("Requested end year is beyond the store")
    if not (np.diff(times[i0:i1 + 1].values).astype("timedelta64[h]") == np.timedelta64(1, "h")).all():
        raise SystemExit("Hourly time axis has gaps in the requested period")

    months = pd.period_range(f"{start}-01", f"{end}-12", freq="M")
    n_m, ny, nx = len(months), i_hi - i_lo, j_hi - j_lo
    acc, cnt = {}, {}
    for v, stats in variables.items():
        for s in stats:
            fill = -np.inf if s == "daily_max_max" else 0.0
            acc[v, s] = np.full((n_m, ny, nx), fill)
            cnt[v, s] = np.zeros(n_m, dtype=np.int64)
    filled = np.zeros((ny, nx), dtype=bool)
    for i, j in tiles:
        filled[i * tlat - i_lo:(i + 1) * tlat - i_lo, j * tlon - j_lo:(j + 1) * tlon - j_lo] = True

    def month_index(ts):
        return (ts.year - start) * 12 + ts.month - 1

    k0, k1 = i0 // tchunk, i1 // tchunk
    t_start = time.monotonic()
    for k in range(k0, k1 + 1):
        for v, stats in variables.items():
            # instantaneous: hours [i0, i1); accumulated: hour-ending, (i0, i1]
            lo, hi = (i0 + 1, i1 + 1) if accum[v] else (i0, i1)
            a_, b_ = max(lo, k * tchunk), min(hi, (k + 1) * tchunk)
            if b_ <= a_:
                continue
            ts = times[a_:b_] - pd.Timedelta(hours=1) if accum[v] else times[a_:b_]
            mi_hr = month_index(ts)
            hr_starts = run_starts(mi_hr)
            mi_day = month_index(times[a_:b_:24]) if not accum[v] else None
            day_starts = run_starts(mi_day) if mi_day is not None else None
            for n, (i, j) in enumerate(tiles, 1):
                h = ds[v][a_:b_, i * tlat:(i + 1) * tlat, j * tlon:(j + 1) * tlon].values.astype(np.float64)
                ys = slice(i * tlat - i_lo, (i + 1) * tlat - i_lo)
                xs = slice(j * tlon - j_lo, (j + 1) * tlon - j_lo)
                if {"mean", "sum"} & set(stats):
                    s_hr = np.add.reduceat(h, hr_starts, axis=0)
                    for s in {"mean", "sum"} & set(stats):
                        acc[v, s][mi_hr[hr_starts], ys, xs] += s_hr
                if set(stats) & DAILY_STATS:
                    d = h.reshape(-1, 24, tlat, tlon)
                    if "daily_min_mean" in stats:
                        acc[v, "daily_min_mean"][mi_day[day_starts], ys, xs] += np.add.reduceat(d.min(1), day_starts, axis=0)
                    dmax = d.max(1)
                    if "daily_max_mean" in stats:
                        acc[v, "daily_max_mean"][mi_day[day_starts], ys, xs] += np.add.reduceat(dmax, day_starts, axis=0)
                    if "daily_max_max" in stats:
                        m = mi_day[day_starts]
                        acc[v, "daily_max_max"][m, ys, xs] = np.maximum(
                            acc[v, "daily_max_max"][m, ys, xs], np.maximum.reduceat(dmax, day_starts, axis=0))
                if n % 25 == 0 or n == len(tiles):
                    print(f"  {v} {times[a_]:%Y-%m}..{times[b_ - 1]:%Y-%m}: {n}/{len(tiles)} tiles "
                          f"({(time.monotonic() - t_start) / 60:.1f} min)", flush=True)
            hours = np.diff(np.r_[hr_starts, len(mi_hr)])
            for s in stats:
                if s in ("mean", "sum"):
                    cnt[v, s][mi_hr[hr_starts]] += hours
                else:
                    cnt[v, s][mi_day[day_starts]] += np.diff(np.r_[day_starts, len(mi_day)])

    ndays = months.days_in_month.values
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    coords = {"time": months.to_timestamp(how="start") + pd.Timedelta(days=14),
              "lat": lat_axis[i_lo:i_hi], "lon": lon_axis[j_lo:j_hi]}
    for (v, s), vals in acc.items():
        expected = ndays * 24 if s in ("mean", "sum") else ndays
        assert (cnt[v, s] == expected).all(), f"{v} {s}: incomplete months"
        if s in ("mean", "daily_min_mean", "daily_max_mean"):
            vals = vals / cnt[v, s][:, None, None]
        vals = vals.astype(np.float32)
        vals[:, ~filled] = np.nan
        da = xr.DataArray(vals, dims=("time", "lat", "lon"), coords=coords, name=v, attrs={
            "units": ds[v].attrs.get("units", ""),
            "long_name": f"{ds[v].attrs.get('long_name', v)}, monthly {s.replace('_', ' ')}",
            "statistic": s,
            "source": f"ERA5 hourly (reanalysis-era5-single-levels), ECMWF ARCO Zarr {STORE_URL}",
        })
        f = out / f"era5_{v}_{s}_monthly_{start}_{end}.nc"
        da.to_netcdf(f)
        print(f"Saved {f} ({f.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
