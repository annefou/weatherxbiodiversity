FROM mambaorg/micromamba:1.5-jammy

RUN micromamba install -y -n base \
    -c conda-forge \
    python=3.12 pandas numpy pyproj scipy xarray netcdf4 && \
    micromamba clean --all --yes

RUN micromamba install -y -n base \
    -c conda-forge \
    pyarrow statsmodels bambi && \
    micromamba clean --all --yes

RUN micromamba install -y -n base \
    -c conda-forge \
    matplotlib && \
    micromamba clean --all --yes
