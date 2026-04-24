"""
Python port of Soroye et al. (2020) — script 4 + helpers.

Sources:
  4_CalcClim_andExposure.R
  func_avgclimate.R
  ClimaticPositionIndex/SpeciesThermalLimits.R
  ClimaticPositionIndex/MapThermalStress.R
  (and the precip equivalents)

Steps:
  1. Read CRU TS 3.24.01 monthly climate (tmp, tmn, tmx, pre) from NetCDF.
  2. Aggregate to annual: tmp→mean, pre→sum, tmn→annual-min, tmx→annual-max.
  3. Bilinear-interpolate the global 0.5° data onto the 100km CEA grid.
  4. mean_T_baseline / recent; same for precip.
  5. Per-cell T_cold = min(annual_tmn across all years)
                 T_hot  = max(annual_tmx across all years)  (climateLimits proxies)
  6. Per-species thermal limits via SpeciesThermalLimits logic:
        T_min_spp = min(T_cold) at cells where species present in baseline
        T_max_spp = max(T_hot)  at cells where species present in baseline
  7. TEI per species per cell per period:
        TEI_bs[spp, cell]    = (meanT_baseline[cell] - T_min_spp) / (T_max_spp - T_min_spp)
        TEI_recent[spp, cell] = (meanT_recent[cell]   - T_min_spp) / (T_max_spp - T_min_spp)
        TEI_delta = TEI_recent - TEI_bs
     (This uses the linearity of CPI: mean_over_years(CPI_year) = CPI(mean_T),
      making `MapThermalStress`'s per-year loop equivalent to one CPI on the period mean.)
  8. Same for PEI using annual-sum precipitation.
  9. avgtemp_bs, avgtemp_delta, avgprecip_bs, avgprecip_delta (non-species-specific).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr
from pyproj import Transformer
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'reference' / 'Bumblebee_repo_wbombusdat'
CLIM_DIR = REF / '0_ClimateData'
import os as _os
OUT_DIR = ROOT / 'soroye_port' / _os.environ.get('OUT_SUBDIR', 'outputs')

# --- CEA grid config (matches scripts 2/3) ---
RES_M = 100_000
X_MIN, X_MAX = -20_037_507, 20_062_493
Y_MIN, Y_MAX = -5_263_885, 6_336_115

cea_to_ll = Transformer.from_crs(
    '+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84', 'EPSG:4326', always_xy=True,
)

# Period year sets (from R — baseline 1901–1974 and recent 2000–2014)
BASELINE_YEARS = list(range(1901, 1975))
RECENT_YEARS = list(range(2000, 2015))

# ---------------------------------------------------------------------------
# Helpers

def load_cru_annual(var: str, agg: str) -> xr.DataArray:
    """Load + annually aggregate all CRU TS files for variable `var`.

    agg: 'mean' | 'sum' | 'min' | 'max'
    Returns DataArray (year, lat, lon) in degC (or mm for precip).
    """
    files = sorted(CLIM_DIR.glob(f'*{var}.dat.nc'))
    print(f'  {var}: {len(files)} decade files')
    pieces = []
    for f in files:
        ds = xr.open_dataset(f)
        v = ds[var]  # monthly, shape (time, lat, lon)
        annual = getattr(v.resample(time='YE'), agg)()
        pieces.append(annual)
    annual_all = xr.concat(pieces, dim='time').sortby('time')
    # re-label time to year index
    annual_all = annual_all.assign_coords(time=annual_all['time.year']).rename({'time': 'year'})
    return annual_all

def bilinear_to_cea(
    global_da: xr.DataArray,
    lat_ll: np.ndarray,
    lon_ll: np.ndarray,
) -> np.ndarray:
    """Bilinear interpolate a global (lat, lon) DataArray at the arbitrary
    (lat_ll, lon_ll) points. Returns a flat array aligned with the input."""
    lat_coord = global_da['lat'].values
    lon_coord = global_da['lon'].values

    # Detect ordering
    # lat: CRU-TS is -89.75..89.75 (ascending).  lon: -179.75..179.75 (ascending).
    # map_coordinates needs fractional indices along each axis.
    def to_idx(coord: np.ndarray, target: np.ndarray) -> np.ndarray:
        if coord[0] > coord[-1]:
            # descending: flip meaning
            coord = coord[::-1]
            flipped = True
        else:
            flipped = False
        step = coord[1] - coord[0]
        idx = (target - coord[0]) / step
        if flipped:
            idx = (len(coord) - 1) - idx
        return idx

    lat_idx = to_idx(lat_coord, lat_ll)
    lon_idx = to_idx(lon_coord, lon_ll)
    arr = global_da.values.astype(float)
    # bilinear via map_coordinates, order=1
    vals = map_coordinates(arr, [lat_idx, lon_idx], order=1, mode='constant', cval=np.nan)
    return vals

def build_cea_cell_centers() -> tuple[int, int, np.ndarray, np.ndarray]:
    n_x = (X_MAX - X_MIN) // RES_M
    n_y = (Y_MAX - Y_MIN) // RES_M
    x_centers = X_MIN + (np.arange(n_x) + 0.5) * RES_M
    y_centers = Y_MAX - (np.arange(n_y) + 0.5) * RES_M  # descending
    xx, yy = np.meshgrid(x_centers, y_centers)          # (n_y, n_x)
    lon, lat = cea_to_ll.transform(xx.ravel(), yy.ravel())
    return n_x, n_y, lat.reshape((n_y, n_x)), lon.reshape((n_y, n_x))

# ---------------------------------------------------------------------------
# 1. Build CEA cell centers
print('Building CEA cell-center table …')
n_x, n_y, cea_lat, cea_lon = build_cea_cell_centers()
n_cells = n_x * n_y
lat_flat = cea_lat.ravel()
lon_flat = cea_lon.ravel()
print(f'  {n_cells:,} cells')

# ---------------------------------------------------------------------------
# 2. Load + aggregate CRU TS
print('\nLoading CRU TS annual aggregates …')
tmp_annual = load_cru_annual('tmp', 'mean')   # annual mean temperature
pre_annual = load_cru_annual('pre', 'sum')    # annual total precipitation
tmn_annual = load_cru_annual('tmn', 'min')    # coldest monthly min T per year
tmx_annual = load_cru_annual('tmx', 'max')    # hottest monthly max T per year
print(f'  Years available: {int(tmp_annual.year.min())}..{int(tmp_annual.year.max())}')

# ---------------------------------------------------------------------------
# 3. Interpolate to CEA grid for each needed year
def interp_years(da: xr.DataArray, years: list[int]) -> np.ndarray:
    """Return array shape (n_years, n_cells) at CEA cell centers."""
    out = np.full((len(years), n_cells), np.nan, dtype=np.float32)
    avail = set(int(y) for y in da.year.values)
    for i, yr in enumerate(years):
        if yr not in avail:
            continue
        layer = da.sel(year=yr)
        # CRU-TS default lat/lon var names may be 'latitude'/'longitude'
        if 'latitude' in layer.dims:
            layer = layer.rename({'latitude': 'lat', 'longitude': 'lon'})
        out[i, :] = bilinear_to_cea(layer, lat_flat, lon_flat)
    return out

print('\nInterpolating tmp (baseline + recent) to CEA …')
tmp_bs_yr = interp_years(tmp_annual, BASELINE_YEARS)
tmp_rc_yr = interp_years(tmp_annual, RECENT_YEARS)
print(f'  baseline shape {tmp_bs_yr.shape}, recent shape {tmp_rc_yr.shape}')

print('Interpolating pre …')
pre_bs_yr = interp_years(pre_annual, BASELINE_YEARS)
pre_rc_yr = interp_years(pre_annual, RECENT_YEARS)

print('Interpolating tmn (all years) for climate-cold limits …')
all_years = list(range(int(tmn_annual.year.min()), int(tmn_annual.year.max()) + 1))
tmn_all_yr = interp_years(tmn_annual, all_years)
tmx_all_yr = interp_years(tmx_annual, all_years)

# ---------------------------------------------------------------------------
# 4. Period means (for TEI = CPI(mean_T), using linearity identity)

def period_mean(a: np.ndarray) -> np.ndarray:
    return np.nanmean(a, axis=0)

meanT_bs = period_mean(tmp_bs_yr)
meanT_rc = period_mean(tmp_rc_yr)
meanP_bs = np.nanmean(pre_bs_yr, axis=0)
meanP_rc = np.nanmean(pre_rc_yr, axis=0)

# avgtemp_bs, avgtemp_delta, avgprecip_bs, avgprecip_delta
avgtemp_bs = meanT_bs
avgtemp_delta = meanT_rc - meanT_bs
avgprecip_bs = meanP_bs
avgprecip_delta = meanP_rc - meanP_bs

# ---------------------------------------------------------------------------
# 5. Per-cell T_cold = min over years of annual_tmn_min
#    Per-cell T_hot = max over years of annual_tmx_max

with np.errstate(invalid='ignore'):
    T_cold = np.nanmin(tmn_all_yr, axis=0)
    T_hot  = np.nanmax(tmx_all_yr, axis=0)
    P_dry  = np.nanmin(pre_annual.reindex(year=all_years).values.reshape(-1, pre_annual.shape[1]*pre_annual.shape[2])[:, :n_cells], axis=0) if False else None  # fix below
# Precip limits are less standard; we use per-year total precip min/max across full time
pre_all_yr = interp_years(pre_annual, all_years)
with np.errstate(invalid='ignore'):
    P_dry = np.nanmin(pre_all_yr, axis=0)
    P_wet = np.nanmax(pre_all_yr, axis=0)

# ---------------------------------------------------------------------------
# 6. Load presence/absence (baseline) from script 02
pa = np.load(OUT_DIR / 'presence_absence.npz', allow_pickle=True)
species = list(pa['species'])
prab_baseline = pa['prab_baseline']     # (spp, cells) 1/0/NaN

# Per-species thermal + precip limits (SpeciesThermalLimits static type)
print('\nComputing per-species thermal + precip limits …')
n_spp = len(species)
T_min_spp = np.full(n_spp, np.nan)
T_max_spp = np.full(n_spp, np.nan)
P_min_spp = np.full(n_spp, np.nan)
P_max_spp = np.full(n_spp, np.nan)
for s in range(n_spp):
    occupied = prab_baseline[s] == 1
    if not occupied.any():
        continue
    T_min_spp[s] = np.nanmin(T_cold[occupied])
    T_max_spp[s] = np.nanmax(T_hot[occupied])
    P_min_spp[s] = np.nanmin(P_dry[occupied])
    P_max_spp[s] = np.nanmax(P_wet[occupied])

# ---------------------------------------------------------------------------
# 7. TEI / PEI per species per cell per period

print('Computing TEI / PEI …')
T_range = T_max_spp - T_min_spp
P_range = P_max_spp - P_min_spp

# Broadcast: meanT_bs (n_cells,) — per-species TEI shape (n_spp, n_cells)
TEI_bs = (meanT_bs[np.newaxis, :] - T_min_spp[:, np.newaxis]) / T_range[:, np.newaxis]
TEI_rc = (meanT_rc[np.newaxis, :] - T_min_spp[:, np.newaxis]) / T_range[:, np.newaxis]
TEI_delta = TEI_rc - TEI_bs

PEI_bs = (meanP_bs[np.newaxis, :] - P_min_spp[:, np.newaxis]) / P_range[:, np.newaxis]
PEI_rc = (meanP_rc[np.newaxis, :] - P_min_spp[:, np.newaxis]) / P_range[:, np.newaxis]
PEI_delta = PEI_rc - PEI_bs

# ---------------------------------------------------------------------------
# 8. Save

np.savez_compressed(
    OUT_DIR / 'climate_tei_pei.npz',
    species=np.array(species),
    avgtemp_bs=avgtemp_bs.astype(np.float32),
    avgtemp_delta=avgtemp_delta.astype(np.float32),
    avgprecip_bs=avgprecip_bs.astype(np.float32),
    avgprecip_delta=avgprecip_delta.astype(np.float32),
    TEI_bs=TEI_bs.astype(np.float32),
    TEI_delta=TEI_delta.astype(np.float32),
    PEI_bs=PEI_bs.astype(np.float32),
    PEI_delta=PEI_delta.astype(np.float32),
    T_min_spp=T_min_spp.astype(np.float32),
    T_max_spp=T_max_spp.astype(np.float32),
    P_min_spp=P_min_spp.astype(np.float32),
    P_max_spp=P_max_spp.astype(np.float32),
    n_x=n_x, n_y=n_y,
)
print(f'\nSaved → {OUT_DIR / "climate_tei_pei.npz"}')
print(f'\navgtemp_bs range: {np.nanmin(avgtemp_bs):.2f}..{np.nanmax(avgtemp_bs):.2f} °C')
print(f'avgtemp_delta range: {np.nanmin(avgtemp_delta):.2f}..{np.nanmax(avgtemp_delta):.2f} °C')
print(f'TEI_delta range: {np.nanmin(TEI_delta):.3f}..{np.nanmax(TEI_delta):.3f}')
print(f'Median TEI_delta at species-occupied baseline cells: {np.nanmedian(TEI_delta[prab_baseline == 1]):.3f}')
