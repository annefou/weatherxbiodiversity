"""
Two standalone forest plots — one per phase. No cross-phase comparison.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

def plot_phase(csv_path, title, subtitle, out_path, color):
    df = pd.read_csv(csv_path, index_col=0)
    # Drop Intercept — not interesting for the scientific story
    df = df.drop('Intercept', errors='ignore')
    # Sort by coefficient magnitude (most positive at top)
    df = df.sort_values('mean', ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(df))
    ci = 1.96 * df['sd']
    ax.errorbar(df['mean'], y, xerr=ci, fmt='o', color=color,
                ecolor=color, capsize=4, markersize=7, elinewidth=1.5)
    ax.axvline(0, color='k', linewidth=0.5)

    # Highlight the key TEI_delta row
    if 'sc_TEI_delta' in df.index:
        idx = df.index.tolist().index('sc_TEI_delta')
        ax.axhspan(idx - 0.5, idx + 0.5, facecolor='gold', alpha=0.2, zorder=0)

    ax.set_yticks(y)
    ax.set_yticklabels(df.index)
    ax.set_xlabel('Coefficient ± 95% CI  (log-odds of extinction)')
    fig.suptitle(title, fontsize=13, y=0.98)
    ax.set_title(subtitle, fontsize=9.5, color='gray', pad=6, loc='left')
    ax.grid(axis='x', linewidth=0.3, alpha=0.5)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=140, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out_path}')

# ---- Phase 2 ----
plot_phase(
    ROOT / 'soroye_port' / 'outputs' / 'posterior_vb_summary.csv',
    title='Phase 2 — Python port validation on Soroye 2020 data',
    subtitle='Global (NA + Europe), 66 Bombus species, CRU TS climate — 13,614 rows. '
             'TEI_delta: +0.15 [0.12, 0.19] — sign matches published claim.',
    out_path=ROOT / 'soroye_port' / 'phase2_forest.png',
    color='#2c7bb6',
)

# ---- Phase 3 ----
plot_phase(
    ROOT / 'soroye_port' / 'outputs_iberia' / 'posterior_vb_summary.csv',
    title='Phase 3 — Iberia regional replication of Soroye 2020',
    subtitle='Iberia only, 31 GBIF-observed Bombus species, CRU TS climate — 528 rows. '
             'TEI_delta: +0.48 [0.27, 0.69] — Soroye\'s claim replicates regionally.',
    out_path=ROOT / 'soroye_port' / 'phase3_forest.png',
    color='#d7191c',
)
