from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from common_panel_utils import ROOT, despine, COLORS
OUT = ROOT / 'Figure1/panels'; OUT.mkdir(parents=True, exist_ok=True)
prec = pd.read_csv(ROOT/'Figure1/data/Fig1C_timing_precision_paired758.csv')
fig, ax = plt.subplots(figsize=(4.85, 2.90), facecolor='white')
ys = [3,2,1,0]
for y, t in zip(ys, [1,3,7,14]):
    a = prec[(prec.threshold_days==t) & (prec.method=='HLS (optical)')].iloc[0]
    b = prec[(prec.threshold_days==t) & (prec.method=='HLS + S1 (optical + SAR)')].iloc[0]
    ax.plot([a.pct,b.pct],[y,y], color='#d0d0d0', lw=2.4, zorder=1)
    ax.scatter(a.pct, y, s=45, c=COLORS['hls'], zorder=3)
    ax.scatter(b.pct, y, s=45, c=COLORS['major'], zorder=3)
    ax.text(a.pct, y+.14, f'{a.pct:.1f}%', ha='center', va='bottom', fontsize=8.5, color=COLORS['hls'])
    ax.text(b.pct, y+.14, f'{b.pct:.1f}%', ha='center', va='bottom', fontsize=8.5, color=COLORS['major'])
ax.set_yticks(ys)
ax.set_yticklabels(['≤ 1 day','≤ 3 days','≤ 7 days','≤ 14 days'])
ax.set_xlabel('Drainage events resolved within interval (%)')
ax.set_xlim(0,90); ax.set_ylim(-.22,3.22)
ax.legend(handles=[
    Line2D([0],[0],marker='o',ls='',mfc=COLORS['hls'],mec='none',ms=6.2,label='HLS (optical)'),
    Line2D([0],[0],marker='o',ls='',mfc=COLORS['major'],mec='none',ms=6.2,label='HLS + S1 (optical + SAR)')],
    loc='upper right', frameon=False, fontsize=8.6)
despine(ax)
fig.subplots_adjust(left=.17,right=.995,bottom=.24,top=.97)
fig.savefig(OUT/'Fig1C.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
