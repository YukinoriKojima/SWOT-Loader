import sys
sys.path.append('../config')

from config import SWORD_raw_dir
import os
import pandas as pd
import numpy as np
import requests, subprocess
import netCDF4 as nc



os.makedirs(f'{SWORD_raw_dir()}', exist_ok=True)
url='https://zenodo.org/records/10013982/files/SWORD_v16_netcdf.zip?download=1'
subprocess.run(f'wget -O {SWORD_raw_dir()}.zip {url}', shell=True)
subprocess.run(f'unzip {SWORD_raw_dir()}.zip -d {SWORD_raw_dir()}', shell=True)