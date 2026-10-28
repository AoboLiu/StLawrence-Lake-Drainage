# St. Lawrence Island Lake Drainage

Data and code accompanying the manuscript:

**Day-to-Week Timing Reveals Cooler Spring Conditions and Concentrated Runoff Before Thermokarst Lake Drainage**

**Authors:** Yating Chen<sup>1,2</sup>, Aobo Liu<sup>1,2,*</sup>, Chengxin Wang<sup>1,3</sup>, and Xiao Cheng<sup>2,4</sup>

1. College of Geography and Environment, Shandong Normal University; Jinan 250014, China.
2. Key Laboratory of Comprehensive Observation of Polar Environment (Sun Yat-sen University), Ministry of Education, Zhuhai 519082, China.
3. Key Research Institute of Yellow River Civilization and Sustainable Development & Yellow River Civilization by Provincial and Ministerial Co-construction of Collaborative Innovation Center, Henan University, Kaifeng 475001, China.
4. School of Geospatial Engineering and Science, Sun Yat-sen University, and Southern Marine Science and Engineering Guangdong Laboratory (Zhuhai), Zhuhai 519082, China.

\* **Corresponding author:** Aobo Liu ([lab2016bnu@foxmail.com](mailto:lab2016bnu@foxmail.com)).

**Manuscript status:** In preparation for submission. A publication DOI has not been assigned in this repository.

## Overview

This repository provides derived data and code for studying thermokarst lake drainage on St. Lawrence Island, Alaska. The materials cover satellite-based event identification and timing, lake and terrain characteristics, regional weekly hydroclimatic analyses, matched case-crossover comparisons, and the main-figure panels.

The original research package contains 27 CSV files, 22 Python scripts, 6 Google Earth Engine JavaScript files, and 16 PNG panels. An unchanged copy of the supplied package is available as [StLawrence_OpenResearch.zip](archive/StLawrence_OpenResearch.zip). Its data, code, and figures are also available as individual files below.

## Repository contents

| Path | Contents |
| --- | --- |
| [`data/`](data/) | Derived lake, terrain, event-timing, Sentinel-1, and climate tables |
| [`gee/`](gee/) | Google Earth Engine scripts for water dynamics, HLS, Sentinel-1, terrain, and climate extraction |
| [`processing/`](processing/) | Python scripts for candidate-event reconstruction and timing refinement |
| [`analysis/`](analysis/) | Regional weekly and matched case-crossover analyses |
| [`figures/`](figures/) | Source tables, plotting scripts, and supplied PNG panels for Figures 1–4 |
| [`requirements.txt`](requirements.txt) | Python dependencies |
| [`archive/`](archive/) | Original ZIP package, preserved without changes |
| [`docs/data_inventory.csv`](docs/data_inventory.csv) | CSV file inventory, row counts, and column names |
| [`docs/original_file_manifest.csv`](docs/original_file_manifest.csv) | Sizes and SHA-256 checksums of the original 74 files |
| [`docs/README_original.md`](docs/README_original.md) | README supplied in the original package |

## Running the supplied analyses

Use a Python environment with the packages listed in `requirements.txt`. Run the following commands from the repository root:

```bash
python -m pip install -r requirements.txt
python analysis/regional_weekly.py
python analysis/case_crossover.py
python processing/s1_timing.py
```

The regional and matched analyses read `data/regional_weekly.csv` and `data/matched_climate.csv`, respectively. Their outputs are written to `results/regional/` and `results/matched/`. The Sentinel-1 timing script reads the manifest, track, and observation tables in `data/` and writes a reduced output table to `results/s1_timing.csv`; it does not replace the supplied `data/s1_timing.csv`.

The regional table contains 180 seasonal weeks from 2016–2024. Matched cases have event years from 2018–2024, with case and historical-control windows spanning 2016–2024. These tables have different sampling units; see their columns and the analysis scripts before combining them.

Dependency versions are not pinned in the supplied package. The files have been checked for completeness and Python syntax, but the scientific workflows have not been rerun as part of repository preparation.

## Main figures

```bash
python figures/run_figures.py
```

The plotting scripts read the bundled CSV files in `figures/Figure*/data/` and write panels to the corresponding `panels/` folders. They do not automatically use newly fitted tables in `results/`. The supplied PNGs are retained so the original panels can be inspected directly.

Figure 1A additionally requires a Sentinel-2 GeoTIFF. Set the `STL_S2_TIF` environment variable to its path, or place it at `data/SLI_Sentinel2.tif`. The figure runner skips this panel when the raster is unavailable. Figure 4B is supplied as a PNG only.

## Upstream Earth Engine processing

Run the JavaScript files in a configured Google Earth Engine environment. Replace the `YOUR_PROJECT` asset placeholders and supply the island boundary and other inputs required by each script. Full upstream reconstruction also requires intermediate exports, including HLS yearly CSV files, that are not all included here.

The scripts reference GLAD Collection 2 annual water dynamics, NASA HLS Version 2, Sentinel-1 GRD, ArcticDEM V4, ERA5-Land daily aggregates, and Daymet Version 4. The collection identifiers and processing settings are recorded in the scripts. ArcticDEM is a 2 m input mosaic; the terrain script uses a 10 m calculation scale.

Regional antecedent exposures are calculated before each regional week starts. Matched antecedent exposures are calculated before the `index_start` date in the climate manifest. The scripts and included tables define the analysis windows used in this package.

## Citation and contact

Until a published citation is available, identify the accompanying manuscript as:

> Liu, A., Chen, Y., Wang, C., and Cheng, X. *Day-to-Week Timing Reveals Cooler Spring Conditions and Concentrated Runoff Before Thermokarst Lake Drainage*. Manuscript in preparation for submission.

When referring to the repository, include its URL and the commit or release used. For scientific questions, contact Yating Chen at [chenyt2016bnu@gmail.com](mailto:chenyt2016bnu@gmail.com).

## License and provenance

No data or code reuse license was specified in the supplied package. This repository does not assign a license on the authors' behalf. Third-party source data remain subject to their providers' terms.
