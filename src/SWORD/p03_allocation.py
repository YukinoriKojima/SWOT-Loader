import sys
sys.path.append('../config')

from config import AllocGaugeInput_file, Map_dir, Alloc_file
import os
import shutil
import subprocess

# input: gauge list already allocated on the high-res river network
#        (brought from outside, e.g. AllocRiverGauge/output/gauge_alloc_mekong_sword.txt)
gauge_input = AllocGaugeInput_file()

# step1
# cd Map_dir()/src_param
# ./allocate_level_gauge <gauge_input>
#   -> outputs ./gauge_alloc.txt in Map_dir()/src_param
src_param_dir = os.path.join(Map_dir(), 'src_param')
subprocess.run(
    f'./allocate_level_gauge {gauge_input}',
    shell=True, check=True, cwd=src_param_dir,
)
step1_out = os.path.join(src_param_dir, 'gauge_alloc.txt')

# step2
# move Map_dir()/src_param/gauge_alloc.txt to Alloc_file()
os.makedirs(os.path.dirname(Alloc_file()), exist_ok=True)
shutil.move(step1_out, Alloc_file())
print(f'Allocation finished: {Alloc_file()}')
