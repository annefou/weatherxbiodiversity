cwlVersion: v1.2
class: CommandLineTool

label: ERA5 preprocessing (monthly tmp, tmn, tmx, pre)
doc: |
  Turns the monthly ERA5 statistics from ERA5_Retrieval into the four monthly
  climate variables used by the analysis (era5_to_climate.py):
  tmp (t2m mean), tmn (t2m daily_min_mean), tmx (t2m daily_max_mean) in degC,
  and pre (tp sum) in mm. Output files: era5_<var>_monthly_<start>_<end>.nc,
  dims (time, lat, lon); start / end are the first and last year in the data.

hints:
  DockerRequirement:
    dockerImageId: era5_preprocessing
    dockerFile:
      $include: Dockerfile
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]

requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: era5_to_climate.py
        entry:
          $include: era5_to_climate.py

baseCommand: [python, era5_to_climate.py]

inputs:
  t2m_mean:
    type: File
    doc: Monthly mean 2 m temperature (ERA5_Retrieval output t2m_mean)
    inputBinding:
      prefix: --t2m-mean
  t2m_daily_min_mean:
    type: File
    doc: Monthly mean of daily minimum 2 m temperature (ERA5_Retrieval output t2m_daily_min_mean)
    inputBinding:
      prefix: --t2m-daily-min-mean
  t2m_daily_max_mean:
    type: File
    doc: Monthly mean of daily maximum 2 m temperature (ERA5_Retrieval output t2m_daily_max_mean)
    inputBinding:
      prefix: --t2m-daily-max-mean
  tp_sum:
    type: File
    doc: Monthly total precipitation (ERA5_Retrieval output tp_sum)
    inputBinding:
      prefix: --tp-sum
  output_dir:
    type: string
    default: results
    inputBinding:
      prefix: --output-dir

# One named output per variable.
outputs:
  tmp:
    type: File
    doc: Monthly mean temperature (degC)
    outputBinding:
      glob: $(inputs.output_dir)/era5_tmp_monthly_*.nc
  tmn:
    type: File
    doc: Monthly mean of daily minimum temperature (degC)
    outputBinding:
      glob: $(inputs.output_dir)/era5_tmn_monthly_*.nc
  tmx:
    type: File
    doc: Monthly mean of daily maximum temperature (degC)
    outputBinding:
      glob: $(inputs.output_dir)/era5_tmx_monthly_*.nc
  pre:
    type: File
    doc: Monthly total precipitation (mm)
    outputBinding:
      glob: $(inputs.output_dir)/era5_pre_monthly_*.nc


$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-1784-2920
    s:name: Anne Fouilloux
