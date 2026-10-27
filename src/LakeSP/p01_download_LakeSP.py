import sys
sys.path.append('../../config')

import os
import zipfile
from config import LakeSP_download_dir, Region, LakeSP_bbox

import earthaccess
from tqdm import tqdm

earthaccess.login()  # Login with your EDL credentials if asked

# Enter continent code
continent_code = Region()    # e.g. "AF", "NA", "EU", "SI", "AS", "AU", "SA", "AR", "GR"
bbox = LakeSP_bbox()         # (西端経度, 南端緯度, 東端経度, 北端緯度)

# Retrieves granules and links list from the passes we want, filtered by
# collection shortname, temporal bounds, granule name, and spatial bounding box.
#
# LakeSP は 1 パスにつき Prior / Obs / Unassigned の 3 種が出る。
#   Prior      = PLD(Prior Lake Database)の湖に紐づく WSE（lake_id, p_lon/p_lat を持つ）★これを使う
#   Obs        = 観測された水域(prior未割当を含む)  / Unassigned = 対応湖なし
# ダム貯水池は PLD 湖として Prior に入るため granule_name で Prior のみに絞る。
#
# NOTE: RiverSP と同様、再処理版 "2.0" は 2025-05-02 で granule が途切れる。以降は
# 現行処理版 "D"(SWOT_L2_HR_LakeSP_D) に存在するため、継ぎ目を 2025-05-02/03 に
# 置いて版の重複(同期間の二重観測)を避けつつ両版を結合する。
_gname = "*LakeSP_Prior*_" + continent_code + "*"
_specs = [
    ('SWOT_L2_HR_LakeSP_2.0',    ('2000-01-25 00:00:00', '2025-05-02 23:59:59')),
    ('SWOT_L2_HR_LakeSP_D',      ('2025-05-03 00:00:00', '2099-05-16 23:59:59')),
]
lake_results = []
for _sn, _temporal in _specs:
    _r = earthaccess.search_data(short_name = _sn,
                                 temporal = _temporal,
                                 granule_name = _gname,
                                 bounding_box = bbox)
    print(f"search {_sn} {_temporal}: {len(_r)} granules")
    lake_results += list(_r)

download_dir = LakeSP_download_dir()
os.makedirs(download_dir, exist_ok=True)

# Collect one external link per granule
links_list = []
for r in tqdm(range(len(lake_results)), desc="collecting links"):
    lake_link = earthaccess.results.DataGranule.data_links(lake_results[r], access='external')[0]
    links_list.append(lake_link)

# Download all granules at once
earthaccess.download(links_list, download_dir)

# Unzip downloaded archives
extract_dir = os.path.join(download_dir, "data_downloads")
os.makedirs(extract_dir, exist_ok=True)
for link in links_list:
    filename = link.split("/")[-1]
    zip_path = os.path.join(download_dir, filename)
    if filename.endswith(".zip") and os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
