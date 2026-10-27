import sys
sys.path.append('../config')

from config import SWORD_csv_file, SWORD_nc_file
import os
import pandas as pd
import numpy as np
import requests, subprocess
import netCDF4 as nc


# reach centre, id and flow accumulation (facc [km2]); the allocation reads the first columns
# "label_from_zero, lat, lon" (lat/lon only) or "label_from_zero, lat, lon, facc" (with area)
with nc.Dataset(SWORD_nc_file()) as src:
  lon, lat, reach_id = src['reaches']['x'][:], src['reaches']['y'][:], src['reaches']['reach_id'][:]
  facc, width = src['reaches']['facc'][:], src['reaches']['width'][:]


df = pd.DataFrame(columns=[ 'lat', 'lon', 'facc', 'reach_id', 'width', ])
df['lon'] = lon
df['lat'] = lat
df['facc'] = facc
df['reach_id'] = reach_id
df['width'] = width
os.makedirs(os.path.dirname(SWORD_csv_file()), exist_ok=True)
df.to_csv(SWORD_csv_file(), index=True, index_label='label_from_zero')
