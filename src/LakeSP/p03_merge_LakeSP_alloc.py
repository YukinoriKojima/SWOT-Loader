import sys
sys.path.append('../../config')

import os

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
import pyproj

from config import LakeSP_csv_file, LakeSP_celltime_file, Map_dir


def bulk_egm08_to_egm96(lats: pd.Series, lons: pd.Series, heights: pd.Series) -> pd.Series:
    """SWOT WSE(EGM2008 geoid) を EGM96 に変換。RiverSP p03 と同一実装。"""
    if not (len(lats) == len(lons) == len(heights)):
        raise ValueError("Latitude, longitude, and height series must be of the same length.")
    # ローカルにキャッシュした PROJ ジオイドグリッドを使う（network=True は silent inf のため無効化）。
    pyproj.network.set_network_enabled(False)
    crs_egm08 = CRS.from_epsg(9518)  # WGS 84 + EGM2008 height
    crs_egm96 = CRS.from_epsg(9707)  # WGS 84 + EGM96 height
    transformer = Transformer.from_crs(crs_egm08, crs_egm96, always_xy=True)
    mask = lats.notna() & lons.notna() & heights.notna()
    out = pd.Series(index=lats.index, dtype="float64")
    X, Y, Z = transformer.transform(lons[mask].astype(float).to_numpy(),
                                    lats[mask].astype(float).to_numpy(),
                                    heights[mask].astype(float).to_numpy())
    n_bad = int((~np.isfinite(Z)).sum())
    if n_bad:
        raise RuntimeError(
            f"EGM2008->EGM96 変換が {n_bad}/{len(Z)} 点で非有限値になりました。"
            f"PROJ ジオイドグリッド(us_nga_egm08_25.tif / us_nga_egm96_15.tif)が "
            f"PROJ data dir ({pyproj.datadir.get_user_data_dir()} など)に見つからない可能性があります。"
            "https://cdn.proj.org から取得して配置し再実行してください。")
    out.loc[mask] = Z
    return out.rename("EGM96_Height")


def read_map_georef(map_dir):
    """map/params.txt から (nx, ny, csize, west, north) を読む。"""
    vals = []
    with open(os.path.join(map_dir, "params.txt")) as f:
        for line in f:
            s = line.split()
            if s:
                vals.append(s[0])
    nx = int(vals[0]); ny = int(vals[1]); csize = float(vals[3])
    west = float(vals[4]); north = float(vals[7])
    return nx, ny, csize, west, north


# --- 読み込み ---
LAKE_df = pd.read_csv(LakeSP_csv_file())

# --- PLD 中心座標 (p_lon, p_lat) を CaMa セル (ix1, iy1) へ割当 ---
# RiverSP は SWORD reach_id→ix,iy の事前割当CSVを使うが、湖は PLD 座標を直接ビニングする。
nx, ny, csize, west, north = read_map_georef(Map_dir())
LAKE_df['p_lon'] = pd.to_numeric(LAKE_df['p_lon'], errors='coerce')
LAKE_df['p_lat'] = pd.to_numeric(LAKE_df['p_lat'], errors='coerce')
LAKE_df['ix1'] = np.floor((LAKE_df['p_lon'] - west) / csize).astype('Int64') + 1
LAKE_df['iy1'] = np.floor((north - LAKE_df['p_lat']) / csize).astype('Int64') + 1
# 領域外を除外
LAKE_df = LAKE_df[LAKE_df['ix1'].between(1, nx) & LAKE_df['iy1'].between(1, ny)]
# RiverSP と揃えるため座標列名を lat_sword/lon_sword にする
LAKE_df = LAKE_df.rename(columns={'p_lat': 'lat_sword', 'p_lon': 'lon_sword'})

# --- 基本フィルタ（wse>=0） ---
LAKE_df['wse'] = pd.to_numeric(LAKE_df['wse'], errors='coerce')
LAKE_df = LAKE_df[LAKE_df['wse'].notna() & (LAKE_df['wse'] >= 0)]

# --- 高さ系変換（EGM2008→EGM96） ---
mask_h = LAKE_df['wse'].notna() & LAKE_df['lat_sword'].notna() & LAKE_df['lon_sword'].notna()
LAKE_df.loc[mask_h, 'wse'] = bulk_egm08_to_egm96(
    LAKE_df.loc[mask_h, 'lat_sword'],
    LAKE_df.loc[mask_h, 'lon_sword'],
    LAKE_df.loc[mask_h, 'wse'])

# --- 「lakeごと平均→偏差→セル平均でレベル整合→偏差復元」(RiverSP の reach を lake に置換) ---
m = LAKE_df.copy()
mu_r = m.groupby('lake_id', dropna=False)['wse'].mean()
m['mu_r'] = m['lake_id'].map(mu_r)
m['delta'] = m['wse'] - m['mu_r']
mu_cell = m.groupby(['ix1', 'iy1', 'time_str'], dropna=False)['mu_r'].transform('mean')
m['WSE'] = mu_cell + m['delta']

keys = ['ix1', 'iy1', 'time_str']

# --- 集約: WSE は平均、それ以外は代表値(first) ---
agg_rules = {c: 'first' for c in m.columns if c not in (keys + ['WSE'])}
agg_rules['WSE'] = 'mean'
celltime = m.groupby(keys, as_index=False).agg(agg_rules)

# --- 各グリッドの時間統計 (WSE_mean, WSE_std) ---
grid_stats = (celltime.groupby(['ix1', 'iy1'], as_index=False)['WSE']
              .agg(WSE_mean='mean', WSE_std='std'))
celltime = celltime.merge(grid_stats, on=['ix1', 'iy1'], how='left')
celltime = celltime.rename(columns={'wse_u': 'uncertainty', 'ix1': 'ix', 'iy1': 'iy', 'time_str': 'day'})

# ---- グリッドごとに日次補間して WSE_mean_interp / WSE_std_interp ----
celltime['day'] = pd.to_datetime(celltime['day'])
records = []
for (ix, iy), g in celltime.dropna(subset=['WSE']).groupby(['ix', 'iy']):
    s = g.set_index('day')['WSE'].sort_index()
    s = s[~s.index.duplicated()]
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq='D')
    s_lin = s.reindex(full_idx).interpolate(method='time')
    records.append({'ix': ix, 'iy': iy,
                    'WSE_mean_interp': s_lin.mean(),
                    'WSE_std_interp': s_lin.std(ddof=1)})
interp_df = pd.DataFrame(records, columns=['ix', 'iy', 'WSE_mean_interp', 'WSE_std_interp'])
celltime = celltime.merge(interp_df, on=['ix', 'iy'], how='left')

# --- 出力 ---
out_csv = LakeSP_celltime_file()
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
celltime = celltime.sort_values(['ix', 'iy', 'day'])
celltime.to_csv(out_csv, index=False)
print(f"Saved {len(celltime)} cell-time rows ({celltime[['ix','iy']].drop_duplicates().shape[0]} cells) -> {out_csv}")
