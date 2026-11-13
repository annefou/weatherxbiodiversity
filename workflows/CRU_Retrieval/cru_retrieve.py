"""
CRU TS 3.24.01 retrieval: the climate data of Soroye et al. (2020).

Downloads the decadal CRU TS 3.24.01 monthly files (0.5 degree, global) from the
producer, the Climatic Research Unit of the University of East Anglia
(https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_3.24.01/, Open Database
Licence), unpacks them and keeps only the study region, so that only small
files are stored:

  <output-dir>/cru_ts3.24.01.<start>.<end>.<var>.dat.nc   (cropped to --bbox)

Soroye et al.'s data deposit has the decades 1901.1910 ... 1971.1980,
1991.2000, 2001.2010, 2011.2015 (no 1981.1990); --decades selects them.

  python cru_retrieve.py --variables tmp tmn tmx pre \
      --decades 1901.1910 1911.1920 ... 2011.2015 --bbox 46 -34 25 7 --output-dir data/cru
"""
from __future__ import annotations

import argparse
import gzip
import shutil
import tempfile
from pathlib import Path

import requests
import xarray as xr

BASE = "https://crudata.uea.ac.uk/cru/data/hrg/cru_ts_3.24.01/cruts.1701201703.v3.24.01"


def main() -> None:
    p = argparse.ArgumentParser(description="Download CRU TS 3.24.01 decadal files and crop them")
    p.add_argument("--variables", nargs="+", default=["tmp", "tmn", "tmx", "pre"])
    p.add_argument("--decades", nargs="+", required=True, help="e.g. 1901.1910 1911.1920 ... 2011.2015")
    p.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("N", "W", "S", "E"),
                   help="region kept, degrees")
    p.add_argument("--output-dir", type=Path, default=Path("data/cru"))
    a = p.parse_args()

    n, w, s, e = a.bbox
    a.output_dir.mkdir(parents=True, exist_ok=True)
    for var in a.variables:
        for dec in a.decades:
            name = f"cru_ts3.24.01.{dec}.{var}.dat.nc"
            out = a.output_dir / name
            if out.exists():
                print(f"exists: {out}")
                continue
            url = f"{BASE}/{var}/{name}.gz"
            with tempfile.TemporaryDirectory() as tmp:
                gz, nc = Path(tmp) / f"{name}.gz", Path(tmp) / name
                with requests.get(url, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    with gz.open("wb") as f:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            f.write(chunk)
                with gzip.open(gz, "rb") as src, nc.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                with xr.open_dataset(nc) as ds:
                    da = ds[var].sel(lat=slice(s, n), lon=slice(w, e)).load()
                da.attrs["source"] = f"CRU TS 3.24.01 ({url}), cropped to lat {s}..{n}, lon {w}..{e}"
                da.to_netcdf(out)
            print(f"saved: {out} {dict(da.sizes)}")


if __name__ == "__main__":
    main()
