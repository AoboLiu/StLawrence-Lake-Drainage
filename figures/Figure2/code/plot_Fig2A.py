from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from common_panel_utils import ROOT, despine, COLORS
OUT = ROOT / 'Figure2/panels'; OUT.mkdir(parents=True, exist_ok=True)
ors = pd.read_csv(ROOT/'Figure2/data/Fig2A_adjusted_OR.csv')
fig, ax = plt.subplots(figsize=(5.25, 4.15), facecolor='white')
metrics=['r300_frac_below_level_minus0p5m','r600_frac_below_level_minus0p5m','r600_frac_below_level_minus1m','distance_to_coast_m']
labs=['300-m low-terrain fraction\n(≥0.5 m below lake margin)','600-m low-terrain fraction\n(≥0.5 m below lake margin)','600-m low-terrain fraction\n(≥1.0 m below lake margin)','Distance to coast']
ys=np.arange(4)[::-1]
ax.axvline(1,color='#777',ls='--',lw=.85)
for y,m in zip(ys,metrics):
    for grp,c,off,mark in [('major_persistent',COLORS['major'],.11,'o'),('moderate_persistent_only',COLORS['moderate'],-.11,'s')]:
        r=ors[(ors.metric==m)&(ors.case_group==grp)].iloc[0]
        val,lo,hi=float(r.OR_per_1SD),float(r.CI_low),float(r.CI_high)
        ax.errorbar(val,y+off,xerr=[[val-lo],[hi-val]],fmt=mark,color=c,ecolor=c,capsize=3.0,capthick=1.0,lw=1.15,ms=5.1,zorder=3)
        ax.text(hi+.035,y+off,f'{val:.2f} ({lo:.2f}, {hi:.2f})',ha='left',va='center',fontsize=8.1,color=c)
ax.set_yticks(ys)
ax.set_yticklabels(labs,fontsize=8.6)
ax.set_xlabel('Adjusted odds ratio per 1 SD (95% CI)')
ax.set_xlim(.72,3.38)
ax.legend(handles=[Line2D([0],[0],marker='o',ls='',mfc=COLORS['major'],mec=COLORS['major'],ms=5.3,label='Major drainage lakes'), Line2D([0],[0],marker='s',ls='',mfc=COLORS['moderate'],mec=COLORS['moderate'],ms=5.3,label='Moderate drainage lakes')], loc='lower right', frameon=False, fontsize=8.6, handletextpad=.4, labelspacing=.35)
despine(ax)
fig.subplots_adjust(left=.28,right=.995,bottom=.16,top=.97)
fig.savefig(OUT/'Fig2A.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
