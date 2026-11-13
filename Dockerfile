# The workflow's environment, exactly as pinned by pixi.lock.
FROM ghcr.io/prefix-dev/pixi:0.76.2

WORKDIR /app
COPY pixi.toml pixi.lock ./
RUN pixi install --locked && rm -rf /root/.cache/rattler

COPY . /app

# Credentials are never in the image: mount them at run time, e.g.
#   docker run -v $PWD/credentials:/app/credentials:ro -v $PWD/results:/app/results weatherxbiodiversity
CMD ["pixi", "run", "--locked", "snakemake", "--cores", "1"]
