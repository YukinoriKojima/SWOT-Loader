import os

# The region is chosen by the environment variable SWORD_REGION (default "mekong", the original setting):
#   SWORD_REGION=sa_arb python p02_convert_nc_to_csv.py
# "mekong" : as_sword_v16, Mekong_03min, allocation by lat/lon only (as before)
# "sa_arb" : sa_sword_v16, ARB_06min, allocation with the reach's flow accumulation (facc) as the area,
#            and the RiverSP merge (p04)
REGIONS = {
    "mekong": dict(
        raw_dir="/work/a06/ykojima/SWORD-Loader/data/netcdf",
        csv_file="/work/a06/ykojima/SWORD-Loader/data/csv/as_sword_v16.csv",
        nc_file="/work/a06/ykojima/SWORD-Loader/data/netcdf/netcdf/as_sword_v16.nc",
        alloc_file="/work/a06/ykojima/SWORD-Loader/data/alloc_txt/alloc_sword_Mekong.txt",
        map_dir="/work/a06/ykojima/CaMa-Flood_v4/map/Mekong_03min",
        alloc_mode="latlon",
        allocated_csv_file="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/as_sword_v16_Mekong_allocated_50.csv",
        riversp_download_dir="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/RiverSP",
        riversp_csv_file="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/RiverSP_Mekong_timeseries.csv",
        riversp_celltime_file="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/RiverSP_Mekong_celltime.csv",
        riversp_bbox=(93.0, 8.0, 109.0, 34.0),
        region_code="AS",
        lakesp_download_dir="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/LakeSP",
        lakesp_csv_file="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/LakeSP_Mekong_timeseries.csv",
        lakesp_celltime_file="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/LakeSP_Mekong_celltime.csv",
        merged_celltime_file="/mnt/aqunia-dev/users/kojima/SWORD-Loader/data/csv/RiverLake_Mekong_celltime_50.csv",
    ),
    "sa_arb": dict(
        raw_dir="/work/a06/ykojima/SWORD/data/netcdf_v16",
        csv_file="/work/a06/ykojima/SWORD-Loader/data/csv/sa_sword_v16_facc.csv",
        nc_file="/work/a06/ykojima/SWORD/data/netcdf_v16/netcdf/sa_sword_v16.nc",
        alloc_file="/work/a06/ykojima/SWORD-Loader/data/alloc_txt/alloc_sword_sa_ARB_06min_facc.txt",
        map_dir="/work/a06/ykojima/cmf_v420/map/ARB_06min",
        alloc_mode="area",
        riversp_dir="/work/a06/ykojima/RivSP_SA",
        riversp_out="/work/a06/ykojima/SWORD-Loader/data/swot/SWOT_HR_daily_ARB_06min_facc.csv",
    ),
    "yukon": dict(
        raw_dir="/work/a06/ykojima/SWORD-Loader/data/netcdf",
        csv_file="/work/a06/ykojima/SWORD-Loader/data/csv/na_sword_v16_facc.csv",
        nc_file="/work/a06/ykojima/SWORD-Loader/data/netcdf/netcdf/na_sword_v16.nc",
        alloc_file="/work/a06/ykojima/SWORD-Loader/data/alloc_txt/alloc_sword_na_Yukon_06min_facc.txt",
        map_dir="/work/a06/ykojima/cmf_v420/map/Yukon_06min",
        alloc_mode="area",
        riversp_dir="/work/a06/ykojima/RiverSP/data/AR/shapefile",
        riversp_out="/work/a06/ykojima/SWORD-Loader/data/swot/SWOT_HR_daily_Yukon_06min_facc.csv",
    ),
}
REGION = os.environ.get("SWORD_REGION", "mekong")
_C = REGIONS[REGION]


def SWORD_raw_dir():
    return _C["raw_dir"]

def SWORD_csv_file():
    return _C["csv_file"]

def SWORD_nc_file():
    return _C["nc_file"]

def AllocRIverGauge_dir():
    return "/work/a06/ykojima/AllocRiverGauge"

def AllocGaugeInput_file():
    return "/mnt/aqunia-dev/users/kojima/AllocRiverGauge/output/gauge_alloc_mekong_sword.txt"

def Alloc_file():
    return _C["alloc_file"]

def Map_dir():
    return _C["map_dir"]

def Alloc_mode():
    """"latlon": alloc_gauge_latlon_only (nearest pixel with uparea >= 1000 km2);
    "area": alloc_gauge_latlon_area (pixel minimising the uparea + location error against facc)"""
    return _C["alloc_mode"]

def RiverSP_dir():
    return _C["riversp_dir"]

def RiverSP_out_file():
    return _C["riversp_out"]

def Allocated_csv_file():
    return _C["allocated_csv_file"]

def RiverSP_download_dir():
    return _C["riversp_download_dir"]

def RiverSP_shp_dir():
    return os.path.join(RiverSP_download_dir(), "data_downloads")

def RiverSP_csv_file():
    return _C["riversp_csv_file"]

def RiverSP_celltime_file():
    return _C["riversp_celltime_file"]

def RiverSP_bbox():
    return _C["riversp_bbox"]

def Region():
    return _C["region_code"]

# ---------------------------------------------------------------------------
# LakeSP (SWOT L2 HR LakeSP_Prior) — RiverSP と対になる湖沼/貯水池 WSE パイプライン
#   RiverSP: 河川 reach 上の WSE（SWORD reach_id で割当）
#   LakeSP : 湖/貯水池ポリゴン上の WSE（PLD lake_id、p_lon/p_lat で CaMa セルへ割当）
# ダム湛水面は RiverSP には出ず LakeSP_Prior 側にあるため、両者を併用して同化する。
# ---------------------------------------------------------------------------
def LakeSP_download_dir():
    return _C["lakesp_download_dir"]

def LakeSP_shp_dir():
    return os.path.join(LakeSP_download_dir(), "data_downloads")

def LakeSP_csv_file():
    return _C["lakesp_csv_file"]

def LakeSP_celltime_file():
    return _C["lakesp_celltime_file"]

def LakeSP_bbox():
    return RiverSP_bbox()

def Merged_celltime_file():
    return _C["merged_celltime_file"]
