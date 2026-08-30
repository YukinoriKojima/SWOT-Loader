import sys
sys.path.append('../../config')

import os
import zipfile
from config import RiverSP_download_dir, Region, RiverSP_bbox

import earthaccess
from tqdm import tqdm

earthaccess.login() # Login with your EDL credentials if asked

# Enter continent code
continent_code = Region()    # e.g. "AF", "NA", "EU", "SI", "AS", "AU", "SA", "AR", "GR"
bbox = RiverSP_bbox()        # (西端経度, 南端緯度, 東端経度, 北端緯度)

# Retrieves granules and links list from the passes we want, filtered by
# collection shortname, temporal bounds, granule name, and spatial bounding box.
#
# NOTE: 再処理版 "2.0" は 2025-05-02 で granule が途切れる。以降は現行処理版 "D"
# (SWOT_L2_HR_RiverSP_reach_D) に存在するため、継ぎ目を 2025-05-02/03 に置いて
# 版の重複(同期間の二重観測)を避けつつ両版を結合する。
_gname = "*Reach*_" + continent_code + "*"
_specs = [
    ('SWOT_L2_HR_RIVERSP_2.0',        ('2000-01-25 00:00:00', '2025-05-02 23:59:59')),
    ('SWOT_L2_HR_RiverSP_reach_D',    ('2025-05-03 00:00:00', '2099-05-16 23:59:59')),
]
river_results = []
for _sn, _temporal in _specs:
    _r = earthaccess.search_data(short_name = _sn,
                                 temporal = _temporal,
                                 granule_name = _gname,
                                 bounding_box = bbox)
    print(f"search {_sn} {_temporal}: {len(_r)} granules")
    river_results += list(_r)

download_dir = RiverSP_download_dir()
os.makedirs(download_dir, exist_ok=True)

# Collect one external link per granule
links_list = []
for r in tqdm(range(len(river_results)), desc="collecting links"):
    river_link = earthaccess.results.DataGranule.data_links(river_results[r], access='external')[0]
    links_list.append(river_link)

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
