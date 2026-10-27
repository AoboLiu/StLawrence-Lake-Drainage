from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, despine, COLORS
OUT = ROOT / 'Figure2/panels'; OUT.mkdir(parents=True, exist_ok=True)
cum = pd.read_csv(ROOT/'Figure2/data/Fig2D_Q1_Q4_cumulative_first_major.csv')
fig, ax = plt.subplots(figsize=(5.45, 4.15), facecolor='white')
for q,c in [('Q1',COLORS['q1']),('Q4',COLORS['q4'])]:
    d=cum[cum.quartile==q]
    lab=f'{q} ({d.metric_min.iloc[0]:.2f}–{d.metric_max.iloc[0]:.2f})'
    ax.plot(d.year,d.pct,marker='o',ms=4.8,lw=1.55,color=c,label=lab)
    ax.fill_between(d.year,d.ci_low,d.ci_high,color=c,alpha=.12)
ax.set_xlabel('Year')
ax.set_ylabel('Cumulative major drainage proportion (%)')
ax.set_ylim(bottom=0)
ax.set_xticks(sorted(cum.year.unique()))
ax.legend(title='300-m low-terrain fraction', frameon=False, loc='upper left', fontsize=8.7, title_fontsize=8.8)
despine(ax)
fig.subplots_adjust(left=.16,right=.995,bottom=.16,top=.97)
fig.savefig(OUT/'Fig2D.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
