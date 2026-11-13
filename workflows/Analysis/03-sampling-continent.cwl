cwlVersion: v1.2
class: CommandLineTool
label: Sampling effort per continent
doc: |
  Per-cell sampling effort (number of species observed) per continent, period and season, on the same grid as the presence/absence step.
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
      - entryname: 03_sampling_continent.py
        entry:
          $include: 03_sampling_continent.py
baseCommand: [python, 03_sampling_continent.py]
inputs:
  records:
    type: File
    inputBinding:
      prefix: --records
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
  period_baseline:
    type: int
    inputBinding:
      prefix: --period-baseline
  period_recent:
    type: int
    inputBinding:
      prefix: --period-recent
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  sampling_continent:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/sampling_continent.npz

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
