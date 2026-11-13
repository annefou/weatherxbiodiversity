cwlVersion: v1.2
class: CommandLineTool
label: Climate normals and TEI/PEI
doc: |
  Grid interpolation of climate normals (monthly files <source>_{tmp,tmn,tmx,pre}_monthly_*.nc, e.g. from ERA5_Preprocessing) and computation of the thermal and precipitation indices (TEI/PEI) per period.
hints:
  DockerRequirement:
    dockerImageId: analysis
    dockerFile:
      $include: Dockerfile
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]
requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: 04_climate_tei_pei.py
        entry:
          $include: 04_climate_tei_pei.py
baseCommand: [python, 04_climate_tei_pei.py]
inputs:
  presence_absence:
    type: File
    inputBinding:
      prefix: --presence-absence
  climate_dir:
    type: Directory
    inputBinding:
      prefix: --climate-dir
  climate_source:
    type: string
    default: era5
    doc: File prefix of the monthly climate files, <source>_<var>_monthly_*.nc
    inputBinding:
      prefix: --climate-source
  years_baseline:
    type: string[]
    inputBinding:
      prefix: --years-baseline
  years_recent:
    type: string[]
    inputBinding:
      prefix: --years-recent
  grid_resolution_m:
    type: int
    inputBinding:
      prefix: --grid-resolution-m
  bbox_latlon:
    type: string[]?
    inputBinding:
      prefix: --bbox-latlon
  grid_bbox:
    type: string[]?
    inputBinding:
      prefix: --grid-bbox
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  climate_tei_pei:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/climate_tei_pei.npz

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
