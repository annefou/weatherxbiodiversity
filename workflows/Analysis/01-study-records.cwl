cwlVersion: v1.2
class: CommandLineTool
label: Study records (continent, erroneous observations, periods, seasons)
doc: |
  Soroye et al. (2020) study definitions applied to the cleaned GBIF
  occurrences (GBIF_Preprocessing output): continent code, removal of the
  erroneous observations, baseline/recent periods and seasons.
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
      - entryname: 01_study_records.py
        entry:
          $include: 01_study_records.py
baseCommand: [python, 01_study_records.py]
inputs:
  occurrences:
    type: File
    doc: occurrences_clean.csv from GBIF_Preprocessing
    inputBinding:
      prefix: --occurrences
  err_obs:
    type: File
    inputBinding:
      prefix: --err-obs
  continent:
    type: int
    inputBinding:
      prefix: --continent
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  clean_records:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/clean_records.csv

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
