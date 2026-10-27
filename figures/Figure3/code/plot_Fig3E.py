from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from common_panel_utils import ROOT, COLORS, despine

OUT = ROOT / 'Figure3' / 'panels'; OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / 'Figure3' /'data' / 'Figure3D_lag_bin_models.csv')
fig, ax = plt.subplots(figsize=(3.25, 3.95), facecolor='white')
periods = ['Week 1', 'Week 2', 'Weeks 3–4']
ypos = {'Week 1':3, 'Week 2':2, 'Weeks 3–4':1}
sub = df[df.display_name == 'Snowmelt']
color = COLORS['Snowmelt']
for period in periods:
    ss = sub[sub.period_label == period]
    for _, r in ss.iterrows():
        is_joint = (r['model'] == 'Joint three-bin model')
        y = ypos[period] + (0.10 if is_joint else -0.10)
        mfc = color if is_joint else 'white'
        ecolor = color if is_joint else '0.8'
        txtcolor = color if is_joint else '0.45'
        ax.errorbar(r.IRR, y, xerr=[[r.IRR-r.CI_low], [r.CI_high-r.IRR]],
                    fmt='o', mfc=mfc, mec=color, mew=0.85,
                    color=color, ecolor=ecolor, elinewidth=1.05,
                    capsize=2.5, markersize=4.4, zorder=3)
        ax.text(r.CI_high + 0.03, y,
                f'{r.IRR:.2f} ({r.CI_low:.2f}, {r.CI_high:.2f})',
                color=txtcolor, fontsize=6.7, ha='left', va='center')
ax.axvline(1, color='0.6', lw=0.85, ls='--')
ax.set_yticks([3,2,1])
ax.set_yticklabels([])
ax.set_xlabel('Snowmelt lag-specific IRR per 1 SD (95% CI)', fontsize=10.2)
ax.set_xlim(0.55, 2.35)
ax.set_ylim(0.5, 3.6)
handles = [
    Line2D([0],[0], marker='o', ls='', mfc=color, mec=color, ms=5.0, label='Snowmelt, joint three-bin'),
    Line2D([0],[0], marker='o', ls='', mfc='white', mec=color, ms=5.0, label='Snowmelt, separate-bin')
]
ax.legend(handles=handles, loc='upper right', frameon=False, fontsize=8.2, handletextpad=0.45, labelspacing=0.35)
despine(ax)
fig.subplots_adjust(left=0.07, right=0.995, bottom=0.18, top=0.98)
fig.savefig(OUT / 'Fig3E.png', facecolor='white', bbox_inches='tight', pad_inches=0.05)
plt.close(fig)
