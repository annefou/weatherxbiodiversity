FROM docker.io/mambaorg/micromamba:1.5-jammy

RUN micromamba install -y -n base \
    -c conda-forge \
    python=3.12 pandas && \
    micromamba clean --all --yes
