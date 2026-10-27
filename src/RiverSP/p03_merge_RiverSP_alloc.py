import sys
sys.path.append('../config')

import os

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
import pyproj

from config import RiverSP_csv_file, Allocated_csv_file, RiverSP_celltime_file


def bulk_egm08_to_egm96(lats: pd.Series, lons: pd.Series, heights: pd.Series) -> pd.Series:
    if not (len(lats) == len(lons) == len(heights)):
        raise ValueError("Latitude, longitude, and height series must be of the same length.")

    # ローカルにキャッシュした PROJ ジオイドグリッドを使う（EGM2008/EGM96）。
    # network=True だと取得失敗時に黙って inf を返すため無効化する。
    # 事前に us_nga_egm08_25.tif / us_nga_egm96_15.tif を PROJ data dir に配置しておくこと
    # （例: curl https://cdn.proj.org/us_nga_egm08_25.tif -o ~/.local/share/proj/us_nga_egm08_25.tif）。
    pyproj.network.set_network_enabled(False)

    # 複合CRSを直接指定（推奨）
    crs_egm08 = CRS.from_epsg(9518)  # WGS 84 + EGM2008 height
    crs_egm96 = CRS.from_epsg(9707)  # WGS 84 + EGM96 height

    # 変換器（経度, 緯度, 高さ の順で渡す）
    transformer = Transformer.from_crs(crs_egm08, crs_egm96, always_xy=True)

    # 欠損は素通し
    mask = lats.notna() & lons.notna() & heights.notna()
    out = pd.Series(index=lats.index, dtype="float64")

    # まとめて変換（経度・緯度・高さ）
    x_lon = lons[mask].astype(float).to_numpy()
    y_lat = lats[mask].astype(float).to_numpy()
    z_h   = heights[mask].astype(float).to_numpy()

    # itransform でもよいが、配列入力の方が高速
    X, Y, Z = transformer.transform(x_lon, y_lat, z_h)  # Z が EGM96高さに

    # PROJ はジオイドグリッド欠落時に鉛直変換を inf で返す（silent失敗）。
    # ここで検知し、黙って下流(WSE=NaN→観測ゼロ→DA無効)へ流さず即エラーにする。
    n_bad = int((~np.isfinite(Z)).sum())
    if n_bad:
        raise RuntimeError(
            f"EGM2008->EGM96 変換が {n_bad}/{len(Z)} 点で非有限値になりました。"
            "PROJ ジオイドグリッド(us_nga_egm08_25.tif / us_nga_egm96_15.tif)が "
            f"PROJ data dir ({pyproj.datadir.get_user_data_dir()} など)に見つからない可能性があります。"
            "https://cdn.proj.org から取得して配置し再実行してください。")

    out.loc[mask] = Z

    return out.rename("EGM96_Height")


# --- 読み込み & 結合 ---
SWOT_HR_df = pd.read_csv(RiverSP_csv_file())

reach_df = pd.read_csv(Allocated_csv_file())
reach_df = reach_df[['reach_id', 'ix1', 'iy1', 'lat_sword', 'lon_sword']]

merged_df = pd.merge(SWOT_HR_df, reach_df, on='reach_id', how='left')

# --- 基本フィルタ（ix1>=0, wse>=0） ---
merged_df = merged_df[merged_df['ix1'].notna() & (merged_df['ix1'] >= 0) & (merged_df['wse'] >= 0)]

# --- 高さ系変換（EGM2008→EGM96） ---
merged_df['wse'] = pd.to_numeric(merged_df['wse'], errors='coerce')
mask_h = merged_df['wse'].notna() & merged_df['lat_sword'].notna() & merged_df['lon_sword'].notna()
merged_df.loc[mask_h, 'wse'] = bulk_egm08_to_egm96(
    merged_df.loc[mask_h, 'lat_sword'],
    merged_df.loc[mask_h, 'lon_sword'],
    merged_df.loc[mask_h, 'wse']
)

# --- ここから「reachごと平均→偏差→セル平均でレベル整合→偏差復元」 ---
m = merged_df.copy()

# 1) reachごとの平均 μ_r
mu_r = m.groupby('reach_id', dropna=False)['wse'].mean()

# 2) 各レコードの偏差 δ = wse - μ_r
m['mu_r']  = m['reach_id'].map(mu_r)
m['delta'] = m['wse'] - m['mu_r']

# 3) (ix1, iy1, time_str) ごとの μ_r の平均（セル内レベル整合用）
mu_cell = m.groupby(['ix1', 'iy1', 'time_str'], dropna=False)['mu_r'].transform('mean')

# 4) 偏差を戻して整合済み WSE を再構成（wse_u は変更しない）
m['WSE'] = mu_cell + m['delta']

# ここまでで m['WSE'] は整合済みとして続行

keys = ['ix1', 'iy1', 'time_str']

# --- 集約ルール作成：WSE/slopeは平均、それ以外は代表値(first) ---
agg_rules = {c: 'first' for c in m.columns if c not in (keys + ['WSE', 'slope', 'slope_u'])}
agg_rules['WSE'] = 'mean'
agg_rules['slope'] = 'mean'
agg_rules['slope_u'] = 'mean'
# --- 同一セル×同一時刻の重複を1行に統合 ---
celltime = (
    m.groupby(keys, as_index=False)
     .agg(agg_rules)
)

# --- 各グリッド(ix1, iy1)の時間統計（WSE_mean, WSE_std） ---
grid_stats = (
    celltime.groupby(['ix1', 'iy1'], as_index=False)['WSE']
            .agg(WSE_mean='mean', WSE_std='std')  # 標本標準偏差(ddof=1)
)

# --- 統計量を付与（列追加） ---
celltime = celltime.merge(grid_stats, on=['ix1', 'iy1'], how='left')
celltime = celltime.rename(columns={'wse_u': 'uncertainty', 'ix1': 'ix', 'iy1': 'iy', 'time_str': 'day'})
# これで celltime は：
#  - 重複が解消された時系列（1セル×1時刻＝1行）
#  - 元の列は代表値を保持
#  - WSE はセル内平均に統合
#  - さらに WSE_mean, WSE_std 列を追加

# ---- グリッドごとに日次補間して WSE_mean_interp / WSE_std_interp を算出 ----
# 必須列: ['ix','iy','day','WSE']
celltime['day'] = pd.to_datetime(celltime['day'])

records = []
for (ix, iy), g in celltime.dropna(subset=['WSE']).groupby(['ix', 'iy']):
    s = g.set_index('day')['WSE'].sort_index()
    s = s[~s.index.duplicated()]  # 同一セル×同一日は既に1行だが念のため

    # 観測があった最初〜最後の日付で連続日次インデックスを作成
    full_idx = pd.date_range(s.index.min(), s.index.max(), freq='D')
    s_lin = s.reindex(full_idx).interpolate(method='time')  # 端点外はNaNのまま

    records.append({
        'ix': ix, 'iy': iy,
        'WSE_mean_interp': s_lin.mean(),
        'WSE_std_interp': s_lin.std(ddof=1),
    })

interp_df = pd.DataFrame(records, columns=['ix', 'iy', 'WSE_mean_interp', 'WSE_std_interp'])

# 元の celltime にマージ（left join）
celltime = celltime.merge(interp_df, on=['ix', 'iy'], how='left')

# --- 出力 ---
out_csv = RiverSP_celltime_file()
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
celltime = celltime.sort_values(['ix', 'iy', 'day'])
celltime.to_csv(out_csv, index=False)
print(f"Saved {len(celltime)} cell-time rows -> {out_csv}")
