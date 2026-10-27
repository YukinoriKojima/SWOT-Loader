# SWORD パイプライン（ゲージ割当表の作成）

SWORD（SWOT River Database）v16 から河川 reach の位置を取り出し、CaMa-Flood 河道へ
ゲージ割当して **reach_id ↔ セル(ix1,iy1)** の対応表を作る。RiverSP のセル割当
（`src/RiverSP/p03`）がこの表を参照する。

## 実行手順（`src/SWORD/` 内で順に）

```bash
cd src/SWORD
python p01_download_SWORD.py       # SWORD v16 netCDF を Zenodo から DL・解凍
python p02_convert_nc_to_csv.py    # reach の (lat,lon,reach_id) を CSV 化
python p03_allocation.py           # CaMa の allocate_level_gauge で河道へゲージ割当
python p04_merge.py                # 割当結果に元 reach 属性を付与
```

出力: `data/csv/as_sword_v16_Mekong_allocated_50.csv`（reach_id ↔ ix1,iy1 の対応表）

## 処理設計・工夫

### p01 — ダウンロード
- Zenodo の `SWORD_v16_netcdf.zip`（record 10013982）を wget→unzip。認証不要。
- 領域コレクションは Region（`AS`）に対応する `as_sword_v16.nc` を使う。

### p02 — nc → CSV
- netCDF の `reaches` グループから `x`(lon), `y`(lat), `reach_id` のみを取り出す。
- **行番号を `label_from_zero` として明示保存**する（`index_label='label_from_zero'`）。
  これが p03 のゲージ割当入力での ID と p04 のマージキーになる。

### p03 — ゲージ割当（CaMa-Flood 実行ファイルを呼ぶ）
- **入力ゲージリストは外部から持ち込む前提**（`config.AllocGaugeInput_file`、
  例: `AllocRiverGauge/output/gauge_alloc_mekong_sword.txt`）。
  高解像度河川網上で割当済みのゲージリストを想定。
- `Map_dir/src_param` に `cwd` を移して CaMa の実行ファイル `./allocate_level_gauge <input>`
  を呼び、出力 `gauge_alloc.txt` を `config.Alloc_file`（`src_param/gauge_alloc_sword_as_50.txt`）へ
  `shutil.move` する。
- **前提**: `allocate_level_gauge` が `src_param` にビルド済みであること。CaMa-Flood 側の
  セットアップに依存する。

### p04 — 属性マージ
- 割当結果（`Alloc_file`, 空白区切り）の先頭列 `ID` を、p02 の `label_from_zero` と結合し、
  元 reach 属性（reach_id 等）を付与する。
- lat/lon が両テーブルにあるため、**元 SWORD 側は `_sword` サフィックス**で残す
  （割当済み座標を優先、元座標は `lat_sword`/`lon_sword`）。RiverSP p03 はこの
  `lat_sword`/`lon_sword` を EGM 変換の座標として使う。

## 依存

`requirements.txt`（netCDF4, numpy, pandas, requests）のみで動く。RiverSP/LakeSP と違い
earthaccess / geopandas / pyproj は不要。ただし p03 は CaMa-Flood の
`allocate_level_gauge` に依存する。
