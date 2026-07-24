import sys
sys.path.append('../config')

from config import SWORD_csv_file, AllocRIverGauge_dir, Map_dir, Alloc_file
import os
import shutil
import subprocess

# step1
# cd AllocRIverGauge_dir()
# ./src/alloc_gauge_latlon_only SWORD_csv_file() 1000
#   -> outputs ./gauge_alloc.txt in AllocRIverGauge_dir()
subprocess.run(
    f'./src/alloc_gauge_latlon_only {SWORD_csv_file()} 1000',
    shell=True, check=True, cwd=AllocRIverGauge_dir(),
)
step1_out = os.path.join(AllocRIverGauge_dir(), 'gauge_alloc.txt')

# step2
# cd Map_dir()/src_param
# ./allocate_level_gauge <step1_out>
#   -> outputs ./gauge_alloc.txt in Map_dir()/src_param
src_param_dir = os.path.join(Map_dir(), 'src_param')
subprocess.run(
    f'./allocate_level_gauge {step1_out}',
    shell=True, check=True, cwd=src_param_dir,
)
step2_out = os.path.join(src_param_dir, 'gauge_alloc.txt')

# step3
# move Map_dir()/src_param/gauge_alloc.txt to Alloc_file()
os.makedirs(os.path.dirname(Alloc_file()), exist_ok=True)
shutil.move(step2_out, Alloc_file())
print(f'Allocation finished: {Alloc_file()}')
