from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pathlib import Path
import pandas as pd
from pyproj import Transformer
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
from common_panel_utils import ROOT, S2, COLORS, read_tight_rgb, enhance_rgb, add_lonlat_ticks, add_scalebar

OUT = ROOT / 'Figure1/panels'; OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT/'Figure1/data/Fig1A_lake_categories.csv')
for c in ['major_drainage','moderate_drainage','temporary_drawdown','other_lake']:
    df[c] = df[c].astype(bool)
tr = Transformer.from_crs('EPSG:4326', 'EPSG:3338', always_xy=True)
df['x'], df['y'] = tr.transform(df.longitude.values, df.latitude.values)
rgb, extent = read_tight_rgb(S2, pad_pixels=12)
rgb = enhance_rgb(rgb)

fig, ax = plt.subplots(figsize=(7.4, 5.25), facecolor='white')
ax.imshow(rgb, extent=extent, origin='upper', zorder=0)
w = extent[1]-extent[0]; h = extent[3]-extent[2]
pad_x = 0.025*w; pad_y = 0.030*h
ax.set_xlim(extent[0]-pad_x, extent[1]+pad_x)
ax.set_ylim(extent[2]-pad_y, extent[3]+pad_y)
ax.set_aspect('equal', adjustable='box', anchor='C')
other = df[df.other_lake]; major = df[df.major_drainage]; moderate = df[df.moderate_drainage]; temp = df[df.temporary_drawdown]
pt = 3.35
ax.scatter(other.x, other.y, s=pt, c=COLORS['other'], alpha=.53, edgecolors='none', zorder=2)
ax.scatter(major.x, major.y, s=pt, c=COLORS['major'], alpha=.75, edgecolors='none', zorder=3)
ax.scatter(moderate.x, moderate.y, s=pt, c=COLORS['moderate'], alpha=.75, edgecolors='none', zorder=4)
ax.scatter(temp.x, temp.y, s=pt, facecolors='none', edgecolors=COLORS['temporary'], linewidths=.40, alpha=.80, zorder=5)
add_lonlat_ticks(ax, 0.5, 0.25, rotate_y=True)
add_scalebar(ax, 50)
handles = [
    Line2D([0],[0],marker='o',ls='',ms=5.7,mfc=COLORS['major'],mec='none',label=f'Major drainage lakes (n = {len(major)})'),
    Line2D([0],[0],marker='o',ls='',ms=5.7,mfc=COLORS['moderate'],mec='none',label=f'Moderate drainage lakes (n = {len(moderate)})'),
    Line2D([0],[0],marker='o',ls='',ms=5.7,mfc='none',mec=COLORS['temporary'],mew=.8,label=f'Temporary drawdown lakes (n = {len(temp)})'),
    Line2D([0],[0],marker='o',ls='',ms=5.7,mfc=COLORS['other'],mec='none',label=f'Other lakes (n = {len(other)})')]
leg = ax.legend(handles=handles, title=f'All lakes (n = {len(df)})', loc='upper right',
                frameon=True, facecolor='white', edgecolor='#888', framealpha=.90,
                fontsize=8.5, title_fontsize=8.9, borderpad=.48, handletextpad=.45, labelspacing=.32)
fig.subplots_adjust(left=.10,right=.99,bottom=.10,top=.97)
fig.savefig(OUT/'Fig1A.png', facecolor='white', bbox_inches='tight', pad_inches=0.03)
plt.close(fig)
print('Saved', OUT/'Fig1A.png')
