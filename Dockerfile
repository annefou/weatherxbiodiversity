FROM mambaorg/micromamba:1.5-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app

# CDS API key must be mounted at runtime:
#   docker run -v ~/.cdsapirc:/home/mambauser/.cdsapirc weatherxbio
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]
CMD ["snakemake", "--cores", "1"]
