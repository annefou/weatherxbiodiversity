# WeatherXBiodiversity: Soroye et al. (2020) Replication

Replication of [Soroye, Newbold & Kerr (2020, *Science*)](https://doi.org/10.1126/science.aax8591) for Iberian *Bombus* using open GBIF occurrence data and ERA5 climate reanalysis.

**Claim under test**: increasing frequency of temperatures exceeding historical baselines predicts local extinction of bumblebee species.

## Pipeline

| Step | Notebook | Input | Output |
|------|----------|-------|--------|
| 1 | `01_download_gbif.py` | GBIF API | `data/gbif_bombus_iberia.csv` |
| 2 | `02_download_era5.py` | CDS API | `data/era5_iberia_monthly_tmax.nc` |
| 3 | `03_climate_departure.py` | ERA5 monthly max | `data/era5_iberia_climate_departure.nc` |
| 4 | `04_spatial_join.py` | GBIF + departure | `results/soroye_replication_iberia.png` |

## Quick start

```bash
# Create environment
mamba env create -f environment.yml
mamba activate weatherxbio

# Run full pipeline
snakemake --cores 1

# Or run interactively
cd notebooks
jupytext --to notebook 01_download_gbif.py
jupyter lab
```

## Prerequisites

- CDS API key in `~/.cdsapirc` ([register here](https://cds.climate.copernicus.eu/))
- Internet access for GBIF and CDS downloads

## Data sources

- **Biodiversity**: [GBIF](https://www.gbif.org/) — *Bombus* occurrence records (Darwin Core)
- **Climate**: [ERA5 via CDS](https://cds.climate.copernicus.eu/) — daily max 2m temperature (CF conventions)

## Context

Prepared for the [BioHackathon Europe 2026](https://biohackathon-europe.org/) project *WeatherXBiodiversity*, which packages cross-domain biodiversity × climate data as [ARC](https://arc-rdm.org/) / [RO-Crate](https://www.researchobject.org/ro-crate/) FAIR Digital Objects.
