cwlVersion: v1.2
class: CommandLineTool
label: Forest plot
doc: |
  Forest plot of GLMM coefficients with credible intervals, highlighting the climate-index term.
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
      - entryname: 06_forest_plot.py
        entry:
          $include: 06_forest_plot.py
baseCommand: [python, 06_forest_plot.py]
inputs:
  summary:
    type: File
    inputBinding:
      prefix: --summary
  title:
    type: string
    inputBinding:
      prefix: --title
  subtitle:
    type: string
    inputBinding:
      prefix: --subtitle
  color:
    type: string
    inputBinding:
      prefix: --color
  output_dir:
    type: string
    default: out
    inputBinding:
      prefix: --output-dir
outputs:
  forest:
    type: File
    outputBinding:
      glob: $(inputs.output_dir)/forest.png

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
