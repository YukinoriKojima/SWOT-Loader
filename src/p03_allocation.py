import sys
sys.path.append('../config')

from config import SWORD_csv_file, AllocRIverGauge_dir, Map_dir, Alloc_file, Alloc_mode
import os
import shutil
import subprocess
import matplotlib.pyplot as plt
import pandas as pd

# step1
# cd AllocRIverGauge_dir()
# latlon: ./src/alloc_gauge_latlon_only SWORD_csv_file() 1000
#         (nearest 30sec pixel with uparea >= 1000 km2; the reach's size is not used)
# area  : ./src/alloc_gauge_latlon_area SWORD_csv_file() global30
#         (the pixel nearby minimising the uparea error against facc plus the location error;
#          pixels under 5% of facc are skipped)
#   -> outputs ./gauge_alloc.txt in AllocRIverGauge_dir()
if Alloc_mode() == 'area':
    cmd = f'./src/alloc_gauge_latlon_area {SWORD_csv_file()} global30'
else:
    cmd = f'./src/alloc_gauge_latlon_only {SWORD_csv_file()} 1000'
subprocess.run(cmd, shell=True, check=True, cwd=AllocRIverGauge_dir(), stdout=subprocess.DEVNULL)
step1_out = os.path.join(AllocRIverGauge_dir(), 'gauge_alloc.txt')
step1_keep = os.path.splitext(Alloc_file())[0] + '_step1.txt'
os.makedirs(os.path.dirname(Alloc_file()), exist_ok=True)
shutil.copy(step1_out, step1_keep)

# step2: the step-1 pixel ("ID, lat, lon, area") -> the CaMa cell
# latlon: cd Map_dir()/src_param; ./allocate_level_gauge <step1_out>  -> ./gauge_alloc.txt there
# area  : allocate_level_gauge.py, the port of its cell choice (the Fortran crashes on rivers that leave
#         the regional high-res map, ARB_06min); same cells on the gauges it does not crash on
if Alloc_mode() == 'area':
    from allocate_level_gauge import main as allocate_level_gauge
    allocate_level_gauge(step1_out, Map_dir(), Alloc_file())
else:
    src_param_dir = os.path.join(Map_dir(), 'src_param')
    subprocess.run(
        f'./allocate_level_gauge {step1_out}',
        shell=True, check=True, cwd=src_param_dir, stdout=subprocess.DEVNULL,
    )
    step2_out = os.path.join(src_param_dir, 'gauge_alloc.txt')
    # step3
    # move Map_dir()/src_param/gauge_alloc.txt to Alloc_file(); the step-1 output is kept beside it
    shutil.move(step2_out, Alloc_file())
os.remove(step1_out)
print(f'Allocation finished: {Alloc_file()} (step 1: {step1_keep})')

aloc = pd.read_csv(Alloc_file(), sep=r"\s+")
plt.scatter(aloc['ix1'], aloc['iy1'])
plt.xlim(0, None), plt.ylim(0, None)
plt.savefig(os.path.dirname(Alloc_file())+'/'+os.path.basename(Alloc_file()).split('.')[0]+'.png')
print(os.path.dirname(Alloc_file())+'/'+os.path.basename(Alloc_file()).split('.')[0]+'.png')
