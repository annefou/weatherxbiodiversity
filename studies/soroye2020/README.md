# Soroye et al. (2020) study tables

Taxonomic curation tables of the original study, used by the GBIF
preprocessing and the Analysis:

| File | Content | Used by |
|---|---|---|
| `Kerr_et_al2015_spplist.csv` | species list (Kerr et al. 2015) | GBIF_Preprocessing (`--species-list`) |
| `bombus_synonyms.tsv` | synonyms merged into valid names | GBIF_Preprocessing (`--synonyms`) |
| `bombus_drop_species.tsv` | taxa removed from the analysis | GBIF_Preprocessing (`--drop-species`) |
| `bombus_err_obs.csv` | erroneous observations (per species, continent, state) | Analysis step 01 (`--err-obs`) |

Source: the data deposit of Soroye, P., Newbold, T. & Kerr, J. (2020),
*Climate change contributes to widespread declines among bumble bees across
continents*, Science 367, 685–688,
[https://doi.org/10.1126/science.aax8591](https://doi.org/10.1126/science.aax8591);
data repository [https://doi.org/10.6084/m9.figshare.9956471](https://doi.org/10.6084/m9.figshare.9956471),
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
`bombus_drop_species.tsv` and `bombus_synonyms.tsv` transcribe, as data files,
the dropped taxa and synonyms that Soroye et al.'s script
`1_Cleandata_and_makeMCPs.R` applies in code (see the header of each file).

The same tables are in the ARC
(`studies/BombusIberia_SupplementaryFiles/resources/`), so no part of the
1.1 GB deposit needs to be downloaded.
