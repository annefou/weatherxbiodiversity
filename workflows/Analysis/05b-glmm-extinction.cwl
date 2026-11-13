cwlVersion: v1.2
class: CommandLineTool
label: GLMM extinction (VB)
doc: |
  Binomial GLMM of occurrence on the climate index, with species random slopes, fitted by variational Bayes (statsmodels).
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
      - entryname: 05b_glmm_extinction.py
        entry:
          $include: 05b_glmm_extinction.py
baseCommand: [python, 05b_glmm_extinction.py]
inputs:
  data:
    type: File
    inputBinding:
      prefix: --data
  seed:
    type: int
    inputBinding:
      prefix: --seed
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  logistic_summary:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/logistic_summary.csv
  posterior_vb_summary:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/posterior_vb_summary.csv

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
