from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parent
tif = Path(os.environ.get('STL_S2_TIF', root.parent / 'data' / 'SLI_Sentinel2.tif'))
for number in range(1, 5):
    for script in sorted((root / f'Figure{number}' / 'code').glob('plot_*.py')):
        if script.name == 'plot_Fig1A.py' and not tif.is_file():
            continue
        subprocess.run([sys.executable, str(script)], check=True)
