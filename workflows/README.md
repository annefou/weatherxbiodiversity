# Workflow steps

The same steps as in the ARC
[WeatherXBiodiversity_Soroye2020](https://git.nfdi4plants.org/lifewatch-eric/WeatherXBiodiversity_Soroye2020)
(DataHUB), copied from its `workflows/` folder: each step has its script(s), a
CWL tool or workflow description (`workflow.cwl`), a `Dockerfile` and a README.
Here each step also has a `rules.smk` (Snakemake), included by the root
`Snakefile` and parameterised by `config/iberia.yaml`.

| Step | Snakemake rules | Script(s) |
|---|---|---|
| `GBIF_Retrieval` | `gbif_metadata`, `gbif_download` | `00-existing-download.py` (key/DOI, no account) or `00-submit-request.py`; `01-download.py` |
| `GBIF_Preprocessing` | `gbif_preprocessing` | `clean_occurrences.py` |
| `ERA5_Retrieval` | `era5_retrieval` | `era5_retrieve.py` |
| `ERA5_Preprocessing` | `era5_preprocessing` | `era5_to_climate.py` |
| `Analysis` | `analysis_01_study_records` … `analysis_06_forest_plot` | `01_study_records.py` … `06_forest_plot.py` |

To run a step with CWL instead (as in the ARC): `cwltool workflows/<Step>/workflow.cwl <job.yml>`;
the whole chain is `workflows/orchestration.cwl`. The step READMEs come from the
ARC and refer to its `runs/` folders for example runs.

`GBIF_Retrieval/00-existing-download.py` is specific to this repository (it
reuses a published download); everything else is identical to the ARC
(commit 38e122e).
