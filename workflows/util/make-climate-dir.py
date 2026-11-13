"""Assemble the four ERA5 monthly climate files into a climate directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tmp", type=Path, required=True)
    parser.add_argument("--tmn", type=Path, required=True)
    parser.add_argument("--tmx", type=Path, required=True)
    parser.add_argument("--pre", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("climate_dir"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for src in (args.tmp, args.tmn, args.tmx, args.pre):
        dest = args.output_dir / src.name
        shutil.copy2(src, dest)
        print(f"Copied {src} to {dest}", flush=True)


if __name__ == "__main__":
    main()
