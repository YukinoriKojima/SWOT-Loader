# SWORD-Loader

CaMa-Flood データ同化（DA）向けに、衛星由来の**水面標高（WSE, Water Surface Elevation）**
観測を「CaMa-Flood セル(ix,iy)×日付」形式の CSV に整形するローダ群。

3 系統の入力を扱う:

- **SWORD** — 河川 reach の位置データベース（SWOT River Database）。ゲージ割当の下敷き。
- **RiverSP** — SWOT L2 HR RiverSP（河川 reach 上の WSE 時系列）。
- **LakeSP** — SWOT L2 HR LakeSP_Prior（湖/貯水池ポリゴン上の WSE 時系列）。

ダム湛水面は RiverSP（河川 reach）には出ず LakeSP_Prior 側にあるため、両者を併用して
同化する。最終的に RiverSP と LakeSP を 1 本の同化用 CSV に統合する。

対象領域は現状 **Mekong 流域**（`config.py` の bbox / Map_dir で切替）。

---

## ディレクトリ構成

```
SWORD-Loader/
├── config/
│   └── config.py              # 全パス・領域(bbox)・Region を一元管理する関数群
├── src/
│   ├── SWORD/                 # SWORD DB → ゲージ割当CSV (RiverSP のセル割当に使う)
│   │   ├── p01_download_SWORD.py
│   │   ├── p02_convert_nc_to_csv.py
│   │   ├── p03_allocation.py
│   │   └── p04_merge.py
│   ├── RiverSP/               # SWOT RiverSP → celltime WSE CSV
│   │   ├── p01_download_RiverSP.py
│   │   ├── p02_RiverSP_to_csv.py
│   │   └── p03_merge_RiverSP_alloc.py
│   ├── LakeSP/                # SWOT LakeSP_Prior → celltime WSE CSV（README あり）
│   │   ├── p01_download_LakeSP.py
│   │   ├── p02_LakeSP_to_csv.py
│   │   └── p03_merge_LakeSP_alloc.py
│   └── merge/
│       └── p04_merge_river_lake.py   # RiverSP + LakeSP を同化用に正規化統合
├── data/                      # DL/生成物（.gitignore、コミット対象外）
│   ├── netcdf/  csv/  RiverSP/  LakeSP/
├── requirements.txt
└── .venv_sword/               # Python 仮想環境（.gitignore）
```

すべての入出力パスは `config/config.py` に集約されている。パスや領域を変えるときは
スクリプト本体ではなく **config.py だけ** を編集する。各スクリプトは
`sys.path.append('../config')`（LakeSP/RiverSP は `'../../config'`）で config を読む。

---

## データフロー

```
                    ┌─────────────────────────────────────────────┐
  SWORD DB (Zenodo) │ SWORD/p01→p02→p03→p04                        │
        │           │  nc → 全reach(lat,lon,reach_id)のCSV          │
        ▼           │  → CaMa河道へゲージ割当 → reach属性を付与      │
  as_sword_v16.csv  │  → Allocated_csv (reach_id, ix1, iy1, ...)   │
                    └───────────────────────┬─────────────────────┘
                                            │ reach_id→(ix,iy) 割当表
                                            ▼
  SWOT RiverSP ──► RiverSP/p01→p02→p03 ──► RiverSP_Mekong_celltime.csv
  (earthaccess)     DL → 品質フィルタ→timeseries → EGM変換+セル統合   │
                                                                    │
  SWOT LakeSP  ──► LakeSP/p01→p02→p03 ──► LakeSP_Mekong_celltime.csv │
  (earthaccess)     DL → 品質フィルタ→timeseries → 座標ビニング+統合  │
                                                                    │
                              merge/p04 ◄───────────────────────────┘
                                  │  z-スコア正規化で river/lake を統合
                                  ▼
                       RiverLake_Mekong_celltime_50.csv  ← DA が読む最終成果物
```

---

## セットアップ

```bash
python -m venv .venv_sword
source .venv_sword/bin/activate
pip install -r requirements.txt
```

`requirements.txt` は SWORD 系（netCDF4, numpy, pandas, requests）のみ。
RiverSP/LakeSP は追加で以下が必要:

- `earthaccess` — NASA Earthdata からの DL（後述の認証が必要）
- `geopandas` — shapefile 読み込み
- `pyproj` + PROJ ジオイドグリッド — EGM2008→EGM96 変換
- `tqdm` — 進捗表示

### earthaccess 認証（RiverSP/LakeSP p01 で必須）

RiverSP/LakeSP の p01 は NASA Earthdata（SWOT データ配信元）へのログインが必要。
コードは引数なしの `earthaccess.login()` を呼ぶだけで、**認証情報は `~/.netrc` から
自動で読まれる**。`.netrc` に以下があれば対話プロンプトは出ない:

```
machine urs.earthdata.nasa.gov
login <Earthdata ユーザ名>
password <パスワード>
```

`.netrc` が無い/別マシンで動かす場合は、対話で 1 回だけログインして保存する:

```python
import earthaccess
earthaccess.login(strategy="interactive", persist=True)  # 入力を ~/.netrc に保存
```

CI 等プロンプト不可の環境では環境変数でも渡せる（`earthaccess.login(strategy="environment")`）:

```bash
export EARTHDATA_USERNAME=<ユーザ名>
export EARTHDATA_PASSWORD=<パスワード>
```

Earthdata アカウント自体は https://urs.earthdata.nasa.gov で取得しておくこと。

### PROJ ジオイドグリッド（RiverSP/LakeSP p03 で必須）

WSE の高さ系変換（EGM2008→EGM96）に PROJ のジオイドグリッドをローカル配置しておく。
未配置だと PROJ が黙って `inf` を返すため、p03 は検知して即エラー終了する。

```bash
curl https://cdn.proj.org/us_nga_egm08_25.tif -o ~/.local/share/proj/us_nga_egm08_25.tif
curl https://cdn.proj.org/us_nga_egm96_15.tif -o ~/.local/share/proj/us_nga_egm96_15.tif
```

---

## 実行手順

各スクリプトはそのディレクトリ内で番号順に実行する（config を相対パスで読むため）。

### 1. SWORD（RiverSP のセル割当表を作る）

```bash
cd src/SWORD
python p01_download_SWORD.py       # SWORD v16 netCDF を Zenodo から DL・解凍
python p02_convert_nc_to_csv.py    # reach の (lat,lon,reach_id) を CSV 化
python p03_allocation.py           # CaMa の allocate_level_gauge で河道へゲージ割当
python p04_merge.py                # 割当結果に元 reach 属性を付与 → Allocated_csv
```

- **p03 は CaMa-Flood 側の実行ファイル** `allocate_level_gauge` を `Map_dir/src_param` で呼ぶ。
  入力ゲージリスト（`AllocGaugeInput_file`）は外部（AllocRiverGauge）から持ち込む前提。
- 出力: `data/csv/as_sword_v16_Mekong_allocated_50.csv`（reach_id ↔ ix1,iy1 の対応表）。

### 2. RiverSP

```bash
cd src/RiverSP
python p01_download_RiverSP.py     # earthaccess で RiverSP reach shp を DL・解凍
python p02_RiverSP_to_csv.py       # shp → reach×日付の timeseries（品質フィルタ）
python p03_merge_RiverSP_alloc.py  # SWORD割当でセル付与 + EGM変換 + celltime 統合
```

出力: `data/csv/RiverSP_Mekong_celltime.csv`

### 3. LakeSP

```bash
cd src/LakeSP
python p01_download_LakeSP.py      # earthaccess で LakeSP_Prior shp を DL・解凍
python p02_LakeSP_to_csv.py        # shp → lake×日付の timeseries（品質フィルタ）
python p03_merge_LakeSP_alloc.py   # PLD座標でセルビニング + EGM変換 + celltime 統合
```

出力: `data/csv/LakeSP_Mekong_celltime.csv`
（詳細は `src/LakeSP/README.md`）

### 4. 統合（DA 入力を作る）

```bash
cd src/merge
python p04_merge_river_lake.py     # RiverSP + LakeSP を z-スコア正規化して統合
```

出力: `data/csv/RiverLake_Mekong_celltime_50.csv`

---

## 各パイプラインの処理設計

各スクリプトの実装上の工夫（版の継ぎ目、OOM 対策、品質フィルタ、レベル整合、
z-スコア統合など）は、それぞれのディレクトリ内ドキュメントにまとめてある:

- [`src/SWORD/README.md`](src/SWORD/README.md) — SWORD DB → ゲージ割当表
- [`src/RiverSP/README.md`](src/RiverSP/README.md) — RiverSP → celltime
- [`src/LakeSP/README.md`](src/LakeSP/README.md) — LakeSP → celltime
- [`src/merge/README.md`](src/merge/README.md) — RiverSP + LakeSP 統合

---

## 出力スキーマ（celltime）

DA が読む最終形。RiverSP/LakeSP/merge で共通に揃えてある主な列:

| 列 | 意味 |
|---|---|
| `ix`, `iy` | CaMa-Flood セル座標（1始まり） |
| `day` | 観測日（12時以降は翌日へ丸め） |
| `WSE` | セル×日付に統合した水面標高（EGM96, m） |
| `uncertainty` | WSE の不確かさ |
| `WSE_mean`, `WSE_std` | セルの時間平均/標準偏差（DA の正規化基準 μ_c, σ_c） |
| `lon_sword`, `lat_sword` | 割当に使った座標 |

merge 出力にはソース識別列 `source`（`river`/`lake`/`river+lake`）と `anchor_src` が付く。

---

## 注意点

- `data/` は `.gitignore` 対象。全期間 DL は LakeSP Prior だけで v2.0=403 + D=753 本
  （各~11MB, 合計~12GB）と大きい。
- LakeSP のセル割当は PLD 中心座標の素のビニングで、河道スナップ済みのゲージ割当と
  1 セルずれ得る（`src/LakeSP/README.md` の TODO 参照）。
- 領域・解像度は `config.py` の `RiverSP_bbox()` / `Region()` / `Map_dir()` で切替。
