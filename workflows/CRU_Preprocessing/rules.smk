# CRU_Preprocessing: monthly tmp, tmn, tmx (degC) and pre (mm) in the common
# climate input format, read by the Analysis with climate source "cru".

rule cru_preprocessing:
    input:
        [f"{DATA}/cru/cru_ts3.24.01.{d}.{v}.dat.nc" for v in CRU_VARS for d in CRU_DECADES],
    output:
        climate_files("cru"),
    params:
        inp=f"{DATA}/cru",
        out=f"{DATA}/climate/cru",
    shell:
        "python {W}/CRU_Preprocessing/cru_to_climate.py --input-dir {params.inp} --output-dir {params.out}"
