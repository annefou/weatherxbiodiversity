cwlVersion: v1.2
class: CommandLineTool
label: Assemble GLMM data
doc: |
  Assembly of the presence/absence, sampling-effort and climate index grids into the per-species, per-cell table for the GLMM.
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
      - entryname: 05a_build_data_glmm.py
        entry:
          $include: 05a_build_data_glmm.py
baseCommand: [python, 05a_build_data_glmm.py]
inputs:
  presence_absence:
    type: File
    inputBinding:
      prefix: --presence-absence
  sampling_continent:
    type: File
    inputBinding:
      prefix: --sampling-continent
  climate_tei_pei:
    type: File
    inputBinding:
      prefix: --climate-tei-pei
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  data_glmm:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/dataGLMM_extinction.parquet

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
