FROM mambaorg/micromamba:1.5-jammy

RUN micromamba install -y -n base \
    -c conda-forge \
    python=3.12 requests && \
    micromamba clean --all --yes