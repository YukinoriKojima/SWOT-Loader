"""RiverSP + LakeSP を同化用に統合（観測を最大限使う正規化マージ）。

方針（ユーザ指定）:
  ① 各ソース(river/lake)を「セル内 z-スコア」に正規化   z = (WSE - μ_{s,c}) / σ_{s,c}
     → 河川面と湖面の絶対レベル・変動スケールの違いを除去して同じ土俵に載せる
  ② セルごとに統一 (μ_c, σ_c) を決める（= 観測数最多ソース=アンカーの μ,σ）
  ③ WSE に戻す   WSE' = z * σ_c + μ_c

なぜこれで良いか（NOR整合）:
  DA(NOR)は obs を (WSE - WSE_mean)/WSE_std に正規化する。WSE_mean=μ_c, WSE_std=σ_c と
  置けば DA が復元するのは z そのもの。よって μ_c/σ_c の選び方は同化結果に不変で、
  物理単位を保つためアンカーの μ,σ を採用する。単一ソースのセルは恒等変換=元のWSE。

要点:
  - 1セルに river/lake 両方あっても「混ぜた生WSEで mean/std を作らない」。必ず z 化してから統一。
  - σ_c=0 / n<2 のソースは z 化できない → そのソースは除外（件数を報告）。
  - 同一 (ix,iy,day) に両ソースがある場合は z を平均して1行に統合。
  - uncertainty はアンカースケールへ換算（unc' = unc * σ_c/σ_s）。
"""
import sys
sys.path.append('.././config')

import os
import numpy as np
import pandas as pd

from config import RiverSP_celltime_file, LakeSP_celltime_file, Merged_celltime_file

KEEP = ['ix', 'iy', 'day', 'WSE', 'uncertainty', 'lon_sword', 'lat_sword']


def load(path, source, id_col):
    df = pd.read_csv(path)
    df = df[KEEP + [id_col]].rename(columns={id_col: 'src_id'})
    df['source'] = source
    df['day'] = pd.to_datetime(df['day'])
    df['WSE'] = pd.to_numeric(df['WSE'], errors='coerce')
    df = df.dropna(subset=['WSE'])
    return df


riv = load(RiverSP_celltime_file(), 'river', 'reach_id')
lak = load(LakeSP_celltime_file(), 'lake', 'lake_id')
df = pd.concat([riv, lak], ignore_index=True)
print(f"loaded river={len(riv)} lake={len(lak)} total={len(df)} rows")

# ---- ① ソース×セルの μ,σ と z 化 ----
gcs = df.groupby(['ix', 'iy', 'source'])['WSE']
df['mu_s'] = gcs.transform('mean')
df['sd_s'] = gcs.transform('std')          # 標本標準偏差 ddof=1
df['n_s'] = gcs.transform('size')

valid = (df['n_s'] >= 2) & (df['sd_s'] > 0) & np.isfinite(df['sd_s'])
n_drop = int((~valid).sum())
print(f"z化できない行(n<2 or σ=0): {n_drop}  ({df.loc[~valid, ['ix','iy','source']].drop_duplicates().shape[0]} source-cells) -> 除外")
df = df[valid].copy()
df['z'] = (df['WSE'] - df['mu_s']) / df['sd_s']

# ---- ② セルごとの統一 (μ_c, σ_c) = 観測数最多ソース(アンカー)の μ,σ ----
# 各 (ix,iy,source) の代表統計
src_stat = (df.groupby(['ix', 'iy', 'source'], as_index=False)
              .agg(mu_s=('mu_s', 'first'), sd_s=('sd_s', 'first'), n_s=('n_s', 'first')))
# セルごとに n_s 最大のソースを選ぶ（同数なら lake を優先: 貯水池水面を基準に）
src_stat['pref'] = np.where(src_stat['source'] == 'lake', 1, 0)
src_stat = src_stat.sort_values(['ix', 'iy', 'n_s', 'pref'], ascending=[True, True, False, False])
anchor = src_stat.drop_duplicates(['ix', 'iy'], keep='first')[['ix', 'iy', 'mu_s', 'sd_s', 'source']]
anchor = anchor.rename(columns={'mu_s': 'mu_c', 'sd_s': 'sd_c', 'source': 'anchor_src'})
df = df.merge(anchor, on=['ix', 'iy'], how='left')

# ---- ③ WSE に戻す（アンカースケール） ----
df['WSE_new'] = df['z'] * df['sd_c'] + df['mu_c']
df['unc_new'] = pd.to_numeric(df['uncertainty'], errors='coerce') * (df['sd_c'] / df['sd_s'])

# ---- 同一 (ix,iy,day) を z 平均で1行に統合 ----
def join_src(s):
    u = sorted(set(s))
    return '+'.join(u)

agg = (df.groupby(['ix', 'iy', 'day'], as_index=False)
         .agg(z=('z', 'mean'),
              mu_c=('mu_c', 'first'), sd_c=('sd_c', 'first'),
              unc_new=('unc_new', 'mean'),
              lon_sword=('lon_sword', 'first'), lat_sword=('lat_sword', 'first'),
              anchor_src=('anchor_src', 'first'),
              source=('source', join_src),
              src_id=('src_id', 'first')))
agg['WSE'] = agg['z'] * agg['sd_c'] + agg['mu_c']

# ---- DA が読む列: WSE, uncertainty, WSE_mean(=μ_c), WSE_std(=σ_c) ----
out = agg.rename(columns={'unc_new': 'uncertainty', 'mu_c': 'WSE_mean', 'sd_c': 'WSE_std'})
out = out[['ix', 'iy', 'day', 'source', 'anchor_src', 'src_id',
           'WSE', 'uncertainty', 'WSE_mean', 'WSE_std', 'lon_sword', 'lat_sword']]
out = out.sort_values(['ix', 'iy', 'day'])

out_csv = Merged_celltime_file()
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
out.to_csv(out_csv, index=False)

# ---- サマリ ----
ncell = out[['ix', 'iy']].drop_duplicates().shape[0]
both = out[out['source'].str.contains(r'\+')][['ix', 'iy']].drop_duplicates().shape[0]
print(f"Saved {len(out)} rows / {ncell} cells -> {out_csv}")
print(f"  anchor=lake cells: {anchor[anchor.anchor_src=='lake'].shape[0]}, anchor=river cells: {anchor[anchor.anchor_src=='river'].shape[0]}")
print(f"  cell-days with BOTH sources fused: {int(out['source'].str.contains(r'\+', regex=True).sum())}  (in {both} cells)")
