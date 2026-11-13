cwlVersion: v1.2
class: Workflow

label: GBIF data retrieval workflow
doc: |
  This workflow chains two steps to 1. submit a GBIF download request and 
  2. download the GBIF data based on the metadata provided by the request.

hints:
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]


requirements:
  StepInputExpressionRequirement: {}

inputs:
  credentials_file: File
  genus: string
  genus_key: int
  countries: string
  has_coordinate:
      type: boolean
      default: true
  has_geospatial_issue:
      type: boolean
      default: false
  poll_interval_sec:
      type: int
      default: 30
  poll_timeout_sec:
      type: int
      default: 3600

steps:

  request:
    run: 00-submit-request.cwl
    in:
      credentials_file: credentials_file
      genus: genus
      genus_key: genus_key
      countries: countries
      has_coordinate: has_coordinate
      has_geospatial_issue: has_geospatial_issue
      poll_interval_sec: poll_interval_sec
      poll_timeout_sec: poll_timeout_sec
    out: [ metadata ]

  download:
    run: 01-download.cwl
    in: 
      metadata:
        source: request/metadata
    out: [ gbif_data, occurrence_table ]

outputs:
  gbif_metadata:
    type: File
    outputSource: request/metadata
  gbif_data:
    type: Directory
    outputSource: download/gbif_data
  occurrence_table:
    type: File
    outputSource: download/occurrence_table

$namespaces:
  s: https://schema.org/
  edam: https://edamontology.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf
  - https://edamontology.org/EDAM_1.18.owl

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9021-3197
    s:name: Dominik Brilhaus
