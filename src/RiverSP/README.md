# RiverSP パイプライン

SWOT **L2 HR RiverSP**（河川 reach 上の WSE 時系列）を取得し、CaMa-Flood
セル(ix,iy)×日付の WSE 観測 CSV（celltime）に変換する。セル割当には SWORD 由来の
ゲージ割当表（`src/SWORD` の出力）を使う。`src/LakeSP` と同じ 3 段構成・同じ
celltime スキーマに揃えてある。

## 実行手順（`src/RiverSP/` 内で順に）

```bash
cd src/RiverSP
python p01_download_RiverSP.py     # earthaccess で RiverSP reach shp を DL・解凍
python p02_RiverSP_to_csv.py       # shp → reach×日付の timeseries（品質フィルタ）
python p03_merge_RiverSP_alloc.py  # SWORD割当でセル付与 + EGM変換 + celltime 統合
```

出力:
- `data/csv/RiverSP_Mekong_timeseries.csv` … reach_id×日付の生 WSE
- `data/csv/RiverSP_Mekong_celltime.csv` … ix,iy×日付に統合（DA の WSEobsfile 形式）

## 認証（earthaccess / NASA Earthdata）

p01 は `earthaccess.login()`（引数なし）で NASA Earthdata にログインする。認証情報は
`~/.netrc` から自動で読まれる。詳細はリポジトリ直下 `README.md` の「earthaccess 認証」節を参照。

## 処理設計・工夫

### p01 — ダウンロード（版の継ぎ目）
- 再処理版 `SWOT_L2_HR_RIVERSP_2.0` は **2025-05-02** で granule が途切れる。以降は現行
  処理版 `SWOT_L2_HR_RiverSP_reach_D` に存在するため、継ぎ目を **2025-05-02/03** に置いて
  2 版を結合し、同期間の二重観測を避ける。
- `granule_name="*Reach*_AS*"`（Region）と `bounding_box`（`config.RiverSP_bbox`）で絞る。
- granule ごとに external link を 1 本集め、一括 DL → zip を `data_downloads/` へ解凍。

### p02 — shp → timeseries（メモリ対策 + 品質フィルタ）
- **OOM 対策**: 処理版 D の Reach shapefile は ~130 列あり、全ファイルを生 concat すると
  メモリ枯渇で OOM kill される（実際に発生）。1 ファイルずつ `NEEDED` 列だけ残し、
  geometry を捨て、品質フィルタ後に結合してメモリを大幅削減。
- **品質フィルタ**: `reach_q<=1`（0=Good/1=Suspect のみ）& `partial_f==0`（部分観測除外）
  & wse 欠損/番兵値(-1e12)除去。
- **日付丸め**: `time_str` を UTC 日付へ丸め、**12 時以降は翌日 00:00** に寄せる。
- reach ごとの `wse_mean`/`wse_std`（時間統計）を列付与して出力。

### p03 — セル割当 + 高さ変換 + celltime 統合
- **セル割当**: SWORD 割当表（`config.Allocated_csv_file`）を reach_id で結合し、
  `ix1,iy1` と割当座標 `lat_sword`/`lon_sword` を付与。`ix1>=0` & `wse>=0` で絞る。
- **高さ系変換 EGM2008→EGM96**: `bulk_egm08_to_egm96()` が pyproj で複合CRS
  （EPSG:9518→9707）変換。**PROJ ジオイドグリッドはローカル必須**（`network=True` だと
  取得失敗時に黙って `inf` を返すため無効化）。非有限値が出たら silent に下流へ流さず
  即 `RuntimeError`。グリッド配置は直下 README のセットアップ参照。
- **レベル整合**: 同一セルに複数 reach があるとき、生 WSE を混ぜて mean/std を作らない。
  「reach ごと平均 μ_r → 各点の偏差 δ=wse-μ_r → (ix,iy,time)ごとの μ_r 平均 → δ を戻して
  整合済み WSE 再構成」。絶対レベル差を吸収してからセル統合する。
- **集約**: `(ix1,iy1,time_str)` ごとに WSE/slope は平均、それ以外は代表値(first)で 1 行化。
- **時間統計 + 日次補間**: セルの `WSE_mean`/`WSE_std` に加え、観測初〜終日で日次線形補間
  した `WSE_mean_interp`/`WSE_std_interp` も付与。

## 依存

earthaccess, geopandas, pyproj（+ PROJ ジオイドグリッド）, tqdm, pandas, numpy。
セットアップは直下 `README.md` 参照。
