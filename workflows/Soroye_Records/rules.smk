# Soroye_Records: the study records of Soroye et al. (2020) themselves (North
# America + Europe, 66 Bombus species), from their data deposit
# (Figshare, https://doi.org/10.6084/m9.figshare.9956471, unpacked under
# config soroye_records.bundle), cleaned with the Phase 2 port of their R
# script 1 (soroye_port/01_clean_data.py: Kerr et al. species list,
# erroneous observations, continent, periods, seasons). The result has the
# columns of Analysis 01 (clean_records.csv) and replaces it: Analysis 02-06
# then run unchanged, once per climate source.

SR = config["soroye_records"]


rule soroye_records:
    input:
        f"{SR['bundle']}/0_data/bombus_ogdata.csv",
        f"{SR['bundle']}/0_data/Kerr_et_al2015_spplist.csv",
        f"{SR['bundle']}/0_data/bombus_err_obs.csv",
    output:
        f"{RES}/common/clean_records.csv",
    shell:
        "python soroye_port/01_clean_data.py && cp soroye_port/outputs/bombus_clean.csv {output}"


ruleorder: soroye_records > analysis_01_study_records
