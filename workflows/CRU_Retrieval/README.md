# CRU_Retrieval (`cru_retrieve.py`)

The climate data of Soroye et al. (2020): CRU TS 3.24.01 monthly, 0.5°, from
its producer, the Climatic Research Unit of the University of East Anglia
(<https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_3.24.01/>, Open Database
Licence). No Figshare download is needed.

The decadal global files (`cru_ts3.24.01.<start>.<end>.<var>.dat.nc.gz`) are
downloaded one by one, unpacked and cropped to `--bbox`, so only small files
are kept (about 130 MB for the study instead of about 5 GB).

The decades are those of Soroye et al.'s data deposit (`config/iberia.yaml`,
`cru.decades`): 1901–1980 and 1991–2015, without 1981–1990, which none of the
study periods uses but which enters the "all years" climate limits.

```bash
python cru_retrieve.py --variables tmp tmn tmx pre \
  --decades 1901.1910 1911.1920 1921.1930 1931.1940 1941.1950 1951.1960 \
            1961.1970 1971.1980 1991.2000 2001.2010 2011.2015 \
  --bbox 46 -34 25 7 --output-dir data/cru
```

Snakemake rule: `cru_retrieval`.

Note: 42 of these 44 files are identical, over the study region, to those in
the local copy of Soroye et al.'s deposit used for Phase 3 of the book; in that
copy `tmx` 2011–2015 is missing and `tmp` 2011–2015 is damaged (its time axis
runs from 2011 back to 1900). This step uses the producer's files.
