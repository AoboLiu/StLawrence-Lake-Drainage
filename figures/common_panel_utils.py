from pathlib import Path
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rasterio
from rasterio.windows import Window, bounds as window_bounds
from pyproj import Transformer
from matplotlib.patches import Rectangle

plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 10.4,
    'axes.labelsize': 11.5,
    'xtick.labelsize': 9.8,
    'ytick.labelsize': 9.8,
    'legend.fontsize': 9.2,
    'axes.linewidth': 0.85,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'savefig.dpi': 600,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

ROOT = Path(__file__).resolve().parent
S2 = Path(os.environ.get('STL_S2_TIF', str(ROOT.parent / 'data' / 'SLI_Sentinel2.tif')))

COLORS = {
    'major': '#c23b48',
    'moderate': '#e58e16',
    'temporary': '#8060bd',
    'other': '#9ecae1',
    'hls': '#6b7785',
    'stable': '#8aa0b8',
    'q1': '#4e86b8',
    'q4': '#c84d5c',
}

def despine(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def panel_letter(ax, s, x=-0.08, y=1.02):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=14.0,
            fontweight='bold', ha='left', va='bottom', clip_on=False)

def read_tight_rgb(path, pad_pixels=10):
    with rasterio.open(path) as src:
        valid = src.dataset_mask() > 0
        rows, cols = np.where(valid)
        if len(rows) == 0:
            rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1)
            return rgb, [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
        r0 = max(int(rows.min()) - pad_pixels, 0)
        r1 = min(int(rows.max()) + 1 + pad_pixels, src.height)
        c0 = max(int(cols.min()) - pad_pixels, 0)
        c1 = min(int(cols.max()) + 1 + pad_pixels, src.width)
        win = Window(c0, r0, c1-c0, r1-r0)
        rgb = np.moveaxis(src.read([1, 2, 3], window=win), 0, -1)
        b = window_bounds(win, src.transform)
        return rgb, [b[0], b[2], b[1], b[3]]

def enhance_rgb(rgb, gain=1.06, gamma=0.94):
    arr = rgb.astype(np.float32) / 255.0
    arr = np.clip(arr * gain, 0, 1)
    return np.clip(arr ** gamma, 0, 1)

def fmt_degree(v, hemi_pos, hemi_neg):
    num = f'{abs(v):.2f}'.rstrip('0').rstrip('.')
    return f'{num}°' + (hemi_neg if v < 0 else hemi_pos)

def add_lonlat_ticks(ax, lon_step=0.5, lat_step=0.25, rotate_y=True):
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    inv = Transformer.from_crs('EPSG:3338', 'EPSG:4326', always_xy=True)
    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:3338', always_xy=True)
    lons, lats = inv.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    lon_mid, lat_mid = np.mean(lons), np.mean(lats)
    lon_vals = np.arange(np.ceil(lon_min/lon_step)*lon_step,
                         np.floor(lon_max/lon_step)*lon_step + lon_step*0.1,
                         lon_step)
    lat_vals = np.arange(np.ceil(lat_min/lat_step)*lat_step,
                         np.floor(lat_max/lat_step)*lat_step + lat_step*0.1,
                         lat_step)
    if len(lon_vals):
        xx, _ = fwd.transform(lon_vals, np.full_like(lon_vals, lat_mid))
        keep = (xx >= min(x0, x1)) & (xx <= max(x0, x1))
        ax.set_xticks(xx[keep])
        ax.set_xticklabels([fmt_degree(v, 'E', 'W') for v in lon_vals[keep]], fontsize=9.7)
    if len(lat_vals):
        _, yy = fwd.transform(np.full_like(lat_vals, lon_mid), lat_vals)
        keep = (yy >= min(y0, y1)) & (yy <= max(y0, y1))
        ax.set_yticks(yy[keep])
        ax.set_yticklabels([fmt_degree(v, 'N', 'S') for v in lat_vals[keep]], fontsize=9.7)
        if rotate_y:
            for lab in ax.get_yticklabels():
                lab.set_rotation(90)
                lab.set_va('center')
                lab.set_ha('center')
    ax.tick_params(axis='x', direction='out', length=3.5, width=.8, pad=3)
    ax.tick_params(axis='y', direction='out', length=3.5, width=.8, pad=7)

def add_scalebar(ax, length_km=50, loc=(0.075, 0.075)):
    xmin, xmax = sorted(ax.get_xlim()); ymin, ymax = sorted(ax.get_ylim())
    w = xmax - xmin; h = ymax - ymin
    x = xmin + loc[0] * w; y = ymin + loc[1] * h
    L = length_km * 1000.0; H = 0.0075 * h; seg = L / 2
    ax.add_patch(Rectangle((x-0.010*w, y-0.012*h), L+0.020*w, H+0.032*h,
                           fc='white', ec='none', alpha=.55, zorder=18))
    ax.add_patch(Rectangle((x, y), seg, H, fc='black', ec='black', lw=.7, zorder=20))
    ax.add_patch(Rectangle((x+seg, y), seg, H, fc='white', ec='black', lw=.7, zorder=20))
    ax.plot([x, x], [y-.25*H, y+1.25*H], c='black', lw=.9, zorder=21)
    ax.plot([x+seg, x+seg], [y-.12*H, y+1.12*H], c='black', lw=.7, zorder=21)
    ax.plot([x+L, x+L], [y-.25*H, y+1.25*H], c='black', lw=.9, zorder=21)
    ax.text(x+L/2, y+1.85*H, f'{length_km} km', ha='center', va='bottom', fontsize=9.0, zorder=22)

from matplotlib.colors import LinearSegmentedColormap
COLORS.update({
    'Runoff': '#4C78A8', 'Snowmelt': '#8E63B6',
    'Precipitation': '#59A14F', 'Temperature': '#E15759',
})
ORDER4 = ['Runoff', 'Snowmelt', 'Precipitation', 'Temperature']
WINDOWS = ['7 d', '14 d', '30 d']
SOFT_CMAP = LinearSegmentedColormap.from_list(
    'soft', ['#fbfdfe', '#eff7f9', '#d6ebef', '#b2d8e0', '#86c0cc'])
_RNG = np.random.default_rng(42)
def jitter(n, w=0.16):
    return _RNG.uniform(-w, w, size=n)

