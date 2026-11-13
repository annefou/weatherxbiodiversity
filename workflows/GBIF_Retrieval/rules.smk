# GBIF_Retrieval: metadata of an existing download (config gbif.download: key or
# DOI, no account needed) or of a new request (gbif.request + credentials), then
# download and unpack; the occurrence table (DWCA occurrence.txt or SIMPLE_CSV
# <key>.csv) is copied to data/gbif/occurrences.tsv.

rule gbif_metadata:
    output:
        f"{DATA}/gbif/metadata.json",
    params:
        cfg=config["gbif"],
    run:
        g = params.cfg
        if g.get("download"):
            shell(f"python {W}/GBIF_Retrieval/00-existing-download.py --download {g['download']} --output-meta {{output}}")
        else:
            r = g["request"]
            shell(f"python {W}/GBIF_Retrieval/00-submit-request.py --credentials-file {g['credentials']} "
                  f"--genus {r['genus']} --genus-key {r['genus_key']} --countries {r['countries']} --output-meta {{output}}")


rule gbif_download:
    input:
        f"{DATA}/gbif/metadata.json",
    output:
        f"{DATA}/gbif/occurrences.tsv",
    params:
        raw=f"{DATA}/gbif/raw",
    shell:
        """
        python {W}/GBIF_Retrieval/01-download.py --metadata_file {input} --output_dir {params.raw}
        key=$(python -c "import json,sys; print(json.load(open(sys.argv[1]))['download']['key'])" {input})
        if [ -f {params.raw}/occurrence.txt ]; then cp {params.raw}/occurrence.txt {output}
        else cp {params.raw}/$key.csv {output}; fi
        """
