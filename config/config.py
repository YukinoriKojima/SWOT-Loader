import os


def SWORD_raw_dir():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/netcdf"

def SWORD_csv_file():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/as_sword_v16.csv"

def SWORD_nc_file():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/netcdf/netcdf/as_sword_v16.nc"

def AllocRIverGauge_dir():
    return "/mnt/aqunia-dev/users/kojima/AllocRiverGauge"

def AllocGaugeInput_file():
    return "/mnt/aqunia-dev/users/kojima/AllocRiverGauge/output/gauge_alloc_mekong_sword.txt"

def Alloc_file():
    return "/mnt/aqunia-dev/users/kojima/CaMa-Flood_v4/map/Mekong_03min/src_param/gauge_alloc_sword_as_50.txt"

def Map_dir():
    return "/mnt/aqunia-dev/users/kojima/CaMa-Flood_v4/map/Mekong_03min"

def Allocated_csv_file():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/as_sword_v16_Mekong_allocated_50.csv"

def RiverSP_download_dir():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/RiverSP"

def RiverSP_shp_dir():
    # p01 が zip を解凍する先 (RiverSP_download_dir 配下の data_downloads)
    return os.path.join(RiverSP_download_dir(), "data_downloads")

def RiverSP_csv_file():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/RiverSP_Mekong_timeseries.csv"

def RiverSP_celltime_file():
    # CaMa-Flood セル(ix,iy)×日付ごとに統合した WSE の出力
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/RiverSP_Mekong_celltime.csv"

def RiverSP_bbox():
    # Mekong River basin: (西端経度, 南端緯度, 東端経度, 北端緯度)
    # 源流(チベット高原) 〜 デルタ(ベトナム) をカバー
    return (93.0, 8.0, 109.0, 34.0)

def Region():
    return 'AS'

# ---------------------------------------------------------------------------
# LakeSP (SWOT L2 HR LakeSP_Prior) — RiverSP と対になる湖沼/貯水池 WSE パイプライン
#   RiverSP: 河川 reach 上の WSE（SWORD reach_id で割当）
#   LakeSP : 湖/貯水池ポリゴン上の WSE（PLD lake_id、p_lon/p_lat で CaMa セルへ割当）
# ダム湛水面は RiverSP には出ず LakeSP_Prior 側にあるため、両者を併用して同化する。
# ---------------------------------------------------------------------------
def LakeSP_download_dir():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/LakeSP"

def LakeSP_shp_dir():
    # p01 が zip を解凍する先 (LakeSP_download_dir 配下の data_downloads)
    return os.path.join(LakeSP_download_dir(), "data_downloads")

def LakeSP_csv_file():
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/LakeSP_Mekong_timeseries.csv"

def LakeSP_celltime_file():
    # CaMa-Flood セル(ix,iy)×日付ごとに統合した 湖沼 WSE の出力
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/LakeSP_Mekong_celltime.csv"

def LakeSP_bbox():
    # RiverSP と同じ Mekong 流域 bbox: (西端経度, 南端緯度, 東端経度, 北端緯度)
    return RiverSP_bbox()

def Merged_celltime_file():
    # RiverSP + LakeSP を同化用に統合した celltime（1セル=1ソース, mean/std再計算済み）
    return "/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/RiverLake_Mekong_celltime_50.csv"