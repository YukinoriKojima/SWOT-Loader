import sys
sys.path.append('../config')

from config import SWORD_csv_file, Alloc_file, Allocated_csv_file
import os
import pandas as pd

# original SWORD table: label_from_zero, lat, lon, reach_id
orig = pd.read_csv(SWORD_csv_file())

# allocated gauges on CaMa-Flood river network (whitespace-separated)
# first column "ID" corresponds to "label_from_zero" in the original table
alloc = pd.read_csv(Alloc_file(), sep=r'\s+')

# merge: keep allocated gauges, attach the original attributes (reach_id etc.)
# overlapping lat/lon: allocated ones stay as-is, original ones get "_sword" suffix
merged = alloc.merge(
    orig, left_on='ID', right_on='label_from_zero', how='left', suffixes=('', '_sword'),
)

os.makedirs(os.path.dirname(Allocated_csv_file()), exist_ok=True)
merged.to_csv(Allocated_csv_file(), index=False)
print(f'Merged csv saved: {Allocated_csv_file()} ({len(merged)} rows)')
