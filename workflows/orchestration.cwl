cwlVersion: v1.2
class: Workflow

label: Full WeatherXBiodiversity workflow
doc: |
  End-to-end replication chain, from data retrieval to forest plot, with no
  pre-downloaded data: GBIF retrieval (00-submit-request + 01-download) ->
  GBIF preprocessing (cleaned occurrences) -> Analysis 01; ERA5 retrieval (ECMWF ARCO) ->
  ERA5 preprocessing -> climate directory -> Analysis 04; then
  Analysis 01 -> 02 -> 03 -> 04 -> 05a -> 05b -> 06.
  Study parameters (taxon, region, years, grid, climate windows, seed, plot
  labels) are declared once here and dispatched to the steps.

requirements:
  - class: SubworkflowFeatureRequirement
  - class: StepInputExpressionRequirement

hints:
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]

inputs:
  # retrieval credentials
  gbif_credentials: File
  cds_credentials: File
  # GBIF study definition
  genus: string
  genus_key: int
  countries: string
  # ERA5 study definition (retrieval boxes, years)
  era5_area:
    type:
      type: array
      items:
        type: array
        items: float
  era5_years: int[]
  # taxonomic study definition (GBIF_Preprocessing)
  species_list: File?
  drop_species: File?
  synonyms: File?
  clean_years: int[]?
  # study records (Analysis 01)
  err_obs: File
  continent: int
  # spatial study definition (Analysis 02-04; grid_bbox in projection
  # meters XOR bbox_latlon in degrees)
  grid_resolution_m: int
  grid_bbox: string[]?
  bbox_latlon: string[]?
  period_baseline: int
  period_recent: int
  # climate windows (Analysis 04)
  years_baseline: string[]
  years_recent: string[]
  # fit determinism (Analysis 05b)
  seed: int
  # plot labels (Analysis 06)
  plot_title: string
  plot_subtitle: string
  plot_color: string

steps:

  gbif:
    run: GBIF_Retrieval/workflow.cwl
    in:
      credentials_file: gbif_credentials
      genus: genus
      genus_key: genus_key
      countries: countries
    out: [ gbif_data, gbif_metadata, occurrence_table ]

  gbif_prep:
    run: GBIF_Preprocessing/workflow.cwl
    in:
      occurrences: gbif/occurrence_table
      years: clean_years
      drop_species: drop_species
      synonyms: synonyms
      species_list: species_list
      output_dir:
        valueFrom: "out_gbif_prep"
    out: [ occurrences_clean ]

  era5:
    run: ERA5_Retrieval/workflow.cwl
    in:
      credentials_file: cds_credentials
      years: era5_years
      area: era5_area
      output_dir:
        valueFrom: "out_era5_retrieval"
    out: [ t2m_mean, t2m_daily_min_mean, t2m_daily_max_mean, tp_sum ]

  era5_prep:
    run: ERA5_Preprocessing/workflow.cwl
    in:
      t2m_mean: era5/t2m_mean
      t2m_daily_min_mean: era5/t2m_daily_min_mean
      t2m_daily_max_mean: era5/t2m_daily_max_mean
      tp_sum: era5/tp_sum
      output_dir:
        valueFrom: "out_era5_prep"
    out: [ tmp, tmn, tmx, pre ]

  climate_dir:
    run: util/make-climate-dir.cwl
    in:
      tmp: era5_prep/tmp
      tmn: era5_prep/tmn
      tmx: era5_prep/tmx
      pre: era5_prep/pre
    out: [ climate_dir ]

  analysis:
    run: Analysis/workflow.cwl
    in:
      occurrences: gbif_prep/occurrences_clean
      err_obs: err_obs
      continent: continent
      grid_resolution_m: grid_resolution_m
      grid_bbox: grid_bbox
      bbox_latlon: bbox_latlon
      period_baseline: period_baseline
      period_recent: period_recent
      climate_dir: climate_dir/climate_dir
      climate_source:
        valueFrom: "era5"
      years_baseline: years_baseline
      years_recent: years_recent
      seed: seed
      plot_title: plot_title
      plot_subtitle: plot_subtitle
      plot_color: plot_color
    out:
      [ clean_records, presence_absence, sampling_continent,
        climate_tei_pei, data_glmm, logistic_summary,
        posterior_vb_summary, forest_plot ]

outputs:
  gbif_metadata:
    type: File
    outputSource: gbif/gbif_metadata
  occurrences:
    type: File
    outputSource: gbif/occurrence_table
  occurrences_clean:
    type: File
    outputSource: gbif_prep/occurrences_clean
  era5_tmp:
    type: File
    outputSource: era5_prep/tmp
  era5_tmn:
    type: File
    outputSource: era5_prep/tmn
  era5_tmx:
    type: File
    outputSource: era5_prep/tmx
  era5_pre:
    type: File
    outputSource: era5_prep/pre
  clean_records:
    type: File
    outputSource: analysis/clean_records
  presence_absence:
    type: File
    outputSource: analysis/presence_absence
  sampling_continent:
    type: File
    outputSource: analysis/sampling_continent
  climate_tei_pei:
    type: File
    outputSource: analysis/climate_tei_pei
  data_glmm:
    type: File
    outputSource: analysis/data_glmm
  logistic_summary:
    type: File
    outputSource: analysis/logistic_summary
  posterior_vb_summary:
    type: File
    outputSource: analysis/posterior_vb_summary
  forest_plot:
    type: File
    outputSource: analysis/forest_plot

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
