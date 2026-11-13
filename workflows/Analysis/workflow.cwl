cwlVersion: v1.2
class: Workflow

label: WeatherXBiodiversity analysis workflow
doc: |
  End-to-end analysis chain of the Soroye et al. (2020) replication:
  study records (01: continent, erroneous observations, periods and
  seasons, on the GBIF_Preprocessing output), gridded presence/absence (02) and sampling
  effort (03), climate normals and TEI/PEI indices (04), GLMM data
  assembly (05a), variational-Bayes GLMM of occurrence on the climate
  index (05b) and forest plot (06). Study parameters (taxon, region,
  years, grid, climate source, seed, plot labels) are declared once
  here and dispatched to the steps, so they cannot drift apart.
  The Bayesian (bambi) variant of the regression is a separate tool,
  05-bayesian-glmm.cwl, run standalone.

requirements:
  StepInputExpressionRequirement: {}

hints:
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]

inputs:
  # step 01 - study records
  occurrences:
    type: File
    doc: occurrences_clean.csv from GBIF_Preprocessing
  err_obs: File
  continent: int
  # steps 02-04 - spatial study definition (grid_bbox in projection
  # meters XOR bbox_latlon in degrees)
  grid_resolution_m: int
  grid_bbox: string[]?
  bbox_latlon: string[]?
  period_baseline: int
  period_recent: int
  # step 04 - climate definition
  climate_dir: Directory
  climate_source:
    type: string
    default: era5
    doc: File prefix of the monthly climate files, <source>_<var>_monthly_*.nc
  years_baseline: string[]
  years_recent: string[]
  # step 05b - fit determinism
  seed: int
  # step 06 - plot labels
  plot_title: string
  plot_subtitle: string
  plot_color: string

steps:

  clean:
    run: 01-study-records.cwl
    in:
      occurrences: occurrences
      err_obs: err_obs
      continent: continent
      output_dir:
        valueFrom: "out_01"
    out: [ clean_records ]

  pa:
    run: 02-presence-absence.cwl
    in:
      records: clean/clean_records
      grid_resolution_m: grid_resolution_m
      grid_bbox: grid_bbox
      bbox_latlon: bbox_latlon
      period_baseline: period_baseline
      period_recent: period_recent
      output_dir:
        valueFrom: "out_02"
    out: [ presence_absence ]

  sampling:
    run: 03-sampling-continent.cwl
    in:
      records: clean/clean_records
      grid_resolution_m: grid_resolution_m
      grid_bbox: grid_bbox
      bbox_latlon: bbox_latlon
      period_baseline: period_baseline
      period_recent: period_recent
      output_dir:
        valueFrom: "out_03"
    out: [ sampling_continent ]

  climate:
    run: 04-climate-tei-pei.cwl
    in:
      presence_absence: pa/presence_absence
      climate_dir: climate_dir
      climate_source: climate_source
      years_baseline: years_baseline
      years_recent: years_recent
      grid_resolution_m: grid_resolution_m
      grid_bbox: grid_bbox
      bbox_latlon: bbox_latlon
      output_dir:
        valueFrom: "out_04"
    out: [ climate_tei_pei ]

  glmm_data:
    run: 05a-build-data-glmm.cwl
    in:
      presence_absence: pa/presence_absence
      sampling_continent: sampling/sampling_continent
      climate_tei_pei: climate/climate_tei_pei
      output_dir:
        valueFrom: "out_05a"
    out: [ data_glmm ]

  glmm_vb:
    run: 05b-glmm-extinction.cwl
    in:
      data: glmm_data/data_glmm
      seed: seed
      output_dir:
        valueFrom: "out_05b"
    out: [ logistic_summary, posterior_vb_summary ]

  forest:
    run: 06-forest-plot.cwl
    in:
      summary: glmm_vb/posterior_vb_summary
      title: plot_title
      subtitle: plot_subtitle
      color: plot_color
      output_dir:
        valueFrom: "out_06"
    out: [ forest ]

outputs:
  clean_records:
    type: File
    outputSource: clean/clean_records
  presence_absence:
    type: File
    outputSource: pa/presence_absence
  sampling_continent:
    type: File
    outputSource: sampling/sampling_continent
  climate_tei_pei:
    type: File
    outputSource: climate/climate_tei_pei
  data_glmm:
    type: File
    outputSource: glmm_data/data_glmm
  logistic_summary:
    type: File
    outputSource: glmm_vb/logistic_summary
  posterior_vb_summary:
    type: File
    outputSource: glmm_vb/posterior_vb_summary
  forest_plot:
    type: File
    outputSource: forest/forest

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
