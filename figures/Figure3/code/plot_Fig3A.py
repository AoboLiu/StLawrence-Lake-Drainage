from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, COLORS, ORDER4, WINDOWS, jitter, despine

OUT = ROOT / 'Figure3' / 'panels'; OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / 'Figure3' /'data' / 'Figure3A_eventweek_standardized_sameweek_anomalies.csv')
fig, axs = plt.subplots(1, 4, figsize=(12.1, 3.55), sharey=True, facecolor='white')
ylim = (-3.3, 4.2)
for ax, var in zip(axs, ORDER4):
    sub = df[df.display_name == var]
    datasets = [sub[sub.window == w]['value_z'].values for w in WINDOWS]
    pos = np.array([1, 2, 3])
    vp = ax.violinplot(datasets, positions=pos, widths=0.72, showextrema=False)
    for b in vp['bodies']:
        b.set_facecolor(COLORS[var]); b.set_edgecolor(COLORS[var]); b.set_alpha(0.18)
    bp = ax.boxplot(datasets, positions=pos, widths=0.32, patch_artist=True, showfliers=False,
                    boxprops=dict(facecolor='white', edgecolor=COLORS[var], lw=1.0, alpha=0.92),
                    medianprops=dict(color=COLORS[var], lw=1.1),
                    whiskerprops=dict(color=COLORS[var], lw=0.8),
                    capprops=dict(color=COLORS[var], lw=0.8))
    for k in ['boxes', 'medians', 'whiskers', 'caps']:
        for artist in bp[k]:
            try:
                artist.set_zorder(2)
            except Exception:
                pass
    for x, w in zip(pos, WINDOWS):
        ss = sub[sub.window == w]
        ax.scatter(np.full(len(ss), x) + jitter(len(ss)), ss.value_z,
                   s=8 + ss.events.values * 2.0, color=COLORS[var], alpha=0.34,
                   edgecolors=COLORS[var], linewidths=0.2, zorder=3)
    ax.axhline(0, color='0.6', lw=0.85, ls='--')
    ax.set_xticks(pos)
    ax.set_xticklabels(WINDOWS)
    ax.set_xlim(0.5, 3.5)
    ax.set_xlabel(var, labelpad=1.8)
    ax.set_ylim(*ylim)
    ax.tick_params(axis='x', pad=3)
    despine(ax)
axs[0].set_ylabel('Standardized same-week anomaly (SD)', fontsize=10.3)
fig.subplots_adjust(left=0.088, right=0.995, bottom=0.22, top=0.98, wspace=0.05)
fig.savefig(OUT / 'Fig3A.png', facecolor='white', bbox_inches='tight', pad_inches=0.05)
plt.close(fig)
