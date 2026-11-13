"""
Step 06: forest plot of a coefficient summary table.

Port of plot_forest.py: one plot per run, from a summary CSV with
mean/sd columns (posterior_vb_summary.csv from 05b or
posterior_summary.csv from 05). Title, subtitle and color are
parameters; dropping the Intercept, sorting by mean, 1.96*sd
confidence bars and highlighting the sc_TEI_delta row are fixed
by the method. Output: forest.png
"""
from __future__ import annotations

from pathlib import Path
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Forest plot of coefficient summaries")
    p.add_argument("--summary", type=Path, required=True,
                   help="summary CSV with mean/sd columns (05b or 05 output)")
    p.add_argument("--title", type=str, required=True)
    p.add_argument("--subtitle", type=str, required=True)
    p.add_argument("--color", type=str, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    a = parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(a.summary, index_col=0)
    df = df.drop('Intercept', errors='ignore')
    df = df.sort_values('mean', ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(df))
    ci = 1.96 * df['sd']
    ax.errorbar(df['mean'], y, xerr=ci, fmt='o', color=a.color,
                ecolor=a.color, capsize=4, markersize=7, elinewidth=1.5)
    ax.axvline(0, color='k', linewidth=0.5)

    if 'sc_TEI_delta' in df.index:
        idx = df.index.tolist().index('sc_TEI_delta')
        ax.axhspan(idx - 0.5, idx + 0.5, facecolor='gold', alpha=0.2, zorder=0)

    ax.set_yticks(y)
    ax.set_yticklabels(df.index)
    ax.set_xlabel('Coefficient ± 95% CI  (log-odds of extinction)')
    fig.suptitle(a.title, fontsize=13, y=0.98)
    ax.set_title(a.subtitle, fontsize=9.5, color='gray', pad=6, loc='left')
    ax.grid(axis='x', linewidth=0.3, alpha=0.5)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(a.output_dir / 'forest.png', dpi=140, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {a.output_dir / "forest.png"}')


if __name__ == '__main__':
    main()
