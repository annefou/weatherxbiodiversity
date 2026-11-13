"""
Generic ERA5 retrieval: daily or monthly statistics from hourly ERA5
single-level data, streamed from ECMWF's ARCO Zarr store (geo-chunked,
time-series optimised). Only the requested statistics are saved; the hourly
data are never written to disk.

Source: always the hourly store STORE_URL (reanalysis-era5-single-levels,
surface variables). ARCO offers no separate daily or monthly product, so both
are computed here from the hourly values; --frequency only changes that
aggregation. They reproduce the CDS products derived-era5-single-levels-daily-
statistics (daily min / max / mean / sum, UTC, from 1-hourly data) and
reanalysis-era5-single-levels-monthly-means (monthly averaged reanalysis).

Any variable of the store, any years from 1940, any region:
  --area N W S E                 a box; repeat --area for several boxes
                                 (e.g. mainland + islands), or
  --occurrences CSV [--buffer]   only the store tiles (1 x 1 degree) within
                                 --buffer degrees of the points in CSV
                                 (columns decimalLatitude, decimalLongitude;
                                 tab-separated, as GBIF SIMPLE_CSV).

--frequency monthly (default), statistics from hourly data over UTC days:
  mean            monthly mean of hourly values
  sum             monthly total (accumulated variables, e.g. tp)
  daily_min_mean  monthly mean of daily minimum    (instantaneous variables)
  daily_max_mean  monthly mean of daily maximum    (instantaneous variables)
  daily_max_max   monthly maximum of daily maximum (instantaneous variables)
  -> <output-dir>/era5_<var>_<stat>_monthly_<start>_<end>.nc

--frequency daily, per UTC day:
  mean, sum, min, max of the hourly values
  -> <output-dir>/era5_<var>_<stat>_daily_<year>.nc   (one file per year)

Accumulated variables (GRIB stepType "accum", e.g. tp, ssrd) hold the amount
for the hour ending at their time stamp, so each value is assigned to the day
or month of t - 1 h. Output dims (time, lat, lon), in the store's native units
(e.g. K, m, J m**-2). Points outside the fetched tiles are NaN.

Authentication: CDS API key from --credentials-file (JSON {"key": "..."});
without it, CDSAPI_KEY or the `key:` line of ~/.cdsapirc.
The store rate-limits per key, so requests are sent one at a time, paced,
and retried with back-off on 403/429/5xx.

Examples:
  python era5_retrieve.py --variables '{"t2m": ["mean"], "tp": ["sum"]}' \
      --years 2000 2001 --area 44 -10 36 4 --credentials-file credentials.json
  python era5_retrieve.py --frequency daily --variables '{"t2m": ["min", "max"]}' \
      --years 2020 2020 --area 44 -10 36 4 --credentials-file credentials.json
"""

import argparse
import asyncio
import calendar
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
MONTHLY_DAILY_STATS = {"daily_min_mean", "daily_max_mean", "daily_max_max"}
STATS = {
    "monthly": {"mean", "sum"} | MONTHLY_DAILY_STATS,
    "daily": {"mean", "sum", "min", "max"},
}
REDUCE = {"sum": np.add, "mean": np.add, "min": np.minimum, "max": np.maximum,
          "daily_max_max": np.maximum}
FILL = {"min": np.inf, "max": -np.inf, "daily_max_max": -np.inf}


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


def select_tiles(lat_axis, lon_axis, tile, areas=None, points=None, buffer=1.0):
    """Store tiles (i, j) covering one or more boxes, or the points +/- buffer degrees."""
    step = lat_axis[1] - lat_axis[0]
    def tile_range(axis, lo, hi, size):
        i0 = int(np.floor((lo - axis[0]) / step)) // size
        i1 = int(np.floor((hi - axis[0]) / step)) // size
        return max(i0, 0), min(i1, (len(axis) - 1) // size)
    tiles = set()
    if areas is not None:
        for n, w, s, e in areas:
            ia, ib = tile_range(lat_axis, s, n, tile[0])
            ja, jb = tile_range(lon_axis, w, e, tile[1])
            tiles |= {(i, j) for i in range(ia, ib + 1) for j in range(ja, jb + 1)}
    else:
        for lat, lon in points:
            ia, ib = tile_range(lat_axis, lat - buffer, lat + buffer, tile[0])
            ja, jb = tile_range(lon_axis, lon - buffer, lon + buffer, tile[1])
            tiles |= {(i, j) for i in range(ia, ib + 1) for j in range(ja, jb + 1)}
    return sorted(tiles)


def run_starts(labels):
    return np.flatnonzero(np.r_[True, labels[1:] != labels[:-1]])


def main() -> None:
    p = argparse.ArgumentParser(description="Generic ERA5 retrieval (ARCO Zarr)")
    p.add_argument("--variables", required=True,
                   help='JSON {variable: [statistics]}, e.g. \'{"t2m": ["mean"]}\'')
    p.add_argument("--frequency", choices=("monthly", "daily"), default="monthly")
    p.add_argument("--years", nargs=2, type=int, required=True, metavar=("START", "END"))
    region = p.add_mutually_exclusive_group(required=True)
    region.add_argument("--area", nargs=4, type=float, action="append",
                        metavar=("N", "W", "S", "E"), help="box; repeat for several boxes")
    region.add_argument("--occurrences", help="CSV with decimalLatitude/decimalLongitude")
    p.add_argument("--buffer", type=float, default=1.0, help="degrees around occurrences")
    p.add_argument("--credentials-file", type=Path, help='JSON {"key": "<CDS API key>"}')
    p.add_argument("--output-dir", default="results")
    a = p.parse_args()

    freq = a.frequency
    variables = json.loads(a.variables)
    start, end = a.years
    for var, stats in variables.items():
        bad = set(stats) - STATS[freq]
        if bad:
            raise SystemExit(f"{var}: statistics {sorted(bad)} not available for {freq} output; "
                             f"choose from {sorted(STATS[freq])}")

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
        if accum[v] and set(stats) & MONTHLY_DAILY_STATS:
            raise SystemExit(f"{v} is accumulated: use 'sum' or 'mean' for monthly output")

    if a.area is not None:
        tiles = select_tiles(lat_axis, lon_axis, (tlat, tlon), areas=a.area)
    else:
        occ = pd.read_csv(a.occurrences, sep="\t",
                          usecols=["decimalLatitude", "decimalLongitude"]).dropna()
        pts = np.unique(np.round(occ.values, 2), axis=0)
        tiles = select_tiles(lat_axis, lon_axis, (tlat, tlon), points=pts, buffer=a.buffer)
    ti, tj = np.array([t[0] for t in tiles]), np.array([t[1] for t in tiles])
    i_lo, i_hi = ti.min() * tlat, (ti.max() + 1) * tlat
    j_lo, j_hi = tj.min() * tlon, (tj.max() + 1) * tlon
    ny, nx = i_hi - i_lo, j_hi - j_lo
    print(f"{len(tiles)} store tiles, box lat {lat_axis[i_lo]:.2f}..{lat_axis[i_hi - 1]:.2f}, "
          f"lon {lon_axis[j_lo]:.2f}..{lon_axis[j_hi - 1]:.2f}; {freq} output", flush=True)

    i0 = times.searchsorted(pd.Timestamp(f"{start}-01-01"))
    i1 = times.searchsorted(pd.Timestamp(f"{end + 1}-01-01"))
    if i1 >= len(times):
        raise SystemExit("Requested end year is beyond the store")
    if not (np.diff(times[i0:i1 + 1].values).astype("timedelta64[h]") == np.timedelta64(1, "h")).all():
        raise SystemExit("Hourly time axis has gaps in the requested period")

    filled = np.zeros((ny, nx), dtype=bool)
    for i, j in tiles:
        filled[i * tlat - i_lo:(i + 1) * tlat - i_lo, j * tlon - j_lo:(j + 1) * tlon - j_lo] = True
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    lat_out, lon_out = lat_axis[i_lo:i_hi], lon_axis[j_lo:j_hi]

    def save(v, s, vals, time_coord, fname):
        vals = vals.astype(np.float32)
        vals[:, ~filled] = np.nan
        da = xr.DataArray(vals, dims=("time", "lat", "lon"), name=v,
                          coords={"time": time_coord, "lat": lat_out, "lon": lon_out}, attrs={
            "units": ds[v].attrs.get("units", ""),
            "long_name": f"{ds[v].attrs.get('long_name', v)}, {freq} {s.replace('_', ' ')}",
            "statistic": s, "frequency": freq,
            "source": f"ERA5 hourly (reanalysis-era5-single-levels), ECMWF ARCO Zarr {STORE_URL}",
        })
        da.to_netcdf(out / fname)
        print(f"Saved {out / fname}", flush=True)

    # Periods: months, or days, counted from start-01-01.
    first_day = pd.Timestamp(f"{start}-01-01")
    if freq == "monthly":
        periods = pd.period_range(f"{start}-01", f"{end}-12", freq="M")
        def period_index(ts):
            return (ts.year - start) * 12 + ts.month - 1
    else:
        periods = pd.date_range(first_day, f"{end}-12-31", freq="D")
        def period_index(ts):
            return ((ts - first_day) // pd.Timedelta(days=1)).to_numpy()
    n_p = len(periods)
    hours = {v: np.zeros(n_p, dtype=np.int64) for v in variables}   # hourly values seen
    days_seen = {v: np.zeros(n_p, dtype=np.int64) for v in variables}

    # Accumulators. Monthly: whole period. Daily: one block per year, saved
    # and freed as soon as the year is complete.
    acc = {}
    def accumulator(v, s, year=None):
        key = (v, s, year)
        if key not in acc:
            n = n_p if year is None else (366 if calendar.isleap(year) else 365)
            acc[key] = np.full((n, ny, nx), FILL.get(s, 0.0),
                               dtype=np.float64 if year is None else np.float32)
        return acc[key]

    year_first = {y: (pd.Timestamp(f"{y}-01-01") - first_day).days for y in range(start, end + 1)}

    def add_daily(v, s, day_idx, vals, ys, xs):
        """Merge per-day results (days day_idx) into the per-year accumulators."""
        years = periods[day_idx].year
        for y in np.unique(years):
            m = years == y
            block = accumulator(v, s, int(y))[:, ys, xs]
            rows = day_idx[m] - year_first[int(y)]
            if s in ("sum", "mean"):
                block[rows] += vals[m]
            else:
                block[rows] = REDUCE[s](block[rows], vals[m])
            accumulator(v, s, int(y))[:, ys, xs] = block

    def flush_years(processed_upto):
        """Save daily files for every year whose hours have all been read."""
        any_accum = any(accum.values())
        for y in range(start, end + 1):
            y_end = times.searchsorted(pd.Timestamp(f"{y + 1}-01-01")) + (1 if any_accum else 0)
            keys = [k for k in acc if k[2] == y]
            if not keys or processed_upto < y_end:
                continue
            first, ndays = year_first[y], len(acc[keys[0]])
            for v, s, _ in keys:
                assert (hours[v][first:first + ndays] == 24).all(), f"{v} {y}: incomplete days"
                vals = acc.pop((v, s, y))
                if s == "mean":
                    vals = vals / 24.0
                save(v, s, vals, periods[first:first + ndays], f"era5_{v}_{s}_daily_{y}.nc")

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
            p_hr = period_index(ts)
            hr_starts = run_starts(p_hr)
            if freq == "monthly" and set(stats) & MONTHLY_DAILY_STATS:
                p_day = period_index(times[a_:b_:24])
                day_starts = run_starts(p_day)
            for n, (i, j) in enumerate(tiles, 1):
                h = ds[v][a_:b_, i * tlat:(i + 1) * tlat, j * tlon:(j + 1) * tlon].values.astype(np.float64)
                ys = slice(i * tlat - i_lo, (i + 1) * tlat - i_lo)
                xs = slice(j * tlon - j_lo, (j + 1) * tlon - j_lo)
                for s in stats:
                    if freq == "daily":
                        add_daily(v, s, p_hr[hr_starts], REDUCE[s].reduceat(h, hr_starts, axis=0), ys, xs)
                    elif s in ("mean", "sum"):
                        accumulator(v, s)[p_hr[hr_starts], ys, xs] += np.add.reduceat(h, hr_starts, axis=0)
                    else:   # monthly statistics of daily min / max
                        d = h.reshape(-1, 24, tlat, tlon)
                        daily = d.min(1) if s == "daily_min_mean" else d.max(1)
                        m = p_day[day_starts]
                        if s == "daily_max_max":
                            accumulator(v, s)[m, ys, xs] = np.maximum(
                                accumulator(v, s)[m, ys, xs], np.maximum.reduceat(daily, day_starts, axis=0))
                        else:
                            accumulator(v, s)[m, ys, xs] += np.add.reduceat(daily, day_starts, axis=0)
                if n % 25 == 0 or n == len(tiles):
                    print(f"  {v} {times[a_]:%Y-%m}..{times[b_ - 1]:%Y-%m}: {n}/{len(tiles)} tiles "
                          f"({(time.monotonic() - t_start) / 60:.1f} min)", flush=True)
            hours[v][p_hr[hr_starts]] += np.diff(np.r_[hr_starts, len(p_hr)])
            if freq == "monthly" and set(stats) & MONTHLY_DAILY_STATS:
                days_seen[v][p_day[day_starts]] += np.diff(np.r_[day_starts, len(p_day)])
        if freq == "daily":
            flush_years(min((k + 1) * tchunk, i1 + 1))

    if freq == "daily":
        assert not acc, f"years left unsaved: {sorted({k[2] for k in acc})}"
        return

    ndays = periods.days_in_month.values
    for (v, s, _), vals in acc.items():
        if s in ("mean", "sum"):
            assert (hours[v] == ndays * 24).all(), f"{v}: incomplete months"
        else:
            assert (days_seen[v] == ndays).all(), f"{v} {s}: incomplete months"
        if s == "mean":
            vals = vals / hours[v][:, None, None]
        elif s in ("daily_min_mean", "daily_max_mean"):
            vals = vals / days_seen[v][:, None, None]
        save(v, s, vals, periods.to_timestamp(how="start") + pd.Timedelta(days=14),
             f"era5_{v}_{s}_monthly_{start}_{end}.nc")


if __name__ == "__main__":
    main()
