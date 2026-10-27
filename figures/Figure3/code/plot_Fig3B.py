from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, COLORS, ORDER4, WINDOWS, despine

OUT = ROOT / 'Figure3' / 'panels'; OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / 'Figure3' /'data' / 'Figure3B_IRR_profiles.csv')
fig, axs = plt.subplots(1, 4, figsize=(12.1, 3.55), sharey=True, facecolor='white')
ylim = (0.25, 2.30)
for ax, var in zip(axs, ORDER4):
    sub = df[df.display_name == var].set_index('window').loc[WINDOWS].reset_index()
    for i, row in enumerate(sub.itertuples(index=False), start=1):
        ax.errorbar(i, row.IRR,
                    yerr=[[row.IRR - row.CI_low], [row.CI_high - row.IRR]],
                    fmt='o', color=COLORS[var], ecolor=COLORS[var], elinewidth=1.2,
                    capsize=3.0, markersize=5.0, zorder=3)
        txt = f'{row.IRR:.2f} ({row.CI_low:.2f}, {row.CI_high:.2f})'
        ax.text(i + 0.11, row.IRR - 0.03, txt, color=COLORS[var], fontsize=7.1,
                ha='left', va='center', rotation=90)
    ax.axhline(1, color='0.6', lw=0.85, ls='--')
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(WINDOWS)
    ax.set_xlim(0.5, 3.5)
    ax.set_xlabel(var, labelpad=1.8)
    ax.set_ylim(*ylim)
    ax.tick_params(axis='x', pad=3)
    despine(ax)
axs[0].set_ylabel('Incidence rate ratio per 1 SD (with 95% CI)', fontsize=10.2)
fig.subplots_adjust(left=0.092, right=0.995, bottom=0.22, top=0.98, wspace=0.06)
fig.savefig(OUT / 'Fig3B.png', facecolor='white', bbox_inches='tight', pad_inches=0.05)
plt.close(fig)
