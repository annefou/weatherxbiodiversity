# ERA5_Preprocessing: monthly tmp, tmn, tmx (degC) and pre (mm) in the common
# climate input format, read by the Analysis with climate source "era5".

rule era5_preprocessing:
    input:
        t2m_mean=f"{DATA}/era5/era5_t2m_mean_monthly_{ERA5_Y0}_{ERA5_Y1}.nc",
        t2m_min=f"{DATA}/era5/era5_t2m_daily_min_mean_monthly_{ERA5_Y0}_{ERA5_Y1}.nc",
        t2m_max=f"{DATA}/era5/era5_t2m_daily_max_mean_monthly_{ERA5_Y0}_{ERA5_Y1}.nc",
        tp_sum=f"{DATA}/era5/era5_tp_sum_monthly_{ERA5_Y0}_{ERA5_Y1}.nc",
    output:
        climate_files("era5"),
    params:
        out=f"{DATA}/climate/era5",
    shell:
        "python {W}/ERA5_Preprocessing/era5_to_climate.py --t2m-mean {input.t2m_mean} "
        "--t2m-daily-min-mean {input.t2m_min} --t2m-daily-max-mean {input.t2m_max} "
        "--tp-sum {input.tp_sum} --output-dir {params.out}"
