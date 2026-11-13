cwlVersion: v1.2
class: CommandLineTool
label: GLMM extinction (Bayesian)
doc: |
  Binomial GLMM of occurrence on the climate index, with species random slopes, fitted by MCMC (bambi/PyMC).
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
      - entryname: 05_bayesian_glmm.py
        entry:
          $include: 05_bayesian_glmm.py
baseCommand: [python, 05_bayesian_glmm.py]
inputs:
  data:
    type: File
    inputBinding:
      prefix: --data
  seed:
    type: int
    inputBinding:
      prefix: --seed
  draws:
    type: int
    inputBinding:
      prefix: --draws
  tune:
    type: int
    inputBinding:
      prefix: --tune
  chains:
    type: int
    inputBinding:
      prefix: --chains
  target_accept:
    type: float
    inputBinding:
      prefix: --target-accept
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  posterior_summary:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/posterior_summary.csv
  posterior:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/posterior.nc

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
