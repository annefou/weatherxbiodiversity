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
# # Step 2c: ERA5 monthly climate with CRU TS definitions
#
# Soroye et al.'s climate step (`soroye_port/04_climate_tei_pei.py`) reads
# four CRU TS 3.24.01 monthly variables. This notebook builds the same four
# variables from **ERA5**, so that a Phase 3 sensitivity run can swap CRU TS
# for ERA5 with nothing else changed. It contains no CRU data.
#
# | Variable | Definition (as CRU TS) | ERA5 source | Units |
# |----------|------------------------|-------------|-------|
# | `tmp` | monthly mean temperature | mean of hourly `t2m` | °C |
# | `tmn` | monthly mean of daily minimum | daily (UTC) min of hourly `t2m`, averaged | °C |
# | `tmx` | monthly mean of daily maximum | daily (UTC) max of hourly `t2m`, averaged | °C |
# | `pre` | monthly total precipitation | sum of hourly `tp` | mm |
#
# ERA5 hourly `tp` at time *t* is the accumulation over the hour **ending**
# at *t*, so each hourly value is assigned to the month containing *t* − 1 h.
#
# Data are streamed from ECMWF's ARCO Zarr store, as in `02b_stream_era5_arco.py`.
# Only the storage tiles (1° × 1°, chunks of 4 × 4 grid points) needed to
# bilinearly interpolate onto the 100 km CEA cells that contain at least one
# GBIF record are fetched. That covers the Canaries, Azores, Madeira and
# Balearics, not just the mainland. The output is a regular 0.25° grid over
# the bounding box of those tiles; points outside the fetched tiles are NaN.
#
# ## Checks done against CDS (2020, mainland box)
#
# | Variable | Reference | Max difference |
# |----------|-----------|----------------|
# | `tmp` | `reanalysis-era5-single-levels-monthly-means` t2m | 0.002 °C |
# | `tmx` | `derived-era5-single-levels-daily-statistics` daily max | 0.0002 °C |
# | `pre` | `reanalysis-era5-single-levels-monthly-means` tp × days | 0.11 mm |
#
# ## Prerequisites
#
# - CDS API key (see `02b_stream_era5_arco.py`).
# - The pinned GBIF download (DOI 10.15468/dl.3frmsq) unpacked in
#   `data/gbif_dl/`; it defines which grid cells are needed.
#
# Run as a notebook or as a script (`python 02c_stream_era5_monthly_climate.py`).
# `ERA5_START` / `ERA5_END` environment variables override the period.

# %%
import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import zarr
from fsspec.implementations.http import HTTPFileSystem
from pyproj import Transformer

# The ARCO store rate-limits per key: bursts of parallel GETs, and even
# fast sequential GETs, return 403 (with a ~2 min cool-down). Serialise
# zarr, pace requests, and back off on 403/429/5xx.
zarr.config.set({"async.concurrency": 1})


class ThrottledHTTP(HTTPFileSystem):
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

# %% [markdown]
# ## Configuration
#
# 1940–2014: from the start of ERA5 to the end of Soroye's recent period.
# ERA5 has no data before 1940, so the climate baseline of the ERA5 run is
# 1940–1974 instead of CRU's 1901–1974.

# %%
DATA = Path("../data") if Path("../data").exists() else Path("data")

STORE_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-002/arco/"
    "reanalysis_era5_single_levels/sfc/geoChunked.zarr"
)
START = int(os.environ.get("ERA5_START", 1940))
END = int(os.environ.get("ERA5_END", 2014))
GBIF_KEY = os.environ.get("GBIF_DOWNLOAD_KEY", "0006204-260423192947929")
GBIF_CSV = DATA / "gbif_dl" / f"{GBIF_KEY}.csv"
OUTDIR = Path(os.environ.get("ERA5_OUTDIR", DATA / "era5_monthly"))
WORKERS = 1  # concurrent tile reads; the ARCO store 403s above ~10 in flight

# CEA grid — identical to soroye_port/02_presence_absence.py
RES_M = 100_000
X_MIN, X_MAX = -20_037_507, 20_062_493
Y_MIN, Y_MAX = -5_263_885, 6_336_115
CEA = "+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84"

# %% [markdown]
# ## 1. Open the store

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


fs = ThrottledHTTP(
    asynchronous=True,
    headers={"Authorization": f"Bearer {cds_api_key()}"},
)
store = zarr.storage.FsspecStore(fs=fs, path=STORE_URL)

ds = xr.open_zarr(
    store,
    consolidated=True,
    chunks=None,
)
lat_axis = ds["latitude"].values
lon_axis = ds["longitude"].values
assert lat_axis[0] < lat_axis[-1] and lon_axis[0] < lon_axis[-1]
times = pd.DatetimeIndex(ds["time"].values)
tchunk, tlat, tlon = ds["t2m"].encoding["chunks"]
assert ds["tp"].encoding["chunks"] == (tchunk, tlat, tlon)
if tchunk % 24 or times[0].hour != 0:
    raise SystemExit("Store time chunks are not aligned to UTC days")

# %% [markdown]
# ## 2. Which storage tiles are needed
#
# Project every GBIF record onto the 100 km CEA grid, take the centres of the
# occupied cells, and keep each storage tile that holds one of the 2 × 2 grid
# points a bilinear interpolation at those centres would use.

# %%
def needed_cell_centres(gbif_csv: Path) -> tuple[np.ndarray, np.ndarray]:
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
    lon, lat = Transformer.from_crs(CEA, "EPSG:4326", always_xy=True).transform(xc, yc)
    return lat, lon


def needed_tiles(lat_pts, lon_pts, lat_axis, lon_axis, tile):
    """(lat_tile, lon_tile) chunk indices covering the 2x2 bilinear
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


lat_pts, lon_pts = needed_cell_centres(GBIF_CSV)
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

# %% [markdown]
# ## 3. Period and accumulators
#
# `t2m` is needed over [START-01-01T00, END+1-01-01T00); `tp` over
# (START-01-01T00, END+1-01-01T00], because its values are hour-ending
# accumulations. Monthly sums and day/hour counts are accumulated, so months
# that straddle storage time chunks are handled exactly.

# %%
i0 = times.searchsorted(pd.Timestamp(f"{START}-01-01"))
i1 = times.searchsorted(pd.Timestamp(f"{END + 1}-01-01"))
if i1 >= len(times):
    raise SystemExit("Requested end year is beyond the store")
step = np.diff(times[i0 : i1 + 1].values).astype("timedelta64[h]")
if not (step == np.timedelta64(1, "h")).all():
    raise SystemExit("Hourly time axis has gaps in the requested period")

months = pd.period_range(f"{START}-01", f"{END}-12", freq="M")
n_m, ny, nx = len(months), i_hi - i_lo, j_hi - j_lo
acc = {k: np.zeros((n_m, ny, nx)) for k in ("tmp", "tmn", "tmx", "pre")}
cnt = {k: np.zeros(n_m, dtype=np.int64) for k in ("tmp", "tmn", "tmx", "pre")}
filled = np.zeros((ny, nx), dtype=bool)
for i, j in tiles:
    filled[i * tlat - i_lo : (i + 1) * tlat - i_lo,
           j * tlon - j_lo : (j + 1) * tlon - j_lo] = True


def month_index(ts: pd.DatetimeIndex) -> np.ndarray:
    return (ts.year - START) * 12 + ts.month - 1


def month_reduce(values, labels):
    """Sum the leading axis over runs of consecutive equal integer labels.
    Returns (labels of the runs, sums, run lengths)."""
    starts = np.flatnonzero(np.r_[True, labels[1:] != labels[:-1]])
    sums = np.add.reduceat(values, starts, axis=0)
    counts = np.diff(np.r_[starts, len(labels)])
    return labels[starts], sums, counts

# %% [markdown]
# ## 4. Stream tiles, one storage time chunk at a time
#
# Tiles are read concurrently, at most `WORKERS` held in memory at once
# (about 9 MB each per full time chunk).

# %%
def load_tile(var, a, b, i, j):
    return ds[var][a:b, i * tlat : (i + 1) * tlat,
                   j * tlon : (j + 1) * tlon].values.astype(np.float64)


def tiles_streamed(var, a, b):
    for n in range(0, len(tiles), WORKERS):
        batch = tiles[n : n + WORKERS]
        futs = [pool.submit(load_tile, var, a, b, i, j) for i, j in batch]
        for ij, f in zip(batch, futs):
            yield ij, f.result()


pool = ThreadPoolExecutor(WORKERS)
k0, k1 = i0 // tchunk, i1 // tchunk
for k in range(k0, k1 + 1):
    a, b = max(i0, k * tchunk), min(i1, (k + 1) * tchunk)              # t2m
    ap, bp = max(i0 + 1, k * tchunk), min(i1 + 1, (k + 1) * tchunk)    # tp
    print(f"  time chunk {k - k0 + 1}/{k1 - k0 + 1} "
          f"{times[min(a, ap)]:%Y-%m-%d}..{times[max(b, bp) - 1]:%Y-%m-%d}",
          end=" ", flush=True)

    if b > a:
        mi_day = month_index(times[a:b:24])
        for (i, j), hourly in tiles_streamed("t2m", a, b):
            h = hourly.reshape(-1, 24, tlat, tlon)
            ys = slice(i * tlat - i_lo, (i + 1) * tlat - i_lo)
            xs = slice(j * tlon - j_lo, (j + 1) * tlon - j_lo)
            for key, daily in (("tmp", h.mean(1)), ("tmn", h.min(1)), ("tmx", h.max(1))):
                lab, s, _ = month_reduce(daily, mi_day)
                acc[key][lab, ys, xs] += s
        lab, _, c = month_reduce(np.zeros(len(mi_day)), mi_day)
        for key in ("tmp", "tmn", "tmx"):
            cnt[key][lab] += c

    if bp > ap:
        mi_hr = month_index(times[ap:bp] - pd.Timedelta(hours=1))
        for (i, j), hourly in tiles_streamed("tp", ap, bp):
            ys = slice(i * tlat - i_lo, (i + 1) * tlat - i_lo)
            xs = slice(j * tlon - j_lo, (j + 1) * tlon - j_lo)
            lab, s, _ = month_reduce(hourly, mi_hr)
            acc["pre"][lab, ys, xs] += s
        lab, _, c = month_reduce(np.zeros(len(mi_hr)), mi_hr)
        cnt["pre"][lab] += c
    print("done", flush=True)
pool.shutdown()

# Every month must be complete: all days for t2m, all hours for tp.
ndays = months.days_in_month.values
assert (cnt["tmp"] == ndays).all(), "incomplete days in some month"
assert (cnt["pre"] == ndays * 24).all(), "incomplete hours in some month"

# %% [markdown]
# ## 5. Save one NetCDF per variable
#
# Layout `(time, lat, lon)` with monthly time stamps at mid-month, read by
# `soroye_port/04_climate_tei_pei.py` when `CLIMATE_SOURCE=era5`.

# %%
OUTDIR.mkdir(parents=True, exist_ok=True)
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
    da = xr.DataArray(vals, dims=("time", "lat", "lon"), coords=coords, name=var,
                      attrs={"units": units, "long_name": long_name})
    da.attrs["source"] = ("ERA5 hourly (reanalysis-era5-single-levels), ECMWF ARCO Zarr, "
                          "aggregated with CRU TS 3.24.01 definitions")
    f = OUTDIR / f"era5_{var}_monthly_{START}_{END}.nc"
    da.to_netcdf(f)
    print(f"Saved {f} ({f.stat().st_size / 1e6:.1f} MB)")
