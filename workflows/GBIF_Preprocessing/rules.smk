# GBIF_Preprocessing: generic cleaning of the occurrence table, with the study's
# year range and taxonomic curation tables.

rule gbif_preprocessing:
    input:
        occurrences=f"{DATA}/gbif/occurrences.tsv",
        drop=f"{STUDY}/bombus_drop_species.tsv",
        synonyms=f"{STUDY}/bombus_synonyms.tsv",
        species=f"{STUDY}/Kerr_et_al2015_spplist.csv",
    output:
        f"{RES}/gbif/occurrences_clean.csv",
    params:
        years=" ".join(map(str, config["gbif"]["years"])),
        out=f"{RES}/gbif",
    shell:
        "python {W}/GBIF_Preprocessing/clean_occurrences.py --occurrences {input.occurrences} "
        "--years {params.years} --drop-species {input.drop} --synonyms {input.synonyms} "
        "--species-list {input.species} --output-dir {params.out}"
