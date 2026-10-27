from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from common_panel_utils import ROOT, despine
OUT = ROOT / 'Figure1/panels'; OUT.mkdir(parents=True, exist_ok=True)
sat = pd.read_csv(ROOT/'Figure1/data/Fig1B_satellite_acquisition_dates.csv')
fig, ax = plt.subplots(figsize=(4.85, 2.90), facecolor='white')
bottom = 0*sat.year.values.astype(float)
for col, label, color in [
    ('L5_dates_thaw','Landsat-5','#d1e5f0'),
    ('L7_dates_thaw','Landsat-7','#92c5de'),
    ('L8_dates_thaw','Landsat-8','#4393c3'),
    ('L9_dates_thaw','Landsat-9','#2166ac'),
    ('S2_dates_thaw','Sentinel-2','#f28e2b'),
    ('S1_dates_thaw','Sentinel-1','#59a14f')]:
    vals = sat[col].values
    ax.bar(sat.year, vals, bottom=bottom, width=.82, color=color, edgecolor='white', linewidth=.22, label=label)
    bottom += vals
ax.set_ylabel('Available thaw-season images per year', fontsize=8.8)
ax.set_xlabel('Year')
ax.set_xlim(1998.5, 2025.5)
ax.xaxis.set_major_locator(MultipleLocator(5))
ax.xaxis.set_minor_locator(MultipleLocator(1))
ax.tick_params(axis='x', which='major', length=5.0, width=.85)
ax.tick_params(axis='x', which='minor', length=2.5, width=.65, labelbottom=False)
ax.legend(ncol=2, frameon=False, loc='upper left', fontsize=8.6, columnspacing=.7, handlelength=1.05, handletextpad=.35)
despine(ax)
fig.subplots_adjust(left=.18,right=.995,bottom=.24,top=.97)
fig.savefig(OUT/'Fig1B.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
