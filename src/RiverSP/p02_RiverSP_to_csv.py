import sys
sys.path.append('../../config')

import os
import glob

from tqdm import tqdm
import geopandas as gpd
import pandas as pd
import numpy as np

from config import RiverSP_shp_dir, RiverSP_csv_file

# ---------- 入力 shapefile 一覧 (p01 の解凍先から自動取得) ----------
shp_dir = RiverSP_shp_dir()
shp_files = sorted(glob.glob(os.path.join(shp_dir, "**", "*.shp"), recursive=True))
if not shp_files:
    raise FileNotFoundError(f"No .shp files found under {shp_dir}")

# ---------- 読み込み & 結合 (ファイル単位で必要列に絞り品質フィルタ→結合) ----------
# NOTE: 処理版 "D" の Reach shapefile は ~130 列ある。全ファイルを生のまま concat すると
# メモリ枯渇で OOM kill される（実際に発生）。1ファイルずつ必要列だけ残し、geometry を捨て、
# 品質フィルタを適用してから結合することでメモリを大幅に削減する。
NEEDED = ['reach_id', 'time', 'time_str', 'wse', 'wse_u',
          'slope', 'slope_u', 'reach_q', 'partial_f', 'dark_frac']

parts = []
for f in tqdm(shp_files, desc="reading shapefiles"):
    g = gpd.read_file(f)
    g = pd.DataFrame(g.drop(columns='geometry', errors='ignore'))
    g = g.reindex(columns=NEEDED)          # 版により欠ける列は NaN 列として補完
    for col in ['wse', 'wse_u', 'slope', 'slope_u', 'dark_frac',
                'reach_q', 'partial_f']:
        g[col] = pd.to_numeric(g[col], errors='coerce')
    g = g.replace(-999999999999.0, np.nan)
    # reach_q: 0=Good,1=Suspect,2=Degraded,3=Bad -> 1以下 / partial_f: 1=部分観測 -> 除外 / wse欠損除去
    m = (
        (g['reach_q'] <= 1) &
        (g['partial_f'] == 0) &
        (~np.isclose(g['wse'], -1e12, atol=1e8)) &
        g['wse'].notna()
    )
    g = g.loc[m]
    if len(g):
        parts.append(g)

SWOT_HR_df = pd.concat(parts, ignore_index=True)
SWOT_HR_df = SWOT_HR_df.dropna(subset=['wse'])

# ---------- 時刻を日付へ丸め (12時間以上なら翌日 00:00) ----------
t = pd.to_datetime(SWOT_HR_df['time_str'], errors='coerce', utc=True)
SWOT_HR_df['time_str'] = (
    t.dt.floor('D') + pd.to_timedelta((t.dt.hour >= 12).astype(int), unit='D')
).dt.date

# ---------- reach ごとの wse 統計を列として付与 ----------
grp = SWOT_HR_df.groupby('reach_id')['wse']
SWOT_HR_df['wse_mean'] = grp.transform('mean')
SWOT_HR_df['wse_std'] = grp.transform('std')

# ---------- ソート & 出力 ----------
SWOT_HR_df = SWOT_HR_df.sort_values(['reach_id', 'time'])[
    ['reach_id', 'time_str', 'wse', 'wse_u', 'slope', 'slope_u',
     'reach_q', 'partial_f', 'dark_frac', 'wse_mean', 'wse_std']
]

out_csv = RiverSP_csv_file()
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
SWOT_HR_df.to_csv(out_csv, index=False)
print(f"Saved {len(SWOT_HR_df)} rows -> {out_csv}")
