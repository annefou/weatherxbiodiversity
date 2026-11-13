cwlVersion: v1.2
class: CommandLineTool

label: GBIF data request
doc: |
  This workflow submits a GBIF download request.
  The executed `00-submit-request.py` script is adapted 
  from https://github.com/annefou/weatherxbiodiversity
  created by https://github.com/annefou/

hints:
  DockerRequirement:
    dockerImageId: gbif_retrieval
    dockerFile:
      $include: Dockerfile
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]

requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: 00-submit-request.py
        entry:
          $include: 00-submit-request.py
  - class: NetworkAccess
    networkAccess: true
  - class: InlineJavascriptRequirement

baseCommand: [python, 00-submit-request.py]
inputs:
  credentials_file:
    type: File
    inputBinding:
      prefix: --credentials-file
  genus:
    type: string
    inputBinding:
      prefix: --genus
  genus_key:
    type: int
    inputBinding:
      prefix: --genus-key
  countries:
    type: string
    inputBinding:
      prefix: --countries
  has_coordinate:
    type: boolean
    default: true
    inputBinding:
      prefix: --has-coordinate
  has_geospatial_issue:
    type: boolean
    default: false
    inputBinding:
      prefix: --has-geospatial-issue
  poll_interval_sec:
    type: int
    default: 30
    inputBinding:
      prefix: --poll-interval-sec
  poll_timeout_sec:
    type: int
    default: 3600
    inputBinding:
      prefix: --poll-timeout-sec
outputs:
  metadata:
    type: File
    outputBinding:
      glob: metadata.json
arguments: ["--output-meta", "metadata.json"]
    

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9021-3197
    s:name: Dominik Brilhaus
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-0035-6475
    s:name: Eli Chadwick
