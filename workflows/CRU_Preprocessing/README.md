# CRU_Preprocessing (`cru_to_climate.py`)

Joins the decadal files of `CRU_Retrieval` into the common climate input
format read by the Analysis (the same layout as `ERA5_Preprocessing`):
`cru_{tmp,tmn,tmx,pre}_monthly_<start>_<end>.nc`, dims `(time, lat, lon)`,
units `degC` (tmp, tmn, tmx) and `mm` (pre).

CRU TS already holds the variables of Soroye et al. (2020) (monthly mean,
mean daily minimum and maximum temperature, monthly precipitation): no
conversion is needed. Decades absent from the input stay absent.

```bash
python cru_to_climate.py --input-dir data/cru --output-dir data/climate/cru
```

Snakemake rule: `cru_preprocessing`; the Analysis then runs with
`--climate-source cru`.
