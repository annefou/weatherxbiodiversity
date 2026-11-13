# CRU_Retrieval: CRU TS 3.24.01 decadal files (the climate data of Soroye et al.
# 2020) from the University of East Anglia, cropped to the study region.

CRU_VARS = ["tmp", "tmn", "tmx", "pre"]
CRU_DECADES = [str(d) for d in config["cru"]["decades"]]


rule cru_retrieval:
    output:
        [f"{DATA}/cru/cru_ts3.24.01.{d}.{v}.dat.nc" for v in CRU_VARS for d in CRU_DECADES],
    params:
        decades=" ".join(CRU_DECADES),
        bbox=" ".join(map(str, config["cru"]["bbox"])),
        out=f"{DATA}/cru",
    shell:
        "python {W}/CRU_Retrieval/cru_retrieve.py --variables tmp tmn tmx pre --decades {params.decades} "
        "--bbox {params.bbox} --output-dir {params.out}"
