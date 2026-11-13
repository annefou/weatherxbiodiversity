# GBIF preprocessing (`clean_occurrences.py`)

Cleans the occurrence table of a GBIF download (GBIF_Retrieval output) for any taxon and any area: keeps and renames the needed columns, removes the genus from species names, drops records without coordinates, species or year, and optionally applies a year range and the study's taxonomic curation tables (dropped taxa, synonyms, species list). Its output, occurrences_clean.csv, is the occurrence input of the Analysis.

## Description

Generic cleaning of the occurrence table from `GBIF_Retrieval` (DWCA
`occurrence.txt`, or a SIMPLE_CSV download), for any taxon and any area:

1. keeps and renames the needed columns: `gbifID` → `LYID`,
   `decimalLatitude` / `decimalLongitude` → `latitude` / `longitude`, `year`,
   `species`, `countryCode` → `country`, `stateProvince` → `state_prov`;
2. species names without each record's genus, lowercase
   (`Bombus terrestris` → `terrestris`);
3. drops records without coordinates, species or year, and, if `years` is
   given, records outside `START <= year < END`;
4. optional taxonomic curation, each from a data file of the study (e.g. in
   an assay): `drop_species` (taxa removed), `synonyms` (merged into valid
   names), `species_list` (only these species kept).

Output: `occurrences_clean.csv` with columns `species`, `latitude`,
`longitude`, `year`, `LYID`, `country`, `state_prov`.

Study-specific definitions (for Soroye et al. 2020: continent, erroneous
observations, periods, seasons) are not part of this step; they belong to the
analysis.

## Use script directly with CLI arguments

```bash
python clean_occurrences.py \
  --occurrences ../../runs/GBIF_Retrieval/results/gbif_data/occurrence.txt \
  --years 1901 2015 \
  --drop-species ../../studies/BombusIberia_SupplementaryFiles/resources/bombus_drop_species.tsv \
  --synonyms ../../studies/BombusIberia_SupplementaryFiles/resources/bombus_synonyms.tsv \
  --species-list ../../studies/BombusIberia_SupplementaryFiles/resources/Kerr_et_al2015_spplist.csv \
  --output-dir results
```

Only `--occurrences` is required.

## Validate the CWL Tool description

```bash
cwltool --validate workflow.cwl
```

## Run the Tool

Test job on the `GBIF_Retrieval` run results, generic cleaning only:

```bash
cwltool workflow.cwl test_gbif_preprocessing.yml
```

The tool's `Dockerfile` is used as a hint (`cwltool` with Docker, or
`cwltool --podman`). The study run is in
[runs/GBIF_Preprocessing](../../runs/GBIF_Preprocessing).
