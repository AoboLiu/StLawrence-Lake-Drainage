# St. Lawrence Island lake drainage

Data and scripts for satellite-based lake-drainage timing, terrain analysis, and hydroclimatic comparisons.

- `gee/`: Google Earth Engine processing
- `processing/`: lake-event reconstruction
- `analysis/`: regional weekly and matched-event analyses
- `data/`: derived analysis inputs
- `figures/`: data and scripts for Figures 1–4

Install Python packages with `pip install -r requirements.txt`. Run analyses from the repository root; use `python figures/run_figures.py` to generate the main-figure panels. Figure 1a requires a Sentinel-2 GeoTIFF supplied through `STL_S2_TIF`.

Earth Engine asset paths must be configured for the user's project. 