# WeatherXBiodiversity: Soroye et al. (2020) Replication

[![Source DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19756173.svg)](https://doi.org/10.5281/zenodo.19756173)
[![Docker image DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19756286.svg)](https://doi.org/10.5281/zenodo.19756286)
[![GBIF DOI](https://img.shields.io/badge/GBIF-10.15468%2Fdl.3frmsq-blue.svg)](https://doi.org/10.15468/dl.3frmsq)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Replication of [Soroye, Newbold & Kerr (2020, *Science*)](https://doi.org/10.1126/science.aax8591) for Iberian *Bombus* using open GBIF occurrence data, with the paper's climate data (CRU TS) and with ERA5.

**Claim under test**: increasing frequency of temperatures exceeding historical baselines predicts local extinction of bumblebee species.

## Structure

```
weatherxbiodiversity/
├── Snakefile                  The workflow: GBIF + climate -> analysis (pixi run snakemake)
├── config/iberia.yaml         Study parameters (GBIF download, years, ERA5 boxes, grid, seed)
├── workflows/                 One folder per step, same scripts and CWL as the ARC
│   ├── GBIF_Retrieval/        Existing GBIF download (key/DOI) or a new request
│   ├── GBIF_Preprocessing/    Generic cleaning of the occurrence table
│   ├── ERA5_Retrieval/        Monthly ERA5 statistics from ECMWF's ARCO Zarr store
│   ├── ERA5_Preprocessing/    Monthly tmp/tmn/tmx/pre (common climate input format)
│   ├── CRU_Retrieval/         CRU TS 3.24.01 (the paper's climate data) from UEA
│   ├── CRU_Preprocessing/     The same variables from CRU TS (common climate input format)
│   ├── Analysis/              01 study records ... 06 forest plot (Soroye et al. 2020)
│   ├── Comparison/            The climate sources side by side
│   └── orchestration.cwl      The whole chain in CWL
├── studies/soroye2020/        Study tables (species list, synonyms, dropped taxa,
│                              erroneous observations; CC BY 4.0, Soroye et al. deposit)
├── credentials/               Templates; your credentials files here are git-ignored
├── soroye_port/               Original Python port behind Phases 2 and 3 of the book
│                              (its own Snakefile: snakemake -s soroye_port/Snakefile)
├── notebooks/                 Data-download notebooks of the original port (jupytext)
└── *.md, myst.yml             The Jupyter Book (https://annefou.github.io/weatherxbiodiversity/)
```

The workflow is the same as in the
[ARC](https://git.nfdi4plants.org/lifewatch-eric/WeatherXBiodiversity_Soroye2020)
(DataHUB): each step has its script, a CWL tool description and a Dockerfile;
here they are run with Snakemake (each step's `rules.smk`), in the ARC with CWL.

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

**Climate data sensitivity** — the workflow (same Iberia GBIF records as Phase 3, same code), with the paper's climate data and with ERA5:

| Climate data | `sc_TEI_delta` | Model rows | Claim |
|---|---|---|---|
| CRU TS 3.24.01 (paper) | **+0.48 [0.26, 0.69]** | 528 | replicates |
| ERA5 (1940–2014) | **−0.05 [−0.24, 0.14]** | 679 | does not replicate |

The regional replication of Soroye's claim depends on the climate dataset.
CRU TS is land-only, so the ERA5 run also includes coastal grid cells (679
instead of 528 model rows). See `results/iberia/comparison/` after a run.

See `soroye_port/phase2_forest.png` and `phase3_forest.png` for full coefficient forest plots.

## Quick start

```bash
# 1. Environment, pinned by pixi.lock (Linux, macOS, Windows)
pixi install

# 2. CDS API key for ERA5 (https://cds.climate.copernicus.eu/profile; accept the
#    ERA5 licence on the CDS website first). The file is git-ignored.
cp credentials/cds_credentials.example.json credentials/cds_credentials.json
#    then put your key in it: {"key": "..."}

# 3. Run the whole workflow: GBIF, CRU TS (the paper's climate data) and ERA5,
#    the Analysis with each, and the comparison (the ERA5 retrieval takes about 1.5 hours)
pixi run snakemake --cores 1
pixi run snakemake --cores 1 -n                  # dry run
pixi run snakemake --cores 1 gbif_preprocessing  # one step (rule names in workflows/*/rules.smk)
```

The GBIF occurrences are the published Phase 3 download
([10.15468/dl.3frmsq](https://doi.org/10.15468/dl.3frmsq)), fetched without a
GBIF account. For a new download, set `gbif.download: null` in
`config/iberia.yaml` and provide `credentials/gbif_credentials.json`.

Results go to `results/iberia/` (git-ignored): `gbif/occurrences_clean.csv`,
`common/` (study records, presence/absence, sampling effort); per climate
source, `cru/` and `era5/` (TEI/PEI, model table, `posterior_vb_summary.csv`,
`forest.png`); and `comparison/` (`coefficients.csv`, `forest_comparison.png`).
Downloads go to `data/`.

## Prerequisites

- [pixi](https://pixi.sh) (installs Python, Snakemake and all packages from `pixi.lock`)
- an internet connection (GBIF download, ERA5 from ECMWF's ARCO store)
- a [CDS account](https://cds.climate.copernicus.eu/) and its API key, with the
  ERA5 licence accepted (otherwise the store answers `403`)
- a [GBIF account](https://www.gbif.org) only for a new GBIF download

## Data sources

- **Biodiversity**: [GBIF Occurrence Download, *Bombus* in Spain and Portugal, georeferenced, no geospatial issues, 36,560 records](https://doi.org/10.15468/dl.3frmsq). Citation: *GBIF.org (2026-04-25) GBIF Occurrence Download https://doi.org/10.15468/dl.3frmsq* (licence CC BY-NC 4.0).
- **Climate, workflow**: [ERA5 hourly data on single levels](https://doi.org/10.24381/cds.adbb2d47) (CC BY 4.0), 1940–2014, streamed from ECMWF's ARCO Zarr store and aggregated to monthly statistics.
- **Climate, the paper's data**: [CRU TS 3.24.01](https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_3.24.01/) monthly (Open Database Licence), as used by Soroye et al. (2020), downloaded from the University of East Anglia by the workflow (Phases 2 and 3 of the book used the copy in their data deposit, via `soroye_port/`).
- **Study tables**: from the data deposit of Soroye et al. (2020), [10.6084/m9.figshare.9956471](https://doi.org/10.6084/m9.figshare.9956471) (CC BY 4.0), in `studies/soroye2020/`.

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
