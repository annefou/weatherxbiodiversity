cwlVersion: v1.2
class: CommandLineTool

label: GBIF preprocessing (clean an occurrence download)
doc: |
  Generic cleaning of a GBIF_Retrieval occurrence table (DWCA occurrence.txt
  or SIMPLE_CSV) for any taxon and any area (clean_occurrences.py): keeps and
  renames the needed columns, strips each record's genus from species names,
  drops records without coordinates, species or year, and optionally applies
  a year range and the study's taxonomic curation tables (dropped taxa,
  synonyms, species list).
  Output: occurrences_clean.csv (species, latitude, longitude, year, LYID,
  country, state_prov).

hints:
  DockerRequirement:
    dockerImageId: gbif_preprocessing
    dockerFile:
      $include: Dockerfile
  SoftwareRequirement:
    packages:
      - package: python
        version: [ "3.12" ]

requirements:
  - class: InitialWorkDirRequirement
    listing:
      - entryname: clean_occurrences.py
        entry:
          $include: clean_occurrences.py

baseCommand: [python, clean_occurrences.py]

inputs:
  occurrences:
    type: File
    doc: GBIF_Retrieval output occurrence_table (DWCA occurrence.txt, tab-separated)
    inputBinding:
      prefix: --occurrences
  years:
    type: int[]?
    doc: "Keep START <= year < END, e.g. [1901, 2015] (default: all years)"
    inputBinding:
      prefix: --years
  drop_species:
    type: File?
    doc: "TSV species<TAB>reason; these taxa are removed"
    inputBinding:
      prefix: --drop-species
  synonyms:
    type: File?
    doc: "TSV from<TAB>to<TAB>note; merged into valid names"
    inputBinding:
      prefix: --synonyms
  species_list:
    type: File?
    doc: CSV with a 'species' column; records of other species are dropped
    inputBinding:
      prefix: --species-list
  output_dir:
    type: string
    default: results
    inputBinding:
      prefix: --output-dir

outputs:
  occurrences_clean:
    type: File
    doc: Cleaned occurrences (CSV)
    outputBinding:
      glob: $(inputs.output_dir)/occurrences_clean.csv

$namespaces:
  s: https://schema.org/

$schemas:
  - https://schema.org/version/latest/schemaorg-current-https.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-8763-1643
    s:name: Jean Iaquinta
  - class: s:Person
    s:identifier: https://orcid.org/0000-0002-1784-2920
    s:name: Anne Fouilloux
