# ERA5 preprocessing (`era5_to_climate.py`)

Converts the monthly ERA5 statistics into the four climate variables the analysis expects: mean, minimum and maximum temperature in °C and total precipitation in mm. Its output format is the common climate input, so another source (such as Destination Earth Climate DT or CMIP6) can replace this step by writing the same files.

## Description

Turns the monthly ERA5 statistics from `ERA5_Retrieval` into the four monthly
climate variables used by the analysis (the exposure indices of Soroye et al.
2020): monthly mean, mean daily minimum and mean daily maximum temperature, and
monthly total precipitation. Background on the method:
[Methods](https://annefou.github.io/weatherxbiodiversity/methods/) and
[Phase 3](https://annefou.github.io/weatherxbiodiversity/phase3/) of the
WeatherXBiodiversity Jupyter Book.

| Output | Definition | From ERA5 (`ERA5_Retrieval` output) | Units |
|---|---|---|---|
| `tmp` | monthly mean temperature (2 m) | `t2m_mean` | °C |
| `tmn` | monthly mean of daily minimum temperature | `t2m_daily_min_mean` | °C |
| `tmx` | monthly mean of daily maximum temperature | `t2m_daily_max_mean` | °C |
| `pre` | monthly total precipitation | `tp_sum` | mm |

Output files: `era5_<var>_monthly_<start>_<end>.nc`, dimensions
`(time, lat, lon)`, geodetic WGS84 latitude / longitude; `<start>` / `<end>` are
the first and last year in the data. Daily minimum / maximum come from the full
hourly cycle (UTC days), not from a few snapshots per day.

## The common climate input format

The analysis reads only these four files. Any other climate source
(Destination Earth Climate DT, CMIP6, ...) can replace ERA5 by writing the same
files: same variable names, definitions, `units` attribute (`degC` for
`tmp`/`tmn`/`tmx`, `mm` for `pre`) and dimensions `(time, lat, lon)`, one value
per calendar month (points outside the area of interest may be NaN). Notes for
Climate DT: its monthly stream has `avg_2t` and `avg_tprate` (enough for `tmp`
and `pre`) but no monthly minimum / maximum temperature, so `tmn` / `tmx` come
from hourly `2t` or a delta method on the historical source; precipitation is
`avg_tprate` in kg m⁻² s⁻¹ (monthly mm = rate × 86400 × days); its HEALPix grid
must be resampled to geodetic WGS84 with `healpix-geo` / `healpix-resample`
(`ellipsoid="WGS84"`), never by matching cell ids.

## Use script directly with CLI arguments

With the four files from `ERA5_Retrieval`:

```bash
python era5_to_climate.py \
  --t2m-mean era5_t2m_mean_monthly_1940_2014.nc \
  --t2m-daily-min-mean era5_t2m_daily_min_mean_monthly_1940_2014.nc \
  --t2m-daily-max-mean era5_t2m_daily_max_mean_monthly_1940_2014.nc \
  --tp-sum era5_tp_sum_monthly_1940_2014.nc \
  --output-dir results
```

or with a directory holding them: `--input-dir <dir> --years 1940 2014`.

## Validate the CWL Tool description

```bash
cwltool --validate workflow.cwl
```

## Run the Tool

Small test on the 2020 outputs of the `ERA5_Retrieval` test job (a 2 × 2° box
around Madrid), stored in `test_data/` (a few seconds, no credentials needed):

```bash
cwltool workflow.cwl test_era5_preprocessing.yml
```

Inputs are the four `File`s named as the `ERA5_Retrieval` tool's outputs
(`t2m_mean`, `t2m_daily_min_mean`, `t2m_daily_max_mean`, `tp_sum`); outputs are
one named `File` per variable: `tmp`, `tmn`, `tmx`, `pre`.

The tool's `Dockerfile` is used as a hint (`cwltool` with Docker, or
`cwltool --podman`).
