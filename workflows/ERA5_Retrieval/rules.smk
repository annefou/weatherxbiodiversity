# ERA5_Retrieval: monthly statistics of hourly ERA5 (2 m temperature: mean, mean
# of daily minimum and maximum; total precipitation: sum), streamed from ECMWF's
# ARCO Zarr store for the study boxes. Needs credentials/cds_credentials.json.

ERA5_Y0, ERA5_Y1 = config["era5"]["years"]
ERA5_STATS = {"t2m": ["mean", "daily_min_mean", "daily_max_mean"], "tp": ["sum"]}


rule era5_retrieval:
    output:
        [f"{DATA}/era5/era5_{v}_{s}_monthly_{ERA5_Y0}_{ERA5_Y1}.nc" for v, ss in ERA5_STATS.items() for s in ss],
    params:
        variables=json.dumps(ERA5_STATS),
        area=" ".join("--area " + " ".join(map(str, box)) for box in config["era5"]["area"]),
        out=f"{DATA}/era5",
        credentials=config["era5"]["credentials"],
    shell:
        "python {W}/ERA5_Retrieval/era5_retrieve.py --variables '{params.variables}' --frequency monthly "
        "--years {ERA5_Y0} {ERA5_Y1} {params.area} --credentials-file {params.credentials} --output-dir {params.out}"
