"""
Build monthly climate (tmp, tmn, tmx, pre) from ERA5 hourly
data streamed from ECMWF's ARCO Zarr store, as climate input for a planned
Phase 3 sensitivity run that swaps CRU TS for ERA5 in
soroye_port/04_climate_tei_pei.py.

Variable definitions mirror CRU TS 3.24.01:
    tmp  monthly mean 2 m temperature           (mean of hourly t2m)      degC
    tmn  monthly mean of daily minimum t2m      (UTC days)                degC
    tmx  monthly mean of daily maximum t2m      (UTC days)                degC
    pre  monthly total precipitation            (sum of hourly tp)        mm
ERA5 hourly `tp` at time t is the accumulation over the hour ending at t,
so each hourly value is assigned to the month containing t - 1 h.

Only the storage tiles (1 x 1 degree, chunks of 4 x 4 grid points) that are
needed to bilinearly interpolate onto the 100 km CEA cells containing at
least one GBIF record are fetched. The output is a regular 0.25 degree grid
over the bounding box of those tiles; points outside fetched tiles are NaN.

Authentication: CDS API key (see stream_era5_arco.py).

Usage:
    python stream_era5_monthly_climate.py                    # 1940-2014
    python stream_era5_monthly_climate.py --start 2000 --end 2000 --outdir /tmp/x
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

from stream_era5_arco import open_store

GBIF_CSV = "data/gbif_dl/0006204-260423192947929.csv"

# CEA grid — identical to soroye_port/02_presence_absence.py
RES_M = 100_000
X_MIN, X_MAX = -20_037_507, 20_062_493
Y_MIN, Y_MAX = -5_263_885, 6_336_115
N_X = (X_MAX - X_MIN) // RES_M
N_Y = (Y_MAX - Y_MIN) // RES_M
CEA = "+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84"


def needed_cell_centres(gbif_csv: str) -> tuple[np.ndarray, np.ndarray]:
    """Lat/lon of the CEA cell centres that contain any GBIF record."""
    df = pd.read_csv(
        gbif_csv, sep="\t", usecols=["decimalLatitude", "decimalLongitude"]
    ).dropna()
    x, y = Transformer.from_crs("EPSG:4326", CEA, always_xy=True).transform(
        df["decimalLongitude"].values, df["decimalLatitude"].values
    )
    col = np.floor((x - X_MIN) / RES_M).astype(int)
    row = np.floor((Y_MAX - y) / RES_M).astype(int)
    cells = np.unique(np.stack([row, col], axis=1), axis=0)
    xc = X_MIN + (cells[:, 1] + 0.5) * RES_M
    yc = Y_MAX - (cells[:, 0] + 0.5) * RES_M
    lon, lat = Transformer.from_crs(CEA, "EPSG:4326", always_xy=True).transform(
        xc, yc
    )
    return lat, lon


def needed_tiles(lat_pts, lon_pts, lat_axis, lon_axis, tile):
    """Set of (lat_tile, lon_tile) chunk indices covering the 2x2 bilinear
    neighbours of every target point."""
    def neighbours(axis, pts):
        step = axis[1] - axis[0]
        i = np.floor((pts - axis[0]) / step).astype(int)
        return np.stack([i, i + 1], axis=1)

    li = neighbours(lat_axis, lat_pts)
    lj = neighbours(lon_axis, lon_pts)
    tiles = set()
    for a in range(2):
        for b in range(2):
            for i, j in zip(li[:, a] // tile[0], lj[:, b] // tile[1]):
                tiles.add((int(i), int(j)))
    return sorted(tiles)


def month_reduce(values, labels, how):
    """Group the leading axis by consecutive integer labels.
    Returns (unique_labels, sums, counts) for how='sum'."""
    starts = np.flatnonzero(np.r_[True, labels[1:] != labels[:-1]])
    sums = np.add.reduceat(values, starts, axis=0)
    counts = np.diff(np.r_[starts, len(labels)])
    return labels[starts], sums, counts


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--start", type=int, default=1940)
    p.add_argument("--end", type=int, default=2014)
    p.add_argument("--gbif", default=GBIF_CSV)
    p.add_argument("--outdir", default="data/era5_monthly")
    p.add_argument("--workers", type=int, default=32)
    args = p.parse_args()

    ds = open_store()
    lat_axis = ds["latitude"].values
    lon_axis = ds["longitude"].values
    assert lat_axis[0] < lat_axis[-1] and lon_axis[0] < lon_axis[-1]
    times = pd.DatetimeIndex(ds["time"].values)
    tchunk, tlat, tlon = ds["t2m"].encoding["chunks"]
    assert ds["tp"].encoding["chunks"] == (tchunk, tlat, tlon)
    if tchunk % 24 or times[0].hour != 0:
        raise SystemExit("Store time chunks are not aligned to UTC days")

    lat_pts, lon_pts = needed_cell_centres(args.gbif)
    tiles = needed_tiles(lat_pts, lon_pts, lat_axis, lon_axis, (tlat, tlon))
    ti = np.array([t[0] for t in tiles])
    tj = np.array([t[1] for t in tiles])
    i_lo, i_hi = ti.min() * tlat, (ti.max() + 1) * tlat
    j_lo, j_hi = tj.min() * tlon, (tj.max() + 1) * tlon
    print(
        f"{len(lat_pts)} CEA cells with GBIF records -> {len(tiles)} tiles, "
        f"box lat {lat_axis[i_lo]:.2f}..{lat_axis[i_hi - 1]:.2f}, "
        f"lon {lon_axis[j_lo]:.2f}..{lon_axis[j_hi - 1]:.2f}"
    )

    # Hours needed: t2m over [start-01-01T00, end+1-01-01T00);
    # tp over (start-01-01T00, end+1-01-01T00] (hour-ending accumulations).
    i0 = times.searchsorted(pd.Timestamp(f"{args.start}-01-01"))
    i1 = times.searchsorted(pd.Timestamp(f"{args.end + 1}-01-01"))
    if i1 >= len(times):
        raise SystemExit("Requested end year is beyond the store")
    step = np.diff(times[i0 : i1 + 1].values).astype("timedelta64[h]")
    if not (step == np.timedelta64(1, "h")).all():
        raise SystemExit("Hourly time axis has gaps in the requested period")

    months = pd.period_range(f"{args.start}-01", f"{args.end}-12", freq="M")
    n_m, ny, nx = len(months), i_hi - i_lo, j_hi - j_lo
    acc = {k: np.zeros((n_m, ny, nx)) for k in ("tmp", "tmn", "tmx", "pre")}
    cnt = {k: np.zeros(n_m, dtype=np.int64) for k in ("tmp", "tmn", "tmx", "pre")}
    filled = np.zeros((ny, nx), dtype=bool)
    for i, j in tiles:
        filled[i * tlat - i_lo : (i + 1) * tlat - i_lo,
               j * tlon - j_lo : (j + 1) * tlon - j_lo] = True

    def month_index(ts: pd.DatetimeIndex) -> np.ndarray:
        return (ts.year - args.start) * 12 + ts.month - 1

    def load_tile(var, a, b, i, j):
        return ds[var][a:b, i * tlat : (i + 1) * tlat,
                       j * tlon : (j + 1) * tlon].values.astype(np.float64)

    def tiles_streamed(var, a, b):
        """Yield ((i, j), hourly array) with at most `workers` tiles in
        memory at once (each is ~9 MB per full time chunk)."""
        for n in range(0, len(tiles), args.workers):
            batch = tiles[n : n + args.workers]
            futs = [pool.submit(load_tile, var, a, b, i, j) for i, j in batch]
            for ij, f in zip(batch, futs):
                yield ij, f.result()

    pool = ThreadPoolExecutor(args.workers)
    k0, k1 = i0 // tchunk, i1 // tchunk
    for k in range(k0, k1 + 1):
        # t2m: whole UTC days inside [i0, i1)
        a, b = max(i0, k * tchunk), min(i1, (k + 1) * tchunk)
        # tp: hours (i0, i1] -> indices [i0+1, i1+1)
        ap, bp = max(i0 + 1, k * tchunk), min(i1 + 1, (k + 1) * tchunk)
        print(f"  time chunk {k - k0 + 1}/{k1 - k0 + 1} "
              f"{times[min(a, ap)]:%Y-%m-%d}..{times[max(b, bp) - 1]:%Y-%m-%d}",
              end=" ", flush=True)

        if b > a:
            days = times[a:b:24]
            mi_day = month_index(days)
            for (i, j), hourly in tiles_streamed("t2m", a, b):
                h = hourly.reshape(-1, 24, tlat, tlon)
                ys = slice(i * tlat - i_lo, (i + 1) * tlat - i_lo)
                xs = slice(j * tlon - j_lo, (j + 1) * tlon - j_lo)
                for key, daily in (("tmp", h.mean(1)), ("tmn", h.min(1)), ("tmx", h.max(1))):
                    lab, s, c = month_reduce(daily, mi_day, "sum")
                    acc[key][lab, ys, xs] += s
            lab, _, c = month_reduce(np.zeros(len(mi_day)), mi_day, "sum")
            for key in ("tmp", "tmn", "tmx"):
                cnt[key][lab] += c

        if bp > ap:
            mi_hr = month_index(times[ap:bp] - pd.Timedelta(hours=1))
            for (i, j), hourly in tiles_streamed("tp", ap, bp):
                ys = slice(i * tlat - i_lo, (i + 1) * tlat - i_lo)
                xs = slice(j * tlon - j_lo, (j + 1) * tlon - j_lo)
                lab, s, c = month_reduce(hourly, mi_hr, "sum")
                acc["pre"][lab, ys, xs] += s
            lab, _, c = month_reduce(np.zeros(len(mi_hr)), mi_hr, "sum")
            cnt["pre"][lab] += c
        print("done", flush=True)
    pool.shutdown()

    # Every month must be complete: days for t2m, hours for tp.
    ndays = months.days_in_month.values
    assert (cnt["tmp"] == ndays).all(), "incomplete days in some month"
    assert (cnt["pre"] == ndays * 24).all(), "incomplete hours in some month"

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    coords = {
        "time": months.to_timestamp(how="start") + pd.Timedelta(days=14),
        "lat": lat_axis[i_lo:i_hi],
        "lon": lon_axis[j_lo:j_hi],
    }
    fields = {
        "tmp": (acc["tmp"] / cnt["tmp"][:, None, None] - 273.15, "degC",
                "monthly mean of hourly 2m temperature"),
        "tmn": (acc["tmn"] / cnt["tmn"][:, None, None] - 273.15, "degC",
                "monthly mean of daily (UTC) minimum 2m temperature"),
        "tmx": (acc["tmx"] / cnt["tmx"][:, None, None] - 273.15, "degC",
                "monthly mean of daily (UTC) maximum 2m temperature"),
        "pre": (acc["pre"] * 1000.0, "mm",
                "monthly total precipitation (sum of hourly tp)"),
    }
    for var, (vals, units, long_name) in fields.items():
        vals = vals.astype(np.float32)
        vals[:, ~filled] = np.nan
        da = xr.DataArray(vals, dims=("time", "lat", "lon"), coords=coords,
                          name=var, attrs={"units": units, "long_name": long_name})
        da.attrs["source"] = "ERA5 hourly (reanalysis-era5-single-levels), ECMWF ARCO Zarr, aggregated with CRU TS 3.24.01 definitions"
        f = out / f"era5_{var}_monthly_{args.start}_{args.end}.nc"
        da.to_netcdf(f)
        print(f"Saved {f} ({f.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
