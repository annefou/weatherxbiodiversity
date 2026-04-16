"""
Download ERA5 daily max 2m temperature from CDS, year by year.

The derived-era5-single-levels-daily-statistics product has strict
cost limits — we must request one year at a time.

Run this script to populate data/era5_daily_max/. It's idempotent:
already-downloaded years are skipped.

Usage:
    python download_era5_daily.py          # all years (1959-2024)
    python download_era5_daily.py 2020     # single year
"""

import cdsapi
import sys
import os

OUTDIR = "data/era5_daily_max"
os.makedirs(OUTDIR, exist_ok=True)
AREA = [44, -10, 36, 4]

client = cdsapi.Client()

if len(sys.argv) > 1:
    years = [int(sys.argv[1])]
else:
    years = range(1959, 2025)

for year in years:
    outfile = os.path.join(OUTDIR, f"era5_tmax_daily_{year}.nc")

    if os.path.exists(outfile):
        size = os.path.getsize(outfile) / 1e6
        print(f"  {year}: already downloaded ({size:.1f} MB)")
        continue

    print(f"  {year}: requesting...", end=" ", flush=True)

    try:
        client.retrieve(
            "derived-era5-single-levels-daily-statistics",
            {
                "variable": ["2m_temperature"],
                "year": [str(year)],
                "month": [f"{m:02d}" for m in range(1, 13)],
                "day": [f"{d:02d}" for d in range(1, 32)],
                "daily_statistic": "daily_maximum",
                "time_zone": "utc+00:00",
                "frequency": "1_hourly",
                "data_format": "netcdf",
                "area": AREA,
            },
            outfile,
        )
        size = os.path.getsize(outfile) / 1e6
        print(f"done ({size:.1f} MB)")
    except Exception as e:
        print(f"FAILED: {e}")
        # Remove partial file
        if os.path.exists(outfile):
            os.remove(outfile)
