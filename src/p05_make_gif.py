import sys
sys.path.append('../config')

from config import RiverSP_out_file, Map_dir
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import LogNorm


def read_diminfo(path):
    with open(path) as f:
        v = [l.split('!!')[0].strip() for l in f if l.strip()]
    nx, ny = int(v[0]), int(v[1])
    west, east, north, south = map(float, v[7:11])
    return nx, ny, west, east, north, south


# --- 地図情報 ---
nx, ny, west, east, north, south = read_diminfo(os.path.join(Map_dir(), 'diminfo-06min.txt'))
dx = (east - west) / nx
dy = (north - south) / ny

up = np.fromfile(os.path.join(Map_dir(), 'uparea.bin'), dtype=np.float32)[:ny * nx].reshape(ny, nx)
up = np.ma.masked_less_equal(up, 0)          # 負値(海)をマスク

# --- 観測データ ---
df_all = pd.read_csv(RiverSP_out_file())
df_all['day'] = pd.to_datetime(df_all['day'])
days = pd.DatetimeIndex(sorted(df_all['day'].unique()))   # 観測ゼロの日もフレームに残す

df = df_all[(df_all['iy'] > 0) & (df_all['ix'] > 0)].copy()
# CaMa の ix, iy は 1 始まりを想定 → セル中心の経緯度
df['lon'] = west + (df['ix'] - 0.5) * dx
df['lat'] = north - (df['iy'] - 0.5) * dy
groups = {d: g for d, g in df.groupby('day')}

# --- 描画 ---
lat_mid = 0.5 * (north + south)
aspect = 1.0 / np.cos(np.deg2rad(lat_mid))
fig_w = 10
fig_h = fig_w * (north - south) * aspect / (east - west) + 1.2
fig, ax = plt.subplots(figsize=(fig_w, fig_h))

cmap = plt.get_cmap('Greys').copy()
cmap.set_bad('#a6cee3')                       # 海の色
im = ax.imshow(up, extent=[west, east, south, north], origin='upper',
               cmap=cmap, norm=LogNorm(vmin=up.min(), vmax=up.max()),
               interpolation='nearest')
ax.set_aspect(aspect)
fig.colorbar(im, ax=ax, shrink=0.7, label='Upstream area [m$^2$]')
ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude')

sc = ax.scatter([], [], s=14, c='red', edgecolors='k', linewidths=0.3, zorder=3)
title = ax.set_title('')


def update(i):
    day = days[i]
    g = groups.get(day)
    if g is None:
        sc.set_offsets(np.empty((0, 2)))
        n = 0
    else:
        sc.set_offsets(np.c_[g['lon'].values, g['lat'].values])
        n = len(g)
    title.set_text(f'{day:%Y-%m-%d}   n_obs = {n}')
    return sc, title


ani = FuncAnimation(fig, update, frames=len(days), blit=False)
out_gif = os.path.join(os.path.dirname(RiverSP_out_file()), 'riversp_obs.gif')
ani.save(out_gif, writer=PillowWriter(fps=4), dpi=110)
print('saved:', out_gif)