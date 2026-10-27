"""Merge SWOT RiverSP reach WSE with the SWORD allocation into a daily cell-level WSE table.

Inputs (config, SWORD_REGION=sa_arb):
  RiverSP_dir()   SWOT_L2_HR_RiverSP_Reach_<cycle>_<pass>_<cont>_<t0>_<t1>_<CRID>_<counter>.shp (dbf read only)
  SWORD_csv_file() p02 output: label_from_zero, lat, lon, facc, reach_id, width (the reach_id is SWORD v16's,
                   which the RiverSP products carry)
  Alloc_file()     p03 output (allocate_level_gauge): ID (= label_from_zero), ..., Type, ix1, iy1 (1-based)
  Map_dir()        uparea.bin, params.txt
Steps:
  1. granules: one per cycle_pass; CRID PIC2 > PGC0 > PIC0 (PGC0 and PIC0 overlap 2023-11 .. 2024-01), then the
     largest product counter (_02, _03 reissues)
  2. reaches: wse valid (> -1e9), reach_q < 3 (3 = bad), time_str a date
  3. reach -> cell by the allocation (Type -9: not allocated, dropped); per reach and day the mean wse / wse_u
  4. per cell and day, the reach whose facc is closest to the cell's uparea (|log(facc / uparea)|)
  5. convert WSE from EGM2008 (SWOT default) to EGM96 geoid via pyproj
Output RiverSP_out_file(): ix, iy (1-based), day, WSE (EGM96), uncertainty (wse_u), lat_y, lon_y (the reach centre),
reach_id, facc, uparea_cell [km2]

Needs pyogrio (not in .venv_sword); e.g. run with HOOPE-IEnKS_CMF/.venv_notebook:
  SWORD_REGION=sa_arb /work/a06/ykojima/HOOPE-IEnKS_CMF/.venv_notebook/bin/python p04_merge_riversp.py
"""
import sys
sys.path.append('../config')

from config import SWORD_csv_file, Alloc_file, Map_dir, RiverSP_dir, RiverSP_out_file
import glob
import os
import re

import numpy as np
import pandas as pd
import pyogrio
from pyproj import Transformer

PAT = re.compile(r"Reach_(\d+)_(\d+)_[A-Z]+_(\d{8}T\d{6})_\d{8}T\d{6}_(P[GI]C\d)_(\d+)\.shp$")
CRID_RANK = {"PIC2": 2, "PGC0": 1, "PIC0": 0}
COLS = ["reach_id", "time_str", "wse", "wse_u", "reach_q"]

# 1. granules
g = []
for f in sorted(glob.glob(os.path.join(RiverSP_dir(), "SWOT_L2_HR_RiverSP_Reach_*.shp"))):
    m = PAT.search(os.path.basename(f))
    if m is None:
        print("skip (name)", f)
        continue
    g.append(dict(f=f, cp=f"{m[1]}_{m[2]}", crid=m[4], rank=CRID_RANK.get(m[4], -1), cnt=int(m[5])))
g = pd.DataFrame(g).sort_values(["cp", "rank", "cnt"])
keep = g.groupby("cp").tail(1)
print(f"granules: {len(g)} files, {len(keep)} kept (one per cycle_pass); by CRID {keep.crid.value_counts().to_dict()}")

# 2. reaches
parts = []
for f in keep.f:
    d = pyogrio.read_dataframe(f, read_geometry=False, columns=COLS)
    parts.append(d)
r = pd.concat(parts, ignore_index=True)
n0 = len(r)
r["day"] = pd.to_datetime(r.time_str.str[:10], format="%Y-%m-%d", errors="coerce")
ok = (r.wse > -1e9) & (r.reach_q < 3) & r.day.notna()
print(f"reach records: {n0}; valid wse {(r.wse > -1e9).sum()}, of which reach_q < 3 {ok.sum()}")
r = r[ok]
r["reach_id"] = r.reach_id.astype(np.int64)

# 3. reach -> cell
s = pd.read_csv(SWORD_csv_file())
a = pd.read_csv(Alloc_file(), sep=r"\s+")
a = a[a.Type != -9][["ID", "ix1", "iy1", "Type"]].rename(columns={"ID": "label_from_zero"})
s = s.merge(a, on="label_from_zero", how="inner")
s["reach_id"] = s.reach_id.astype(np.int64)
r = r.merge(s[["reach_id", "ix1", "iy1", "facc", "lat", "lon"]], on="reach_id", how="inner")
print(f"records on allocated reaches: {len(r)} ({r.reach_id.nunique()} reaches)")
r = (r.groupby(["reach_id", "day"], as_index=False)
      .agg(wse=("wse", "mean"), wse_u=("wse_u", "mean"), ix1=("ix1", "first"), iy1=("iy1", "first"),
           facc=("facc", "first"), lat=("lat", "first"), lon=("lon", "first")))

# 4. one reach per cell and day: facc closest to the cell's uparea
p = open(os.path.join(Map_dir(), "params.txt")).read().split()
NX, NY = int(p[0]), int(p[4])
up = np.fromfile(os.path.join(Map_dir(), "uparea.bin"), np.float32)[:NX * NY].reshape(NY, NX) * 1e-6   # km2
r["uparea_cell"] = up[r.iy1.to_numpy() - 1, r.ix1.to_numpy() - 1]
r["mis"] = np.abs(np.log(np.maximum(r.facc, 1e-3) / np.maximum(r.uparea_cell, 1e-3)))
r = r.sort_values(["ix1", "iy1", "day", "mis"])
n_multi = int((r.groupby(["ix1", "iy1", "day"]).size() > 1).sum())
o = r.groupby(["ix1", "iy1", "day"], as_index=False).first()
print(f"cell-days: {len(o)} ({n_multi} with more than one reach); cells {o.groupby(['ix1', 'iy1']).ngroups}")

o = o.rename(columns={"ix1": "ix", "iy1": "iy", "wse": "WSE", "wse_u": "uncertainty", "lat": "lat_y", "lon": "lon_y"})

# 5. Convert WSE from EGM2008 (SWOT default) to EGM96 geoid
t_2008_to_ell = Transformer.from_crs("EPSG:9518", "EPSG:4979", always_xy=True)
t_ell_to_96 = Transformer.from_crs("EPSG:4979", "EPSG:5773", always_xy=True)
_, _, h_ell = t_2008_to_ell.transform(o.lon_y.to_numpy(), o.lat_y.to_numpy(), o.WSE.to_numpy())
_, _, wse_96 = t_ell_to_96.transform(o.lon_y.to_numpy(), o.lat_y.to_numpy(), h_ell)
print(f"EGM2008 -> EGM96: mean shift {np.nanmean(wse_96 - o.WSE.to_numpy()):.3f} m, "
      f"range [{np.nanmin(wse_96 - o.WSE.to_numpy()):.3f}, {np.nanmax(wse_96 - o.WSE.to_numpy()):.3f}] m")
o["WSE"] = wse_96

o["day"] = o.day.dt.strftime("%Y-%m-%d")
o = o[["ix", "iy", "day", "WSE", "uncertainty", "lat_y", "lon_y", "reach_id", "facc", "uparea_cell"]]
os.makedirs(os.path.dirname(RiverSP_out_file()), exist_ok=True)
o.to_csv(RiverSP_out_file(), index=False)
print(f"saved {RiverSP_out_file()}")
