# merge パイプライン（RiverSP + LakeSP 統合）

RiverSP と LakeSP の celltime を、データ同化（DA）で観測を最大限使えるよう 1 本に
統合する。最終成果物 `data/csv/RiverLake_Mekong_celltime_50.csv` を DA が読む。

## 実行手順（`src/merge/` 内で）

```bash
cd src/merge
python p04_merge_river_lake.py
```

入力: `RiverSP_Mekong_celltime.csv`, `LakeSP_Mekong_celltime.csv`
出力: `RiverLake_Mekong_celltime_50.csv`

## 処理設計・工夫（z-スコア正規化マージ）

河川面と湖面は**絶対レベルも変動スケールも違う**。生 WSE を混ぜて mean/std を作ると
物理的に無意味になるため、以下の手順で統合する。

1. **z 化**: 各ソース(river/lake)をセル内 z-スコアに正規化
   `z = (WSE - μ_{s,c}) / σ_{s,c}`。レベル・スケール差を除去して同じ土俵に載せる。
2. **アンカー選択**: セルごとに統一 (μ_c, σ_c) を、**観測数最多ソース（アンカー）**の μ,σ に
   決める。同数なら lake 優先（貯水池水面を基準に）。
3. **WSE へ復元**: `WSE' = z·σ_c + μ_c`。単一ソースのセルは恒等変換（=元の WSE）。

### なぜこれで良いか（NOR 整合）
DA(NOR) は obs を `(WSE - WSE_mean)/WSE_std` に正規化する。`WSE_mean=μ_c, WSE_std=σ_c` と
置けば DA が復元するのは z そのもの。よって **μ_c/σ_c の選び方は同化結果に不変**で、
物理単位を保つためアンカーの μ,σ を採用している。

### その他の要点
- σ_c=0 / n<2 のソースは z 化できない → そのソースは除外（件数を報告）。
- 同一 (ix,iy,day) に両ソースがある場合は **z を平均して 1 行に統合**。
- uncertainty はアンカースケールへ換算（`unc' = unc·σ_c/σ_s`）。

## 出力列（追加分）
共通 celltime 列（ix,iy,day,WSE,uncertainty,WSE_mean,WSE_std,lon/lat_sword）に加え:

| 列 | 意味 |
|---|---|
| `source` | 統合元（`river` / `lake` / `river+lake`）|
| `anchor_src` | そのセルの μ,σ を決めたアンカーソース |
| `src_id` | 代表 reach_id / lake_id |

## 依存

pandas, numpy のみ（earthaccess/geopandas/pyproj 不要）。
