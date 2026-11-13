cwlVersion: v1.2
class: CommandLineTool
label: Assemble ERA5 climate directory
doc: |
  Collects the four ERA5 monthly climate files (tmp, tmn, tmx, pre) from
  ERA5_Preprocessing into a single Directory laid out the way
  Analysis/04-climate-tei-pei.cwl expects it (era5_<var>_monthly_*.nc).
hints:
  DockerRequirement:
    dockerImageId: util
    dockerFile:
      $include: Dockerfile
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]
requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: make_climate_dir.py
        entry:
          $include: make-climate-dir.py
baseCommand: [python, make_climate_dir.py]
inputs:
  tmp:
    type: File
    inputBinding:
      prefix: --tmp
  tmn:
    type: File
    inputBinding:
      prefix: --tmn
  tmx:
    type: File
    inputBinding:
      prefix: --tmx
  pre:
    type: File
    inputBinding:
      prefix: --pre
  output_dir:
    type: string
    default: climate_dir
    inputBinding:
      prefix: --output-dir
outputs:
  climate_dir:
    type: Directory
    outputBinding:
      glob: $(inputs.output_dir)

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
