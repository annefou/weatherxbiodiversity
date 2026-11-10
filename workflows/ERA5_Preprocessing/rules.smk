# ERA5_Preprocessing: monthly ERA5 statistics -> monthly tmp/tmn/tmx/pre with
# CRU TS definitions (degC, mm), the climate input of the exposure indices.
# Run on its own: snakemake --cores 1 era5_preprocessing

ERA5_CLIMATE_DIR = "data/era5_climate"
ERA5_CLIMATE = [
    f"{ERA5_CLIMATE_DIR}/era5_{v}_monthly_{ERA5_START}_{ERA5_END}.nc"
    for v in ("tmp", "tmn", "tmx", "pre")
]


rule era5_preprocessing:
    input:
        ERA5_CLIMATE,


rule era5_to_climate:
    input:
        ERA5_FILES,
    output:
        ERA5_CLIMATE,
    shell:
        "python workflows/ERA5_Preprocessing/era5_to_climate.py "
        f"--input-dir {ERA5['output_dir']} --years {ERA5_START} {ERA5_END} "
        f"--output-dir {ERA5_CLIMATE_DIR}"
