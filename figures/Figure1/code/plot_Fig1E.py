from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, despine, COLORS
OUT = ROOT / 'Figure1/panels'; OUT.mkdir(parents=True, exist_ok=True)
weekly = pd.read_csv(ROOT/'Figure1/data/Fig1E_events_by_week_533.csv')
fig, ax = plt.subplots(figsize=(5.05, 3.15), facecolor='white')
weeks = np.arange(int(weekly.week_from_may1.min()), int(weekly.week_from_may1.max())+1)
for cls, col, off, label in [('Major',COLORS['major'],-.10,'Major drainage events'),('Moderate',COLORS['moderate'],.10,'Moderate drainage events')]:
    s = weekly[weekly.event_class==cls].set_index('week_from_may1').n
    vals = np.array([int(s.get(w,0)) for w in weeks])
    xs = weeks + off
    ax.vlines(xs,0,vals,color=col,lw=1.0)
    ax.scatter(xs,vals,s=28,c=col,label=label,zorder=3)
shade_n = int(weekly.loc[weekly.week_from_may1.between(3,7),'n'].sum())
pct = 100*shade_n/int(weekly.n.sum())
ax.axvspan(2.5,7.5,color='#e8e8e8',alpha=.72,zorder=0)
ytop = max(weekly.n.max()*1.12, 1)
ax.set_ylim(0, ytop)
ax.text(3.1, ytop*.80, f'{pct:.1f}% of events\nin weeks 3–7', ha='left', va='top', fontsize=8.6, color='#555', bbox=dict(fc='white',ec='none',alpha=.55,pad=1.0))
ax.set_ylabel('Number of lake drainage events')
ax.set_xlabel('Week of thaw season (May 1–Sep 17)')
ax.set_xlim(.6, 20.4)
ax.set_xticks(np.arange(1,21,2))
ax.legend(frameon=False,loc='upper right',fontsize=8.7,markerscale=0.95,handletextpad=0.35,labelspacing=0.35)
despine(ax)
fig.subplots_adjust(left=.16,right=.995,bottom=.18,top=.97)
fig.savefig(OUT/'Fig1E.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
