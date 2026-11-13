# ERA5 retrieval (`era5_retrieve.py`)

Streams hourly ERA5 climate surface data from ECMWF's ARCO Zarr store and saves only daily or monthly statistics (mean, sum, min, max, and monthly means of daily min/max). It works with any variable in the store, any years from 1940, and any region, given either as a bounding box or as the area around a set of occurrence points (such as GBIF output). The hourly data is never written to disk.

## Description

Streams hourly ERA5 single-level data from ECMWF's ARCO Zarr store and saves
daily or monthly statistics. Only the requested statistics are written; the
hourly data are never saved. 

- Any surface variable of the store (`t2m`, `d2m`, `tp`, `msl`, `u10`, `v10`,
  `ssrd`, ...), any years from 1940.
- Area: one or more boxes `--area N W S E` (repeat for several boxes), or the
  store tiles around occurrence points (`--occurrences`, `--buffer`).
- `--frequency monthly` (default): `mean`, `sum`, `daily_min_mean`,
  `daily_max_mean`, `daily_max_max` →
  `era5_<var>_<stat>_monthly_<start>_<end>.nc`.
- `--frequency daily`: `mean`, `sum`, `min`, `max` per UTC day →
  `era5_<var>_<stat>_daily_<year>.nc`.
- Native ERA5 units (K, m, ...). ARCO only offers hourly ERA5: daily and
  monthly values are computed from it and reproduce the CDS daily-statistics
  and monthly-means products.
- Requests are paced and retried, because the store rate-limits per CDS key.

## Preparation: CDS API credentials

Copy `credentials.example.json` to `credentials.json` and put your CDS
API key in it (from https://cds.climate.copernicus.eu/profile):

```json
{"key": "your-cds-api-key"}
```

`cds_credentials.json` is in .gitignore to prevent it from being committed accidentally.

If the workflow is run directly without `--credentials-file`, the script falls back to the environment variable `CDSAPI_KEY` or the configuration file `~/.cdsapirc`.

## Use script directly with CLI arguments

With example parameters:

```bash
python era5_retrieve.py \
  --variables '{"t2m": ["mean", "daily_min_mean", "daily_max_mean"], "tp": ["sum"]}' \
  --frequency monthly \
  --years 2020 2020 \
  --area 41.5 -4.5 39.5 -2.5 \
  --credentials-file credentials.json \
  --output-dir results
```

## Validate the CWL Tool description

```bash
cwltool --validate workflow.cwl
```

## Run the Tool

Small test (2020, a 2 × 2° box around Madrid, about 30 s):

```bash
cwltool workflow.cwl test_era5_retrieve.yml
```

Outputs, one named output per file (monthly): 

* `t2m_mean`
* `t2m_daily_min_mean`
* `t2m_daily_max_mean`
* `t2m_daily_max_max`
* `tp_sum`

Each is optional and present only if requested in `variables`. The default
`variables` give `t2m_mean`, `t2m_daily_min_mean`, `t2m_daily_max_mean` and
`tp_sum`: these are the necessary files for the ERA5_Preprocessing workflow.

A `Dockerfile` is provided which is the recommended environment to run the workflow.

