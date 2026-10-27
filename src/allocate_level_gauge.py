"""Python port of the cell choice in CaMa-Flood's map/<region>/src_param/allocate_level_gauge.F90.

The Fortran program follows the river from the chosen pixel to its unit-catchment outlet (for the
distance and the mainstem / tributary type) without a bounds check, and crashes (SIGSEGV) where the
river leaves a regional high-res map (ARB_06min: e.g. SWORD reach 1788 at 4.88N, 61.39W).  Only the
cell is needed downstream (p04), so this port keeps the part that decides it, as in the Fortran:
  - gauges outside the CaMa domain (params.txt west/east/south/north) are skipped (not written)
  - search the +-3 high-res pixels around the gauge for uparea > 5 % of the gauge's area; error
    err = (upa - area) / area, plus 0.02 x dd where dd = sqrt(2) |dy| (the Fortran's
    ((jy-iy)**2 + (jy-iy)**2)**0.5, dx not used), rate = 1 + err2 (over) or 1 / (1 + err2) (under,
    at most 1000); the first pixel (dy outer, dx inner) with the smallest rate wins
  - the cell is the pixel's unit catchment (catmxy); none found or catmxy < 0 -> Type -9
Output columns as the Fortran's gauge_alloc.txt: ID lat lon area Type ix1 iy1 ix2 iy2 and five
-999.0 columns (Type 0 = allocated; the mainstem / tributary type, elevations and distances are not
computed).

Usage:  allocate_level_gauge.py <step-1 gauge list> <CaMa map dir> <output>
"""
import os
import sys

import numpy as np


def main(gaugelist, map_dir, out):
    p = open(os.path.join(map_dir, "params.txt")).read().split("\n")
    west, east, south, north = (float(p[k].split()[0]) for k in (4, 5, 6, 7))
    hires = "1min"
    loc = open(os.path.join(map_dir, hires, "location.txt")).read().split("\n")[2].split()
    west2, east2, south2, north2 = (float(v) for v in loc[2:6])
    nx, ny = int(loc[6]), int(loc[7])
    csize = (east2 - west2) / nx
    n = nx * ny
    # each file starts with the region's block (Fortran direct access, record 1 / 2); the rest is unused
    upa = np.fromfile(os.path.join(map_dir, hires, f"{hires}.uparea.bin"), np.float32)[:n].reshape(ny, nx)
    cat = np.fromfile(os.path.join(map_dir, hires, f"{hires}.catmxy.bin"), np.int16)[:2 * n].reshape(2, ny, nx)

    rows = []
    with open(gaugelist) as f:
        next(f)
        for line in f:
            v = line.replace(",", " ").split()
            gid, lat0, lon0, area0 = int(v[0]), float(v[1]), float(v[2]), float(v[3])
            if lon0 < west or lon0 > east or lat0 < south or lat0 > north:
                continue
            ix = int((lon0 - west2) / csize) + 1
            iy = int((north2 - lat0) / csize) + 1
            rate0, best = 1.e20, None
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    jx, jy = ix + dx, iy + dy
                    if jx <= 0 or jx > nx or jy <= 0 or jy > ny:
                        continue
                    u = float(upa[jy - 1, jx - 1])
                    if not u > area0 * 0.05:
                        continue
                    err = (u - area0) / area0
                    dd = (2.0 * (jy - iy) ** 2) ** 0.5
                    err2 = err + 0.02 * dd if err > 0 else (err - 0.02 * dd if err < 0 else err)
                    if err2 >= 0:
                        rate = 1 + err2
                    elif -1 < err2 < 0:
                        rate = min(1. / (1 + err2), 1000.)
                    else:
                        rate = 1000.
                    if rate < rate0:
                        rate0, best = rate, (jx, jy)
            typ, ixx, iyy = -9, -999, -999
            if best is not None and area0 > 0:
                cx, cy = int(cat[0, best[1] - 1, best[0] - 1]), int(cat[1, best[1] - 1, best[0] - 1])
                if cx >= 0 and cy >= 0:
                    typ, ixx, iyy = 0, cx, cy
            rows.append((gid, lat0, lon0, area0, typ, ixx, iyy))

    with open(out, "w") as w:
        w.write("        ID       lat       lon        area    Type     ix1   iy1     ix2   iy2"
                "  elv_outlet   elv_gauge    elv_upst  dst_outlet    dst_upst\n")
        for gid, lat0, lon0, area0, typ, ixx, iyy in rows:
            w.write(f"{gid:10d}{lat0:10.3f}{lon0:10.3f}{area0:12.1f}{typ:8d}{ixx:8d}{iyy:6d}{-999:8d}{-999:6d}"
                    + "".join(f"{-999.0:12.2f}" for _ in range(5)) + "\n")
    print(f"{len(rows)} gauges in the domain, {sum(r[4] == 0 for r in rows)} allocated -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
