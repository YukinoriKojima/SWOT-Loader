# LakeSP パイプライン（RiverSP と対）

SWOT **L2 HR LakeSP_Prior**（PLD 湖/貯水池ポリゴン上の WSE）を取得し、CaMa-Flood
セル(ix,iy)×日付の WSE 観測 CSV に変換する。ダム湛水面は RiverSP(河川 reach)には
出ず LakeSP_Prior 側にあるため、RiverSP と併用して同化するのが狙い。

`src/RiverSP/` と同じ 3 段構成・同じ出力スキーマ（celltime）に揃えてある。

## 認証（earthaccess / NASA Earthdata）

p01 は `earthaccess.login()`（引数なし）でログインし、認証情報を `~/.netrc` から自動で
読む。詳細はリポジトリ直下 `README.md` の「earthaccess 認証」節を参照。

## 実行手順（`src/LakeSP/` 内で順に）

```bash
cd src/LakeSP
python p01_download_LakeSP.py    # earthaccess で LakeSP_Prior を DL・解凍
python p02_LakeSP_to_csv.py      # shp -> lake×time の timeseries CSV（品質フィルタ）
python p03_merge_LakeSP_alloc.py # PLD座標でセル割当 + EGM変換 + celltime 統合
```

出力:
- `data/csv/LakeSP_Mekong_timeseries.csv` … lake_id×日付の生 WSE
- `data/csv/LakeSP_Mekong_celltime.csv`  … ix,iy×日付に統合（DA の WSEobsfile 形式）

## RiverSP との対応

| 項目 | RiverSP | LakeSP |
|---|---|---|
| コレクション | `SWOT_L2_HR_RIVERSP_2.0` + `_reach_D` | `SWOT_L2_HR_LakeSP_2.0` + `_D`（Prior のみ）|
| 版の継ぎ目 | 2025-05-02/03 | 同左 |
| 主キー | reach_id | lake_id |
| セル割当 | SWORD reach→ix,iy（事前割当CSV, 河道スナップ済み）| PLD 中心 `p_lon/p_lat` を直接ビニング |
| 高さ変換 | EGM2008→EGM96 | 同左 |
| 出力 | `RiverSP_Mekong_celltime.csv` | `LakeSP_Mekong_celltime.csv` |

## 注意点 / TODO

- **割当は素のビニング**：PLD 中心座標→セルのため、河道スナップ済みのゲージ割当と
  1 セルずれ得る（検証で ID9 が (341,424) vs 期待 (340,425)）。ダムセルへ寄せたい場合は
  `dam_alloc_river.txt` の (ix,iy) へスナップする後処理を p03 に足す。
- **品質フィルタ** `quality_f<=1 & partial_f==0`：LakeSP の要約フラグに基づく暫定値。
  有効観測での `quality_f` 実値を見て必要なら調整。
- DA に渡すときは RiverSP celltime と **マージ**（両プロダクト併用）するか、
  貯水池セルのみ LakeSP を優先する等の統合方針を別途決める。
- 全期間 DL は Prior だけで v2.0=403 + D=753 本（各~11MB, 合計~12GB）。
