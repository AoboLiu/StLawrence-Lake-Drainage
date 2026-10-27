from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, despine, COLORS
OUT = ROOT / 'Figure2/panels'; OUT.mkdir(parents=True, exist_ok=True)
quart = pd.read_csv(ROOT/'Figure2/data/Fig2C_quartile_observed_fraction.csv')
fig, ax = plt.subplots(figsize=(5.95, 4.15), facecolor='white')
ranges={q:(quart[quart.quartile==q].metric_min.min(),quart[quart.quartile==q].metric_max.max()) for q in ['Q1','Q2','Q3','Q4']}
for typ,c,mark,off,lab in [('Major',COLORS['major'],'o',-.045,'Major drainage lakes'),('Moderate',COLORS['moderate'],'s',.045,'Moderate drainage lakes')]:
    d=quart[quart.type==typ]
    x=range(1,5)
    x=[v+off for v in x]
    ax.errorbar(x,d.pct,yerr=[d.pct-d.ci_low,d.ci_high-d.pct],fmt=mark+'-',color=c,ecolor=c,capsize=3.2,lw=1.35,ms=5.2,label=lab)
ax.set_xticks(range(1,5))
ax.set_xticklabels([f'{q} ({ranges[q][0]:.2f}–{ranges[q][1]:.2f})' for q in ['Q1','Q2','Q3','Q4']], fontsize=8.3)
ax.margins(x=0.06)
ax.set_xlabel('Quartile of 300-m low-terrain fraction')
ax.set_ylabel('Drainage proportion (%)')
ax.set_ylim(bottom=0)
ax.legend(frameon=False,loc='upper left',fontsize=8.9)
despine(ax)
fig.subplots_adjust(left=.16,right=.995,bottom=.24,top=.97)
fig.savefig(OUT/'Fig2C.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
