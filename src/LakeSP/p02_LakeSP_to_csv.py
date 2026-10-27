import sys
sys.path.append('../../config')

import os
import glob

from tqdm import tqdm
import geopandas as gpd
import pandas as pd
import numpy as np

from config import LakeSP_shp_dir, LakeSP_csv_file

# ---------- 入力 shapefile 一覧 (p01 の解凍先から自動取得, Prior のみ) ----------
shp_dir = LakeSP_shp_dir()
shp_files = sorted(glob.glob(os.path.join(shp_dir, "**", "*LakeSP_Prior*.shp"), recursive=True))
if not shp_files:
    raise FileNotFoundError(f"No LakeSP_Prior .shp files found under {shp_dir}")

# ---------- 読み込み & 結合 (ファイル単位で必要列に絞り品質フィルタ→結合) ----------
# LakeSP_Prior の列は多い。RiverSP と同様、1ファイルずつ必要列に絞り geometry を捨てて
# 品質フィルタ後に結合する（位置は PLD 座標 p_lon/p_lat を使うので geometry 不要）。
#
# NOTE: 元データの 'wse_std' は「湖内の空間ばらつき」。RiverSP と同じく後段で作る
#       「lake ごとの時間平均/標準偏差」と名前が衝突するため、読み込み時に wse_std_obs へ改名する。
NEEDED = ['lake_id', 'lake_name', 'time', 'time_str', 'wse', 'wse_u', 'wse_std',
          'area_total', 'quality_f', 'partial_f', 'dark_frac',
          'p_lon', 'p_lat', 'p_ref_wse']

parts = []
for f in tqdm(shp_files, desc="reading Prior shapefiles"):
    g = gpd.read_file(f)
    g = pd.DataFrame(g.drop(columns='geometry', errors='ignore'))
    g = g.reindex(columns=NEEDED)          # 版により欠ける列は NaN 列として補完
    g = g.rename(columns={'wse_std': 'wse_std_obs'})
    for col in ['wse', 'wse_u', 'wse_std_obs', 'area_total', 'dark_frac',
                'quality_f', 'partial_f', 'p_lon', 'p_lat', 'p_ref_wse']:
        g[col] = pd.to_numeric(g[col], errors='coerce')
    g = g.replace(-999999999999.0, np.nan)
    # 品質フィルタ（RiverSP に対応）:
    #   quality_f: 0=good, 1=bad の要約フラグ -> 1以下（=有効）を保持
    #   partial_f: 1=部分観測 -> 除外 / time_str='no_data'(未観測) と wse 欠損を除去
    m = (
        (g['quality_f'] <= 1) &
        (g['partial_f'] == 0) &
        (~np.isclose(g['wse'], -1e12, atol=1e8)) &
        g['wse'].notna() &
        (g['time_str'].astype(str) != 'no_data')
    )
    g = g.loc[m]
    if len(g):
        parts.append(g)

if not parts:
    raise RuntimeError("有効な LakeSP_Prior 観測が0件。品質フィルタ/入力を確認してください。")

LAKE_df = pd.concat(parts, ignore_index=True)
LAKE_df = LAKE_df.dropna(subset=['wse'])

# ---------- 時刻を日付へ丸め (12時間以上なら翌日 00:00) ----------
t = pd.to_datetime(LAKE_df['time_str'], errors='coerce', utc=True)
LAKE_df['time_str'] = (
    t.dt.floor('D') + pd.to_timedelta((t.dt.hour >= 12).astype(int), unit='D')
).dt.date
LAKE_df = LAKE_df.dropna(subset=['time_str'])

# ---------- lake ごとの wse 時間統計を列として付与 ----------
grp = LAKE_df.groupby('lake_id')['wse']
LAKE_df['wse_mean'] = grp.transform('mean')
LAKE_df['wse_std'] = grp.transform('std')

# ---------- ソート & 出力 ----------
LAKE_df = LAKE_df.sort_values(['lake_id', 'time'])[
    ['lake_id', 'lake_name', 'time_str', 'wse', 'wse_u', 'wse_std_obs',
     'area_total', 'quality_f', 'partial_f', 'dark_frac',
     'p_lon', 'p_lat', 'p_ref_wse', 'wse_mean', 'wse_std']
]

out_csv = LakeSP_csv_file()
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
LAKE_df.to_csv(out_csv, index=False)
print(f"Saved {len(LAKE_df)} rows ({LAKE_df['lake_id'].nunique()} lakes) -> {out_csv}")
