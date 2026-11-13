"""
Climate normals + thermal/precipitation exposure indices (TEI/PEI).

Port of Soroye et al. (2020) script 4 (4_CalcClim_andExposure.R,
func_avgclimate.R, ClimaticPositionIndex/*), parameterized as a CWL tool.

Climate input (--climate-dir): monthly files in the common climate input
format, <source>_{tmp,tmn,tmx,pre}_monthly_<start>_<end>.nc, where <source>
is --climate-source (default era5: the output of
workflows/ERA5_Preprocessing/era5_to_climate.py). Another source (e.g.
Destination Earth Climate DT) only needs to write the same files.

Annual aggregation: tmp -> annual mean, pre -> annual sum, tmn -> annual min,
tmx -> annual max.

Method (unchanged from the replication):
  1. Annually aggregate monthly climate.
  2. Bilinear-interpolate onto the study's CEA grid cell centers.
  3. Period means for baseline and recent windows.
  4. Per-cell T_cold = min(annual tmn), T_hot = max(annual tmx),
     P_dry = min(annual pre), P_wet = max(annual pre) over ALL years.
  5. Per-species limits = min/max of those over baseline-occupied cells
     (presence_absence.npz from step 02).
  6. TEI = (meanT - T_min)/(T_max - T_min) per period; PEI likewise;
     deltas = recent - baseline.

Writes <output-dir>/climate_tei_pei.npz.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr
from pyproj import Transformer
from scipy.ndimage import map_coordinates

CEA_CRS = "+proj=cea +lat_ts=0 +lon_0=0 +ellps=WGS84"
VARS = ("tmp", "tmn", "tmx", "pre")
AGGS = {"tmp": "mean", "pre": "sum", "tmn": "min", "tmx": "max"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Climate normals + TEI/PEI exposure indices")
    p.add_argument("--presence-absence", type=Path, required=True,
                   help="presence_absence.npz from step 02")
    p.add_argument("--climate-dir", type=Path, required=True,
                   help="directory with monthly climate files")
    p.add_argument("--climate-source", default="era5",
                   help="file prefix of the monthly climate files, "
                        "<source>_<var>_monthly_*.nc (default: era5)")
    p.add_argument("--years-baseline", type=int, nargs=2, required=True,
                   metavar=("START", "END"), help="baseline period (inclusive)")
    p.add_argument("--years-recent", type=int, nargs=2, required=True,
                   metavar=("START", "END"), help="recent period (inclusive)")
    p.add_argument("--grid-resolution-m", type=int, required=True)
    bbox = p.add_mutually_exclusive_group(required=True)
    bbox.add_argument("--grid-bbox", type=float, nargs=4,
                      metavar=("XMIN", "XMAX", "YMIN", "YMAX"),
                      help="CEA meters")
    bbox.add_argument("--bbox-latlon", type=float, nargs=4,
                      metavar=("N", "W", "S", "E"), help="degrees")
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def grid_bounds(a: argparse.Namespace) -> tuple[float, float, float, float]:
    if a.grid_bbox is not None:
        return tuple(a.grid_bbox)
    n, w, s, e = a.bbox_latlon
    ll_to_cea = Transformer.from_crs("EPSG:4326", CEA_CRS, always_xy=True)
    x_min, y_s = ll_to_cea.transform(w, s)
    x_max, y_n = ll_to_cea.transform(e, n)
    return x_min, x_max, y_s, y_n


def climate_files(climate_dir: Path, source: str, var: str) -> list[Path]:
    pattern = f"{source}_{var}_monthly_*.nc"
    files = sorted(climate_dir.glob(pattern))
    if not files:
        hint = (
            f"expected files {source}_<var>_monthly_<start>_<end>.nc, e.g. the "
            "output of workflows/ERA5_Preprocessing (in this repo: "
            "runs/ERA5_Preprocessing/results/)"
        )
        listed = sorted(p.name for p in climate_dir.iterdir())[:10]
        raise FileNotFoundError(
            f"climate_dir {climate_dir} has no {source} files for '{var}' "
            f"(pattern {pattern}). {hint}. Directory contains: "
            f"{', '.join(listed) if listed else '(empty)'}. Check the "
            f"climate_dir path and climate_source in the job file."
        )
    return files


def load_annual(climate_dir: Path, source: str, var: str) -> xr.DataArray:
    agg = AGGS[var]
    files = climate_files(climate_dir, source, var)
    print(f"  {var}: {len(files)} file(s)")
    pieces = []
    for f in files:
        v = xr.open_dataset(f)[var]
        # skipna=False: a year with a missing month (or a point without data)
        # stays missing, instead of a partial or zero sum.
        pieces.append(getattr(v.resample(time="YE"), agg)(skipna=False))
    annual = xr.concat(pieces, dim="time").sortby("time")
    annual = annual.assign_coords(time=annual["time.year"]).rename({"time": "year"})
    return annual


def bilinear_to_points(da: xr.DataArray, lat_ll: np.ndarray, lon_ll: np.ndarray) -> np.ndarray:
    lat_coord = da["lat"].values
    lon_coord = da["lon"].values

    def to_idx(coord: np.ndarray, target: np.ndarray) -> np.ndarray:
        if coord[0] > coord[-1]:
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
    return map_coordinates(da.values.astype(float), [lat_idx, lon_idx],
                           order=1, mode="constant", cval=np.nan)


def main() -> None:
    a = parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    res = a.grid_resolution_m
    x_min, x_max, y_min, y_max = grid_bounds(a)
    n_x = int(round((x_max - x_min) / res))
    n_y = int(round((y_max - y_min) / res))
    x_centers = x_min + (np.arange(n_x) + 0.5) * res
    y_centers = y_max - (np.arange(n_y) + 0.5) * res
    xx, yy = np.meshgrid(x_centers, y_centers)
    cea_to_ll = Transformer.from_crs(CEA_CRS, "EPSG:4326", always_xy=True)
    lon, lat = cea_to_ll.transform(xx.ravel(), yy.ravel())
    n_cells = n_x * n_y
    print(f"Grid: {n_x} x {n_y} = {n_cells:,} cells at {res} m")

    print(f"Loading {a.climate_source} annual aggregates …")
    annual = {var: load_annual(a.climate_dir, a.climate_source, var) for var in VARS}
    all_years = list(range(int(annual["tmp"].year.min()),
                           int(annual["tmp"].year.max()) + 1))
    print(f"  Years available: {all_years[0]}..{all_years[-1]}")

    def interp_years(da: xr.DataArray, years: list[int]) -> np.ndarray:
        out = np.full((len(years), n_cells), np.nan, dtype=np.float32)
        avail = set(int(y) for y in da.year.values)
        for i, yr in enumerate(years):
            if yr not in avail:
                continue
            layer = da.sel(year=yr)
            if "latitude" in layer.dims:
                layer = layer.rename({"latitude": "lat", "longitude": "lon"})
            out[i, :] = bilinear_to_points(layer, lat, lon)
        return out

    baseline_years = list(range(a.years_baseline[0], a.years_baseline[1] + 1))
    recent_years = list(range(a.years_recent[0], a.years_recent[1] + 1))

    print("Interpolating to CEA grid …")
    tmp_bs = np.nanmean(interp_years(annual["tmp"], baseline_years), axis=0)
    tmp_rc = np.nanmean(interp_years(annual["tmp"], recent_years), axis=0)
    pre_bs = np.nanmean(interp_years(annual["pre"], baseline_years), axis=0)
    pre_rc = np.nanmean(interp_years(annual["pre"], recent_years), axis=0)
    tmn_all = interp_years(annual["tmn"], all_years)
    tmx_all = interp_years(annual["tmx"], all_years)
    pre_all = interp_years(annual["pre"], all_years)

    with np.errstate(invalid="ignore"):
        T_cold = np.nanmin(tmn_all, axis=0)
        T_hot = np.nanmax(tmx_all, axis=0)
        P_dry = np.nanmin(pre_all, axis=0)
        P_wet = np.nanmax(pre_all, axis=0)

    pa = np.load(a.presence_absence, allow_pickle=True)
    species = list(pa["species"])
    prab_baseline = pa["prab_baseline"]

    print("Computing per-species limits …")
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

    T_range = T_max_spp - T_min_spp
    P_range = P_max_spp - P_min_spp

    TEI_bs = (tmp_bs[np.newaxis, :] - T_min_spp[:, np.newaxis]) / T_range[:, np.newaxis]
    TEI_rc = (tmp_rc[np.newaxis, :] - T_min_spp[:, np.newaxis]) / T_range[:, np.newaxis]
    PEI_bs = (pre_bs[np.newaxis, :] - P_min_spp[:, np.newaxis]) / P_range[:, np.newaxis]
    PEI_rc = (pre_rc[np.newaxis, :] - P_min_spp[:, np.newaxis]) / P_range[:, np.newaxis]

    out = a.output_dir / "climate_tei_pei.npz"
    np.savez_compressed(
        out,
        species=np.array(species),
        avgtemp_bs=tmp_bs.astype(np.float32),
        avgtemp_delta=(tmp_rc - tmp_bs).astype(np.float32),
        avgprecip_bs=pre_bs.astype(np.float32),
        avgprecip_delta=(pre_rc - pre_bs).astype(np.float32),
        TEI_bs=TEI_bs.astype(np.float32),
        TEI_delta=(TEI_rc - TEI_bs).astype(np.float32),
        PEI_bs=PEI_bs.astype(np.float32),
        PEI_delta=(PEI_rc - PEI_bs).astype(np.float32),
        T_min_spp=T_min_spp.astype(np.float32),
        T_max_spp=T_max_spp.astype(np.float32),
        P_min_spp=P_min_spp.astype(np.float32),
        P_max_spp=P_max_spp.astype(np.float32),
        n_x=n_x, n_y=n_y,
    )
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()
