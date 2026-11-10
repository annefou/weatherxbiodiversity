# Common climate input format

`workflows/Analysis` reads monthly climate in one fixed format. Any climate
source (ERA5 today; Destination Earth Climate DT or CMIP6 later) plugs in by
producing files in this format with its own retrieval and preprocessing steps,
and pointing the `climate` section of the config at them. The analysis code
does not change.

```
ERA5        ─ ERA5_Retrieval ─ ERA5_Preprocessing ─┐
Climate DT  ─ <its retrieval> ─ <its preprocessing> ─┼→ monthly tmp/tmn/tmx/pre → Analysis
CMIP6       ─ <its retrieval> ─ <its preprocessing> ─┘
```

## Files

One NetCDF file per variable in the climate directory (`climate.dir`):

```
<source>_<var>_monthly_<start>_<end>.nc
```

`<source>` is the label set as `climate.source` (e.g. `era5`, `climatedt`,
`cmip6`); `<start>`/`<end>` are the first and last year. Exactly one file per
variable must match.

## Variables (CRU TS 3.24.01 definitions)

| `<var>` | Definition | Units (`units` attribute) |
|---|---|---|
| `tmp` | monthly mean temperature (2 m) | `degC` |
| `tmn` | monthly mean of daily minimum temperature | `degC` |
| `tmx` | monthly mean of daily maximum temperature | `degC` |
| `pre` | monthly total precipitation | `mm` |

Daily minimum / maximum must come from the full diurnal cycle (hourly data for
ERA5), not from a few snapshots per day, which underestimate the extremes.

## Grid and time

- Dimensions exactly `(time, lat, lon)`; one value per calendar month.
- `lat`, `lon`: regular grid in degrees, **geodetic WGS84** latitude and
  longitude in −180..180 (ascending or descending both work). Values outside
  the area of interest may be NaN, but every grid point needed to interpolate
  onto the 100 km equal-area cells holding occurrences must be filled.
- `time`: one time stamp per month (any day within the month).
- All months of every year in `climate.baseline_years` and
  `climate.recent_years` must be present. The thermal / precipitation limits
  use every year in the file.

`soroye_port/04_climate_tei_pei.py` refuses files with other units or
dimensions.

## Adding a source: notes

- **ERA5** (`workflows/ERA5_Retrieval`, `workflows/ERA5_Preprocessing`):
  hourly ARCO store → monthly statistics (K, m) → this format.
- **Destination Earth Climate DT** (lessons from the other hackathon projects
  that use it; working code in `konya-wetlands-water-surface`,
  `anatolia-jerboa-climate-sdm`, `donana-hydroperiod-evidence`,
  `extreme-precipitation-climatedt-replication` and GRID4EARTH
  `healpix-connector`):
  - Generation 2 via Polytope (`class=d1, dataset=climate-dt, generation=2`):
    historical `activity=baseline, experiment=hist` 1990–2014, scenario
    `activity=projections, experiment=SSP3-7.0` 2015–2049; one realization.
    The endpoint depends on the model: IFS-NEMO on
    `polytope.mn5.apps.dte.destination-earth.eu`, IFS-FESOM on
    `polytope.lumi.apps.dte.destination-earth.eu`.
  - Monthly stream `clmn` has `avg_2t` (228004) and `avg_tprate` (235055) —
    enough for `tmp` and `pre` (rate × 86400 × days → mm) — but **no monthly
    min / max temperature** (`mx2t24`/`mn2t24` silently resolve to other
    fields). For `tmn` / `tmx` either aggregate hourly `clte` `2t` to daily
    min / max (much larger volume), or use a delta method on the historical
    source (add the Climate DT change in mean temperature to its tmn / tmx, as
    in `anatolia-jerboa-climate-sdm`). Request parameters by numeric id and
    check the returned paramId.
  - `tp` / `228` is refused; precipitation is `avg_tprate` (kg m⁻² s⁻¹). In
    hourly `clte` feature requests, list the 24 hours explicitly: a
    `/to/../by/..` range silently returns only the first hour.
  - Cut the area server-side (`polygon` or `boundingbox` feature; MARS cannot
    crop HEALPix with `area`). Keep transfers well below ~500 MB and at most 5
    concurrent requests; retry with back-off.
  - Climate DT is on a native **spherical** HEALPix grid. Never match its cell
    ids to WGS84 cells; resample from coordinates to geodetic WGS84 with
    `healpix-geo` / `healpix-resample` (`ellipsoid="WGS84"`, authalic
    latitude), e.g. healpix-connector's `BilinearConservative` — not `healpy`
    (spherical latitudes; up to ~0.13°, ~14 km, off at Iberian latitudes).
  - Generation 2 starts in 1990, so it cannot supply Soroye's historical
    baseline: use it for future periods, with the species limits and model
    fit from the historical source.
  - Raw Climate DT data must not be redistributed; DestinE attribution is
    required on derived outputs.
- **CMIP6**: the monthly `Amon` table already has `tas`, `tasmin`, `tasmax`,
  `pr` (K, K, K, kg m⁻² s⁻¹), matching these definitions after unit conversion
  and regridding to a regular lat/lon grid.
