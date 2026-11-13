FROM docker.io/mambaorg/micromamba:1.5-jammy

RUN micromamba install -y -n base \
    -c conda-forge \
    python=3.12 "xarray>=2024.6" "pandas>=2.0" numpy "zarr>=3" fsspec aiohttp netcdf4 && \
    micromamba clean --all --yes
