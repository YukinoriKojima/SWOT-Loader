import sys
sys.path.append('../config')

from config import SWORD_csv_file, SWORD_nc_file
import os
import pandas as pd
import numpy as np
import requests, subprocess
import netCDF4 as nc



with nc.Dataset(SWORD_nc_file()) as src:
  lon, lat, reach_id = src['reaches']['x'][:], src['reaches']['y'][:], src['reaches']['reach_id'][:]


df = pd.DataFrame(columns=[ 'lat', 'lon', 'reach_id', ])
df['lon'] = lon
df['lat'] = lat
df['reach_id'] = reach_id
df.to_csv(SWORD_csv_file(), index=True, index_label='label_from_zero')