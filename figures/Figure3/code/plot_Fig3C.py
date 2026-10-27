from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, ORDER4, WINDOWS, SOFT_CMAP

OUT = ROOT / 'Figure3' / 'panels'; OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / 'Figure3' /'data' / 'Figure3C_added_deviance.csv')
mat = df.pivot(index='display_name', columns='window', values='added_deviance_pct').loc[ORDER4, WINDOWS]
fig, ax = plt.subplots(figsize=(4.75, 4.05), facecolor='white')
im = ax.imshow(mat.values, cmap=SOFT_CMAP, vmin=0, vmax=35, aspect='auto')
ax.set_xticks(range(3)); ax.set_xticklabels(WINDOWS)
ax.set_yticks(range(4)); ax.set_yticklabels(ORDER4)
ax.set_xlabel('Antecedent window')
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j, i, f'{mat.values[i,j]:.1f}%', ha='center', va='center', fontsize=8.0, color='#22323d')
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.04)
cb.set_label('Added deviance explained (%)', fontsize=10.0)
cb.ax.tick_params(labelsize=9.0)
fig.subplots_adjust(left=0.18, right=0.90, bottom=0.14, top=0.98)
fig.savefig(OUT / 'Fig3C.png', facecolor='white', bbox_inches='tight', pad_inches=0.05)
plt.close(fig)
