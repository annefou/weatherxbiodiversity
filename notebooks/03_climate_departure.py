# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Step 3: Compute Climate Departure Index
#
# This notebook computes the climate departure index from
# [Soroye, Newbold & Kerr (2020, *Science*)](https://doi.org/10.1126/science.aax8591).
#
# ## Method
#
# For each grid cell:
#
# 1. **Baseline period** (1959–1974): find the maximum monthly temperature
#    ever recorded — this represents the historical thermal ceiling.
# 2. **Recent period** (2000–2024): count how many months exceed that ceiling.
# 3. **Climate departure** = fraction of recent months exceeding the baseline max.
#
# A departure of 0.10 means 10% of months in the recent period were hotter
# than the hottest month in the entire baseline — a signal of climate extremes
# pushing beyond the historical envelope.
#
# ## Difference from original
#
# | | Soroye et al. (2020) | This replication |
# |---|---|---|
# | Climate data | CRU TS 3.10 | ERA5 (CDS daily statistics) |
# | Resolution | 0.5° (~50 km) | 0.25° (~25 km) |
# | Baseline | 1901–1974 (73 years) | 1959–1974 (16 years) |
# | Region | All Europe + N. America | Iberian Peninsula |
# | Temperature | Monthly mean of daily max | Monthly max of daily max |

# %%
import xarray as xr
import numpy as np
from pathlib import Path

# %% [markdown]
# ## Configuration

# %%
DATADIR = Path("../data")
RESULTS = Path("../results")
RESULTS.mkdir(exist_ok=True)

BASELINE = ("1959", "1974")
RECENT = ("2000", "2024")

# %% [markdown]
# ## 1. Load monthly maximum temperature

# %%
# Prefer daily-max-derived monthly max; fall back to monthly means
monthly_tmax_file = DATADIR / "era5_iberia_monthly_tmax.nc"
monthly_mean_file = DATADIR / "era5_iberia_monthly_t2m_combined.nc"

if monthly_tmax_file.exists():
    t2m = xr.open_dataarray(monthly_tmax_file)
    source = "monthly max of daily max"
elif monthly_mean_file.exists():
    t2m = xr.open_dataarray(monthly_mean_file)
    source = "monthly mean (approximate)"
else:
    raise FileNotFoundError("No ERA5 temperature file found. Run notebook 02 first.")

# Identify time dimension
time_dim = "valid_time" if "valid_time" in t2m.dims else "time"

print(f"Source: {source}")
print(f"Shape: {t2m.shape}")
print(f"Time: {str(t2m[time_dim].values[0])[:10]} to {str(t2m[time_dim].values[-1])[:10]}")
print(f"Grid: {t2m.sizes['latitude']} × {t2m.sizes['longitude']}")

# %% [markdown]
# ## 2. Compute baseline thermal ceiling

# %%
baseline = t2m.sel({time_dim: slice(*BASELINE)})
baseline_max = baseline.max(dim=time_dim)

print(f"Baseline period: {BASELINE[0]}–{BASELINE[1]}")
print(f"  Months in baseline: {baseline.sizes[time_dim]}")
print(f"  Thermal ceiling range: {float(baseline_max.min()):.1f} to {float(baseline_max.max()):.1f} °C")

# %% [markdown]
# ## 3. Compute climate departure

# %%
recent = t2m.sel({time_dim: slice(*RECENT)})
n_months = recent.sizes[time_dim]

departure = (recent > baseline_max).sum(dim=time_dim) / n_months

departure.name = "climate_departure"
departure.attrs = {
    "units": "fraction",
    "long_name": "Fraction of recent months exceeding baseline thermal ceiling",
    "method": "Soroye, Newbold & Kerr (2020), Science 367:685-688",
    "baseline_period": f"{BASELINE[0]}-{BASELINE[1]}",
    "recent_period": f"{RECENT[0]}-{RECENT[1]}",
    "n_recent_months": int(n_months),
    "temperature_source": source,
}

print(f"Recent period: {RECENT[0]}–{RECENT[1]} ({n_months} months)")
print(f"\nClimate departure across Iberian Peninsula:")
print(f"  Mean:  {float(departure.mean())*100:.1f}%")
print(f"  Max:   {float(departure.max())*100:.1f}%")
print(f"  Min:   {float(departure.min())*100:.1f}%")
print(f"  Std:   {float(departure.std())*100:.1f}%")

# %% [markdown]
# ## 4. Save and visualize

# %%
dep_file = DATADIR / "era5_iberia_climate_departure.nc"
departure.to_netcdf(dep_file)
print(f"Saved: {dep_file}")

# %%
try:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    departure.plot(ax=ax, cmap="YlOrRd", vmin=0, vmax=0.2,
                   cbar_kwargs={"label": "Climate departure (fraction)"})
    ax.set_title(
        f"Climate departure: fraction of months ({RECENT[0]}–{RECENT[1]})\n"
        f"exceeding baseline max ({BASELINE[0]}–{BASELINE[1]})"
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    fig.savefig(RESULTS / "climate_departure_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    print(f"Saved: {RESULTS / 'climate_departure_map.png'}")
except ImportError:
    print("matplotlib not available — skipping plot")
