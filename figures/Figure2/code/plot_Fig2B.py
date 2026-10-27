from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, despine, COLORS
OUT = ROOT / 'Figure2/panels'; OUT.mkdir(parents=True, exist_ok=True)
vals = pd.read_csv(ROOT/'Figure2/data/Fig2B_group_values.csv')
fig, ax = plt.subplots(figsize=(5.45, 4.15), facecolor='white')
order=[('strict_stable','Stable lakes',COLORS['stable']),('moderate_persistent_only','Moderate drainage lakes',COLORS['moderate']),('major_persistent','Major drainage lakes',COLORS['major'])]
rng=np.random.default_rng(1)
for i,(g,lab,c) in enumerate(order,1):
    v=vals.loc[vals.persistent_group==g,'r300_frac_below_level_minus0p5m'].values
    vp=ax.violinplot(v,[i],widths=.72,showextrema=False)
    body=vp['bodies'][0]; body.set_facecolor(c); body.set_edgecolor(c); body.set_alpha(.17); body.set_zorder(1)
    bp=ax.boxplot(v,positions=[i],widths=.22,patch_artist=True,showfliers=False,
                  boxprops=dict(facecolor='white',edgecolor=c,lw=1.1),
                  medianprops=dict(color=c,lw=1.35),
                  whiskerprops=dict(color=c,lw=.9),capprops=dict(color=c,lw=.9))
    for k in ['boxes','medians','whiskers','caps']:
        for artist in bp[k]: artist.set_zorder(2)
    sample=v if len(v)<=320 else rng.choice(v,320,replace=False)
    ax.scatter(i+np.random.default_rng(i).normal(0,.055,len(sample)), sample, s=6, c=c, alpha=.32, edgecolors='none', zorder=4)
ax.set_xticks([1,2,3])
ax.set_xticklabels(['Stable lakes\n(n = 1025)','Moderate drainage lakes\n(n = 370)','Major drainage lakes\n(n = 740)'], fontsize=9.0)
ax.set_ylabel('300-m low-terrain fraction (>0.5 m below lake margin)', fontsize=9.5)
ax.set_ylim(bottom=0)
despine(ax)
fig.subplots_adjust(left=.18,right=.995,bottom=.18,top=.97)
fig.savefig(OUT/'Fig2B.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
