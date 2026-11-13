
cwlVersion: v1.2
class: CommandLineTool

label: GBIF data download
doc: |
  This workflow downloads GBIF data based on a metadata file
  provided by a download request.

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
      - entryname: 01-download.py
        entry:
          $include: 01-download.py
  - class: NetworkAccess
    networkAccess: true

baseCommand: [python, 01-download.py]
inputs:
  metadata:
    type: File
    default: metadata.json
    inputBinding:
      prefix: --metadata_file
  gbif_download_dir:
    type: string
    default: gbif_data
    inputBinding:
      prefix: --output_dir

outputs:
  gbif_data:
    type: Directory
    outputBinding:
      glob: $(inputs.gbif_download_dir)
  occurrence_table:
    type: File
    doc: The GBIF occurrence table (occurrence.txt), wired directly into steps expecting a single File.
    outputBinding:
      glob: $(inputs.gbif_download_dir)/occurrence.txt


$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9021-3197
    s:name: Dominik Brilhaus