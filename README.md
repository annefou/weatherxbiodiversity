# WeatherXBiodiversity: Soroye et al. (2020) Replication

[![Source DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19756173.svg)](https://doi.org/10.5281/zenodo.19756173)
[![Docker image DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19756286.svg)](https://doi.org/10.5281/zenodo.19756286)
[![GBIF DOI](https://img.shields.io/badge/GBIF-10.15468%2Fdl.3frmsq-blue.svg)](https://doi.org/10.15468/dl.3frmsq)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Replication of [Soroye, Newbold & Kerr (2020, *Science*)](https://doi.org/10.1126/science.aax8591) for Iberian *Bombus* using open GBIF occurrence data and CRU TS climate.

**Claim under test**: increasing frequency of temperatures exceeding historical baselines predicts local extinction of bumblebee species.

## Structure

> [!IMPORTANT]
> The Copernicus API requires users to manually accept the licence for a dataset before it can be retrieved.
> If a `403` error with the text `requested licences not accepted` is encountered, please login to
> the Copernicus CDS website and manually accept the required licence. Accepting a licence in this way
> enables the download of all datasets using this licence without further manual action being required.

```
weatherxbiodiversity/
├── notebooks/                  Upstream data-download notebooks (jupytext)
│   ├── 01_download_gbif.py     GBIF Bombus records for Iberia (~36k)
│   ├── 01b_gbif_download_doi.py
│   │                           Citable GBIF download (DOI 10.15468/dl.3frmsq)
│   ├── 02_download_era5.py     ERA5 monthly max T via the CDS queue (~27 h)
│   ├── 02b_stream_era5_arco.py Same field streamed from ECMWF ARCO Zarr (~1 min)
│   └── 02c_stream_era5_monthly_climate.py
│                               ERA5 monthly tmp/tmn/tmx/pre with CRU TS definitions (ARCO Zarr)
├── data/                       Processed data
├── reference/Bumblebee_repo_wbombusdat/
│                               Soroye et al.'s Figshare dataset (R scripts + CRU TS)
└── soroye_port/                Faithful Python port of Soroye's R pipeline
    ├── 01_clean_data.py + 01_clean_data_iberia.py
    ├── 02_presence_absence.py
    ├── 03_sampling_continent.py
    ├── 04_climate_tei_pei.py
    ├── 05b_regression_statsmodels.py
    ├── plot_forest.py
    ├── outputs/                Phase 2 run on Soroye's global data (validation)
    ├── outputs_iberia/         Phase 3 run on Iberia GBIF + CRU TS (replication)
    ├── phase2_forest.png
    └── phase3_forest.png
```

## Method

The port in `soroye_port/` mirrors Soroye et al.'s R scripts 1–5:

1. Clean bombus occurrences, apply Kerr-2015 species filter and IUCN exclusion list
2. Rasterise onto the 100 km cylindrical-equal-area (CEA) grid per (species × period × season), infer absences from other-species presence
3. Compute per-(period × season) sampling effort (distinct LYID counts per cell), sum across all 6 seasons, set continent raster
4. Compute per-species Thermal Exposure Index (TEI) and Precipitation Exposure Index (PEI) baseline + delta using CRU TS 3.24.01 monthly climate bilinearly interpolated onto the CEA grid
5. Mixed-effects logistic regression `extinction ~ continent + sc_sampling + sc_TEI_bs + sc_TEI_delta + sc_TEI_bs:sc_TEI_delta + sc_PEI_bs + sc_PEI_delta + sc_PEI_bs:sc_PEI_delta + sc_TEI_bs:sc_PEI_bs + sc_TEI_delta:sc_PEI_delta + (1|species)` via statsmodels variational Bayes

## Results

**Phase 2** — Python port run on Soroye's own data (global, 66 species, CRU TS, 13 614 rows):

- `sc_TEI_delta` = **+0.15 [0.12, 0.19]** — positive sign matches Soroye. Port validated.

**Phase 3** — same Python code on Iberia GBIF + CRU TS (31 species, 528 rows):

- `sc_TEI_delta` = **+0.48 [0.27, 0.69]** — **Soroye's claim replicates on Iberia**.

See `soroye_port/phase2_forest.png` and `phase3_forest.png` for full coefficient forest plots.

## Quick start

### Workflow: Soroye 2020 replication on Iberia with ERA5

Five steps under `workflows/`, each with its own Snakemake file (`rules.smk`),
mirroring the [ARC](https://git.nfdi4plants.org/weil/WeatherXBiodiversity_Soroye2020).
Parameters live in `config/phase3_iberia.yaml`.

| Step | Snakemake target | Does |
|---|---|---|
| `GBIF_Retrieval` | `gbif_download` | Occurrences by GBIF download key / DOI (default 10.15468/dl.3frmsq), or a new request |
| `ERA5_Retrieval` | `era5_download` | Monthly ERA5 statistics (t2m mean, daily min, daily max; tp sum), 1940–2014, streamed from ECMWF's ARCO Zarr store |
| `GBIF_Preprocessing` | `gbif_preprocessing` | Clean + grid the occurrences (`soroye_port/01_clean_data_iberia.py`, `02`, `03`) |
| `ERA5_Preprocessing` | `era5_preprocessing` | Monthly `tmp`, `tmn`, `tmx`, `pre` (°C, mm) with CRU TS definitions |
| `Analysis` | `analysis` | Exposure indices (`04`, ERA5 climate, baseline 1940–1974), model table (`05a`), regression (`05b`) |

```bash
# 1. Environment, pinned by pixi.lock (Linux, macOS, Windows)
pixi install

# 2. Soroye's Figshare bundle, ~1.1 GB (only its species tables are used).
#    Figshare refuses scripted downloads: download it in a browser from
#    https://doi.org/10.6084/m9.figshare.9956471 and save it as
#    reference/Bumblebee_repo.zip (or set FIGSHARE_ZIP=/path/to/zip).

# 3. Credentials, required for the steps that use them (files are gitignored):
cp credentials/cds_credentials.example.json credentials/cds_credentials.json    # ERA5: your CDS API key
cp credentials/gbif_credentials.example.json credentials/gbif_credentials.json  # only for a new GBIF download
#    The default GBIF download (DOI 10.15468/dl.3frmsq) is public: no login needed.

# 4. Run all steps, or one step at a time
pixi run snakemake --cores 1
pixi run snakemake --cores 1 gbif_download   # gbif_download, era5_download, gbif_preprocessing,
                                             # era5_preprocessing, analysis
```

Results: `soroye_port/run/phase3_era5/posterior_vb_summary.csv` (gitignored).

The climate source is swappable: `Analysis` reads monthly climate in a common
format ([`workflows/CLIMATE_INPUT.md`](workflows/CLIMATE_INPUT.md)), selected by
the `climate` section of the config. Another source (e.g. Destination Earth
Climate DT or CMIP6 for future scenarios) only needs its own retrieval and
preprocessing steps producing the same files.
The ERA5 download is paced (the ARCO store rate-limits per key) and takes the
longest; the other steps take minutes.

### Manual steps (previous instructions)

```bash
# Create environment
mamba env create -f environment.yml
mamba activate weatherxbio

# Download data (one-off, slow)
cd notebooks
python 02b_stream_era5_arco.py           # ERA5 from ECMWF's ARCO Zarr (CDS key, ~1 min)
# or the same field via the CDS queue (66 one-year requests, ~27 h):
# python 02_download_era5.py
cd ..
# and (GBIF — needs GBIF_USER/GBIF_PWD/GBIF_EMAIL set)
cd notebooks
# 01b mints the citable DOI and saves metadata, it does NOT download the data:
python 01b_gbif_download_doi.py
# fetch the zipped snapshot it just registered, and unpack where the pipeline expects it:
mkdir -p ../data/gbif_dl
curl -L -o ../data/gbif_dl/<download_key>.zip \
  "https://api.gbif.org/v1/occurrence/download/request/<download_key>.zip"
unzip -q ../data/gbif_dl/<download_key>.zip -d ../data/gbif_dl/
# (the exact <download_key> and URL are printed by 01b)
cd ..

# Run the port end to end
snakemake --cores 1
# or step by step:
cd soroye_port
python 01_clean_data_iberia.py
OUT_SUBDIR=outputs_iberia python 02_presence_absence.py
OUT_SUBDIR=outputs_iberia python 03_sampling_continent.py
OUT_SUBDIR=outputs_iberia python 04_climate_tei_pei.py
OUT_SUBDIR=outputs_iberia python 05a_build_dataGLMM.py
OUT_SUBDIR=outputs_iberia python 05b_regression_statsmodels.py
python plot_forest.py
```

Scripts 02–05 take an `OUT_SUBDIR` env var (default `outputs`) to switch between the Phase-2 (global Soroye) and Phase-3 (Iberia) runs.

## Prerequisites

- CDS API key in `~/.cdsapirc` ([register here](https://cds.climate.copernicus.eu/))
- Internet access for GBIF and CDS
- Soroye et al.'s Figshare dataset (~1.1 GB zip) at `reference/Bumblebee_repo.zip`, extracted to `reference/Bumblebee_repo_wbombusdat/` — includes the CRU TS climate required by script 04

## Data sources

- **Biodiversity**: [GBIF Occurrence Download — *Bombus* in Spain + Portugal, georeferenced, no geospatial issues, 36,560 records](https://doi.org/10.15468/dl.3frmsq) — citation: *GBIF.org (2026-04-25) GBIF Occurrence Download https://doi.org/10.15468/dl.3frmsq* — DOI minted by `notebooks/01b_gbif_download_doi.py` (which saves the metadata only, not the data); the zip fetched from `https://api.gbif.org/v1/occurrence/download/request/0006204-260423192947929.zip` and unpacked in `data/gbif_dl/`
- **Climate**: CRU TS 3.24.01 monthly (from Soroye's Figshare deposit) — used for both Phase 2 and Phase 3 to isolate region as the only swap variable
- **Climate (future extension)**: [ERA5 via CDS](https://cds.climate.copernicus.eu/) — for a future sensitivity run; either downloaded via the CDS queue (`notebooks/02_download_era5.py`) or streamed from ECMWF's ARCO Zarr store of [`reanalysis-era5-single-levels`](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) (`notebooks/02b_stream_era5_arco.py`, `notebooks/02c_stream_era5_monthly_climate.py`)

## How to cite

If you use this software, please cite both this repository (via its Zenodo
concept DOI, which always resolves to the latest version) and Soroye et al.
(2020).

```
Fouilloux, A. (2026). WeatherXBiodiversity: Soroye et al. (2020) Replication
for Iberian Bombus (v0.2.0). Zenodo. https://doi.org/10.5281/zenodo.19756173
```

BibTeX:

```bibtex
@software{fouilloux_weatherxbiodiversity_2026,
  author    = {Fouilloux, Anne},
  title     = {{WeatherXBiodiversity: Soroye et al. (2020) Replication for Iberian Bombus}},
  year      = {2026},
  version   = {v0.2.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.19756173},
  url       = {https://doi.org/10.5281/zenodo.19756173}
}
```

The DOI `10.5281/zenodo.19756173` is the **concept DOI** — it always resolves
to the latest release. Specific version DOIs are available on the
[Zenodo record page](https://doi.org/10.5281/zenodo.19756173).

The accompanying Docker container image is archived separately at
[10.5281/zenodo.19756286](https://doi.org/10.5281/zenodo.19756286).

See [`CITATION.cff`](CITATION.cff) for machine-readable citation metadata.

## Context

Prepared for the [BioHackathon Europe 2026](https://biohackathon-europe.org/) project *WeatherXBiodiversity*, which packages cross-domain biodiversity × climate data as [ARC](https://arc-rdm.org/) / [RO-Crate](https://www.researchobject.org/ro-crate/) FAIR Digital Objects.
