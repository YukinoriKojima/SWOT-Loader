import sys
sys.path.append('../config')

from config import SWORD_raw_dir
import os, hashlib, zipfile, requests

RECORD_ID = '10013982'
FILENAME  = 'SWORD_v16_netcdf.zip'

out_dir  = SWORD_raw_dir()
zip_path = f'{out_dir}.zip'
os.makedirs(out_dir, exist_ok=True)

# Get the expected checksum and size from Zenodo's API
meta = requests.get(f'https://zenodo.org/api/records/{RECORD_ID}', timeout=60).json()
finfo = next(f for f in meta['files'] if f['key'] == FILENAME)
expected_md5  = finfo['checksum'].split(':', 1)[1]
expected_size = finfo['size']
url = f'https://zenodo.org/records/{RECORD_ID}/files/{FILENAME}?download=1'

def md5sum(path, chunk=8 << 20):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()

from tqdm import tqdm

done = os.path.exists(zip_path) and os.path.getsize(zip_path) == expected_size
while not done:
    have = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
    headers = {'Range': f'bytes={have}-'} if have else {}
    with requests.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        resumed = (r.status_code == 206)
        mode = 'ab' if resumed else 'wb'
        with open(zip_path, mode) as f, tqdm(
            total=expected_size,
            initial=have if resumed else 0,
            unit='B', unit_scale=True, unit_divisor=1024,
            desc=FILENAME,
        ) as bar:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                bar.update(len(chunk))
    done = os.path.getsize(zip_path) == expected_size

if md5sum(zip_path) != expected_md5:
    raise RuntimeError(f'MD5 mismatch for {zip_path}; delete it and re-run')

with zipfile.ZipFile(zip_path) as z:
    z.extractall(out_dir)
print('Extracted to', out_dir)