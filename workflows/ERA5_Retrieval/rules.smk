# ERA5_Retrieval: monthly statistics of hourly ERA5 (2 m temperature: mean, mean
# of daily minimum and maximum; total precipitation: sum), streamed from ECMWF's
# ARCO Zarr store. Region: the study boxes (config era5.area), or, with
# era5.grid_cells (buffer in degrees), only the store tiles around the study
# grid cells that hold records. Needs credentials/cds_credentials.json.

ERA5_Y0, ERA5_Y1 = config["era5"]["years"]
ERA5_STATS = {"t2m": ["mean", "daily_min_mean", "daily_max_mean"], "tp": ["sum"]}
ERA5_CELLS = config["era5"].get("grid_cells")


rule era5_grid_cells:
    input:
        f"{RES}/common/presence_absence.npz",
    output:
        f"{DATA}/era5/grid_cells.tsv",
    params:
        grid=f"--grid-resolution-m {config['analysis']['grid_resolution_m']} "
             f"--grid-bbox {' '.join(map(str, config['analysis']['grid_bbox']))}",
    shell:
        "python {W}/ERA5_Retrieval/grid_cells.py --presence-absence {input} {params.grid} --output {output}"


rule era5_retrieval:
    input:
        [f"{DATA}/era5/grid_cells.tsv"] if ERA5_CELLS else [],
    output:
        [f"{DATA}/era5/era5_{v}_{s}_monthly_{ERA5_Y0}_{ERA5_Y1}.nc" for v, ss in ERA5_STATS.items() for s in ss],
    params:
        variables=json.dumps(ERA5_STATS),
        region=(f"--occurrences {DATA}/era5/grid_cells.tsv --buffer {ERA5_CELLS['buffer']}" if ERA5_CELLS else
                " ".join("--area " + " ".join(map(str, box)) for box in config["era5"]["area"])),
        out=f"{DATA}/era5",
        credentials=config["era5"]["credentials"],
    shell:
        "python {W}/ERA5_Retrieval/era5_retrieve.py --variables '{params.variables}' --frequency monthly "
        "--years {ERA5_Y0} {ERA5_Y1} {params.region} --credentials-file {params.credentials} --output-dir {params.out}"
