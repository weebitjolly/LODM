import os
import random
import math
import re
from pathlib import Path

import pandas as pd
import numpy as np
import geopandas as gpd
import fiona
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, substring, unary_union

# =============================================
# Deployment auto-selection (latest deployment)
# =============================================

def get_latest_deployment_path(deployments_root: str) -> Path:
    """
    Find the subfolder in `deployments_root` with name pattern 'deployment_<int>',
    return the one with the highest <int>. Raises ValueError if none are found.
    """
    root = Path(deployments_root)
    if not root.exists():
        raise ValueError(f"Deployments root does not exist: {deployments_root}")

    pattern = re.compile(r"^deployment_(\d+)$", re.IGNORECASE)
    candidates = []
    for entry in root.iterdir():
        if entry.is_dir():
            m = pattern.match(entry.name)
            if m:
                try:
                    num = int(m.group(1))
                    candidates.append((num, entry))
                except ValueError:
                    pass

    if not candidates:
        raise ValueError(f"No 'deployment_<number>' folders found in: {deployments_root}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    latest_num, latest_path = candidates[0]
    print(f"📂 Selected latest deployment: {latest_path.name} (#{latest_num})")
    return latest_path

# ==================
# Configuration
# ==================

# Root folder that contains deployment_* subfolders
DEPLOYMENTS_ROOT = r"C:\Litter Production\Deployments"
LATEST_DEPLOYMENT_PATH = get_latest_deployment_path(DEPLOYMENTS_ROOT)

# Data inputs
CENTERLINES_PATH = r"C:\Litter Production\GIS Reference\Street_centerlines_City_of_Norfolk"
CENTERLINES_LAYER = None  # e.g., "Centerlines" if your GPKG/FGDB has multiple layers
WARDS_PATH = r"K:\Data Science\GIS Reference\Wards.shp"
WARDS_LAYER = None
WARD_ID_FIELD = "WARD"

# Generation settings
NUM_ROUTES = 30
ROUTES_PER_WARD = 5
TARGET_M = 1207.33  
SEED = 4
MIN_FRACTION_IN_WARD = 0.60
SNAP_TOLERANCE_M = 3.0   # how close endpoints must be to be considered connected (meters)
MAX_STEPS = 2000         # safety cap for random walks
AVOID_OVERLAP = True
OVERLAP_BUFFER_M = 2.0
RESERVE_FULL_SEGMENTS = True

# Output naming (inside the current deployment)
OUTPUT_PREFIX = "norfolk_centerlines_random_routes_by_ward"
FGDB_NAME = f"{OUTPUT_PREFIX}.gdb"               # FileGDB folder
FGDB_PATH = LATEST_DEPLOYMENT_PATH / FGDB_NAME   # e.g., ...\deployment_4\norfolk_centerlines_random_routes_by_ward.gdb
GPKG_PATH = LATEST_DEPLOYMENT_PATH / f"{OUTPUT_PREFIX}.gpkg"
SHP_PATH  = LATEST_DEPLOYMENT_PATH / f"{OUTPUT_PREFIX}.shp"  # optional
CSV_PATH  = LATEST_DEPLOYMENT_PATH / f"{OUTPUT_PREFIX}.csv"

# -----------------------------
# Helpers
# -----------------------------

def load_wards(path, layer=None, target_crs=None):
    print(f"Loading wards from: {path} (layer={layer})")
    gdf = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    # Explode multipolygons
    if "index_parts" in gpd.GeoDataFrame.explode.__code__.co_varnames:
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    else:
        gdf = gdf.explode().reset_index(drop=True)
    # Project to centerline CRS if provided; else pick local meter CRS
    if target_crs is not None:
        gdf = gdf.to_crs(target_crs)
    else:
        crs_m = gdf.estimate_utm_crs()
        gdf = gdf.to_crs(crs_m)
    print(f"Wards loaded: {len(gdf)}")
    return gdf

def filter_streets_to_ward(streets_proj: gpd.GeoDataFrame,
                           ward_poly,
                           min_fraction: float = MIN_FRACTION_IN_WARD) -> gpd.GeoDataFrame:
    """
    Keep centerline segments where the fraction of segment length inside ward_poly
    is at least min_fraction. Assumes streets_proj is already in a meter-based CRS.
    """
    if streets_proj is None or len(streets_proj) == 0:
        print("[filter_streets_to_ward] WARNING: streets_proj is empty or None.")
        return gpd.GeoDataFrame(columns=streets_proj.columns, geometry="geometry", crs=getattr(streets_proj, "crs", None))
    if ward_poly is None or ward_poly.is_empty:
        print("[filter_streets_to_ward] WARNING: ward_poly is None/empty.")
        return streets_proj.iloc[0:0].copy()
    try:
        if not ward_poly.is_valid:
            ward_poly = ward_poly.buffer(0)
    except Exception as e:
        print(f"[filter_streets_to_ward] WARNING: ward_poly validity fix failed: {e}")
        return streets_proj.iloc[0:0].copy()

    if streets_proj.crs is None:
        raise ValueError("[filter_streets_to_ward] streets_proj has no CRS.")

    try:
        inter_geom = streets_proj.geometry.intersection(ward_poly)
        inter_len = inter_geom.length
        seg_len = streets_proj.geometry.length.replace(0, pd.NA)
        frac = (inter_len / seg_len).fillna(0.0)
        mask = frac >= float(min_fraction)
        subset = streets_proj[mask].copy()
        print(f"[filter_streets_to_ward] Segments in ward (>= {min_fraction*100:.0f}%): {len(subset)} / {len(streets_proj)}")
        return subset
    except Exception as e:
        print(f"[filter_streets_to_ward] ERROR during intersection: {e}")
        return streets_proj.iloc[0:0].copy()

def filter_centerlines_excluding_highways_by_type(
    streets_gdf: gpd.GeoDataFrame,
    st_type_field: str = "ST_TYPE",
    exclude_keywords: list[str] | None = None,
) -> gpd.GeoDataFrame:
    gdf = streets_gdf.copy()
    if st_type_field not in gdf.columns:
        raise ValueError(f"Field '{st_type_field}' not found in centerlines.")
    col = gdf[st_type_field].astype(str).str.strip().str.upper()
    mask = pd.Series(False, index=gdf.index)
    if exclude_keywords:
        pattern = "|".join([kw.strip().upper() for kw in exclude_keywords if kw and kw.strip()])
        kw_mask = col.str.contains(pattern, na=False)
        mask = mask | kw_mask
    filtered = gdf[~mask].copy()
    print(f"Filtered out {int(mask.sum())} segments by ST_TYPE; remaining: {len(filtered)}")
    return filtered

def filter_centerlines_excluding_vdot(
    streets_gdf: gpd.GeoDataFrame,
    vdot_field: str = "VDOT",
    excluded_values: tuple[int, ...] = (7, 8, 9),
) -> gpd.GeoDataFrame:
    gdf = streets_gdf.copy()
    if vdot_field not in gdf.columns:
        print(f"Field '{vdot_field}' not found; skipping VDOT filter.")
        return gdf
    vdot_num = pd.to_numeric(gdf[vdot_field], errors="coerce")
    mask = vdot_num.isin(excluded_values)
    filtered = gdf[~mask].copy()
    print(f"Filtered out {int(mask.sum())} segments by {vdot_field} in {excluded_values}; remaining: {len(filtered)}")
    return filtered

def intersects_used(line: LineString, used_union, buffer_m: float) -> bool:
    if used_union is None:
        return False
    test_geom = line if buffer_m <= 0 else line.buffer(buffer_m, cap_style=2, join_style=2)
    return test_geom.intersects(used_union)

def load_centerlines(path, layer=None):
    """
    Load centerlines into a GeoDataFrame. Accepts GPKG/SHP/FGDB/Feature Service.
    """
    print(f"Loading centerlines from: {path} (layer={layer})")
    gdf = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    # Explode to individual LineStrings
    if "index_parts" in gpd.GeoDataFrame.explode.__code__.co_varnames:
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    else:
        gdf = gdf.explode().reset_index(drop=True)
    # Project to local meter-based CRS
    crs_m = gdf.estimate_utm_crs()
    gdf = gdf.to_crs(crs_m)
    gdf["length_m"] = gdf.geometry.length
    print(f"Projected to: {crs_m.to_authority()} | segments: {len(gdf)}")
    return gdf

def line_endpoints(line: LineString) -> tuple[Point, Point]:
    coords = list(line.coords)
    return Point(coords[0]), Point(coords[-1])

def orient_line_starting_at(line: LineString, near_pt: Point, tol: float) -> LineString:
    start_pt, end_pt = line_endpoints(line)
    if start_pt.distance(near_pt) <= tol:
        return line
    elif end_pt.distance(near_pt) <= tol:
        return LineString(list(line.coords)[::-1])
    else:
        return line

def trim_line_to_length(line: LineString, target_len: float) -> LineString:
    if target_len <= 0:
        return LineString([line.coords[0]])
    total = line.length
    if target_len >= total:
        return line
    return substring(line, 0, target_len, normalized=False)

def build_endpoint_pairs(streets_proj: gpd.GeoDataFrame, snap_tol_m: float):
    records = []
    for seg_id, geom in enumerate(streets_proj.geometry.values):
        if geom is None or geom.is_empty or geom.geom_type != "LineString":
            continue
        s_pt, e_pt = line_endpoints(geom)
        records.append({"seg_id": seg_id, "ep_idx": 0, "geometry": s_pt})
        records.append({"seg_id": seg_id, "ep_idx": 1, "geometry": e_pt})

    endpoints = gpd.GeoDataFrame(records, geometry="geometry", crs=streets_proj.crs)

    buffered = endpoints.copy()
    buffered["geometry"] = buffered.geometry.buffer(snap_tol_m)

    pairs = gpd.sjoin(
        buffered.rename(columns={"seg_id": "left_seg_id", "ep_idx": "left_ep_idx"}),
        endpoints.rename(columns={"seg_id": "right_seg_id", "ep_idx": "right_ep_idx"}),
        predicate="intersects",
        how="inner",
    )
    pairs = pairs[(pairs["left_seg_id"] != pairs["right_seg_id"]) |
                  (pairs["left_ep_idx"] != pairs["right_ep_idx"])].copy()

    pairs = pairs[["left_seg_id", "left_ep_idx", "right_seg_id", "right_ep_idx", "geometry"]].reset_index(drop=True)
    pairs = pairs.rename(columns={"geometry": "join_area"})

    right_points = endpoints.rename(columns={
        "seg_id": "right_seg_id", "ep_idx": "right_ep_idx", "geometry": "right_point"
    })
    pairs = pairs.merge(right_points, on=["right_seg_id", "right_ep_idx"], how="left")

    return pairs, endpoints

def generate_one_route(streets_proj: gpd.GeoDataFrame,
                       pairs_df: gpd.GeoDataFrame,
                       endpoints_df: gpd.GeoDataFrame,
                       target_m: float,
                       rng: random.Random,
                       max_steps: int,
                       snap_tol_m: float,
                       used_seg_ids: set[int] | None = None,
                       used_union=None,
                       avoid_overlap: bool = True,
                       overlap_buffer_m: float = 0.0,
                       reserve_full_segments: bool = True):
    used_seg_ids = used_seg_ids or set()

    # Candidate starts
    candidate_starts = []
    for seg_id, geom in enumerate(streets_proj.geometry.values):
        if seg_id in used_seg_ids:
            continue
        if avoid_overlap and intersects_used(geom, used_union, overlap_buffer_m):
            continue
        candidate_starts.append(seg_id)
    if not candidate_starts:
        return None, []

    start_seg = rng.choice(candidate_starts)
    start_line: LineString = streets_proj.geometry.iloc[start_seg]
    start_ep_idx = rng.choice([0, 1])
    start_pt = endpoints_df[(endpoints_df["seg_id"] == start_seg) &
                            (endpoints_df["ep_idx"] == start_ep_idx)].geometry.iloc[0]
    curr_line = orient_line_starting_at(start_line, start_pt, snap_tol_m)
    if avoid_overlap and intersects_used(curr_line, used_union, overlap_buffer_m):
        return None, []

    path_coords = list(curr_line.coords)
    cum_len = curr_line.length

    prev_seg = None
    curr_seg = start_seg
    used_this_route: list[int] = [curr_seg] if reserve_full_segments else []
    curr_tail_pt = Point(path_coords[-1])

    def _pt_key(pt: Point, ndp: int = 3) -> tuple[float, float]:
        return (round(pt.x, ndp), round(pt.y, ndp))

    visited_nodes = set()
    s_ep, e_ep = line_endpoints(curr_line)
    visited_nodes.add(_pt_key(s_ep))
    visited_nodes.add(_pt_key(e_ep))

    steps = 0
    while cum_len < target_m and steps < max_steps:
        steps += 1

        cand = pairs_df[(pairs_df["left_seg_id"] == curr_seg) &
                        (pairs_df["left_ep_idx"].isin([0, 1])) &
                        (pairs_df["right_seg_id"] != curr_seg)].copy()
        cand = cand[cand["right_point"].distance(curr_tail_pt) <= snap_tol_m]
        cand = cand[cand["right_seg_id"] != prev_seg]
        cand = cand[~cand["right_seg_id"].isin(list(used_seg_ids))]

        if cand.empty:
            return None, []

        min_seg_len_m = 25.0
        viable = []
        for _, row in cand.iterrows():
            nsid = int(row["right_seg_id"])
            nline = streets_proj.geometry.iloc[nsid]
            nline_oriented = orient_line_starting_at(nline, curr_tail_pt, snap_tol_m)
            if nline_oriented.length < min_seg_len_m:
                continue
            n_s, n_e = line_endpoints(nline_oriented)
            far_ep = n_e if _pt_key(n_s) == _pt_key(curr_tail_pt) else n_s
            if _pt_key(far_ep) in visited_nodes:
                continue
            viable.append((nsid, nline_oriented, far_ep))

        if not viable:
            return None, []

        next_seg, next_line_oriented, far_ep = viable[rng.randrange(len(viable))]
        next_len = next_line_oriented.length

        if avoid_overlap and intersects_used(next_line_oriented, used_union, overlap_buffer_m):
            return None, []

        remaining = target_m - cum_len
        if next_len > remaining:
            next_line_trimmed = trim_line_to_length(next_line_oriented, remaining)
            coords_to_add = list(next_line_trimmed.coords)[1:]
            path_coords.extend(coords_to_add)
            cum_len = target_m
            if reserve_full_segments:
                used_this_route.append(next_seg)
            break
        else:
            coords_to_add = list(next_line_oriented.coords)[1:]
            path_coords.extend(coords_to_add)
            visited_nodes.add(_pt_key(Point(coords_to_add[-1])))
            cum_len += next_len
            if reserve_full_segments:
                used_this_route.append(next_seg)

        prev_seg = curr_seg
        curr_seg = next_seg
        curr_tail_pt = Point(path_coords[-1])

    if cum_len < target_m - 0.5:
        return None, []

    final_line = LineString(path_coords)
    if final_line.length > target_m + 0.5:
        final_line = trim_line_to_length(final_line, target_m)

    return final_line, used_this_route

def generate_routes_for_ward(streets_full_proj: gpd.GeoDataFrame,
                             ward_poly,
                             ward_name: str,
                             num_routes: int = ROUTES_PER_WARD,
                             target_m: float = TARGET_M,
                             seed: int = SEED,
                             snap_tol_m: float = SNAP_TOLERANCE_M,
                             max_steps: int = MAX_STEPS,
                             avoid_overlap: bool = AVOID_OVERLAP,
                             overlap_buffer_m: float = OVERLAP_BUFFER_M,
                             reserve_full_segments: bool = RESERVE_FULL_SEGMENTS):
    streets_sub = filter_streets_to_ward(streets_full_proj, ward_poly, MIN_FRACTION_IN_WARD)
    if streets_sub.empty:
        print(f"[{ward_name}] No eligible segments; skipping.")
        return None, None

    print(f"[{ward_name}] Building endpoint connectivity...")
    pairs_df, endpoints_df = build_endpoint_pairs(streets_sub, snap_tol_m)

    rng = random.Random(seed)
    segments = []
    attempts = 0
    max_attempts = num_routes * 100
    used_seg_ids = set()
    used_union = None

    print(f"[{ward_name}] Generating {num_routes} routes of {target_m:.2f} m...")
    while len(segments) < num_routes and attempts < max_attempts:
        attempts += 1
        seg, seg_ids_used = generate_one_route(
            streets_sub, pairs_df, endpoints_df,
            target_m, rng, max_steps, snap_tol_m,
            used_seg_ids=used_seg_ids,
            used_union=used_union,
            avoid_overlap=avoid_overlap,
            overlap_buffer_m=overlap_buffer_m,
            reserve_full_segments=reserve_full_segments
        )
        if seg is None:
            continue
        wkt_proj = seg.wkt
        if any(s["wkt_proj"] == wkt_proj for s in segments):
            continue
        for sid in seg_ids_used:
            used_seg_ids.add(sid)
        used_union = seg if overlap_buffer_m <= 0 else seg.buffer(overlap_buffer_m, cap_style=2, join_style=2)
        segments.append({"geometry_proj": seg, "wkt_proj": wkt_proj})

    if len(segments) < num_routes:
        print(f"[{ward_name}] WARNING: Only generated {len(segments)} routes after {attempts} attempts.")

    crs_proj = streets_sub.crs
    gdf_proj = gpd.GeoDataFrame(
        {
            "Ward": [ward_name] * len(segments),
            "Route": [f"{ward_name}_R{str(i+1).zfill(3)}" for i in range(len(segments))],
            "geometry": [s["geometry_proj"] for s in segments],
        },
        geometry="geometry",
        crs=crs_proj
    )
    gdf_proj["length_m"] = gdf_proj.geometry.length
    gdf = gdf_proj.to_crs(epsg=4326)
    gdf["min_lon"] = gdf.geometry.bounds.minx
    gdf["min_lat"] = gdf.geometry.bounds.miny
    gdf["max_lon"] = gdf.geometry.bounds.maxx
    gdf["max_lat"] = gdf.geometry.bounds.maxy
    return gdf, gdf_proj

def generate_routes_from_centerlines(centerlines_path=CENTERLINES_PATH,
                                     centerlines_layer=CENTERLINES_LAYER,
                                     num_routes=NUM_ROUTES,
                                     target_m=TARGET_M,
                                     seed=SEED,
                                     snap_tol_m=SNAP_TOLERANCE_M,
                                     max_steps=MAX_STEPS,
                                     avoid_overlap=AVOID_OVERLAP,
                                     overlap_buffer_m=OVERLAP_BUFFER_M,
                                     reserve_full_segments=RESERVE_FULL_SEGMENTS):
    rng = random.Random(seed)

    streets = load_centerlines(centerlines_path, centerlines_layer)
    if len(streets) == 0:
        raise RuntimeError("No centerline features loaded.")

    streets = filter_centerlines_excluding_vdot(streets, vdot_field="VDOT", excluded_values=(7, 8, 9))
    streets = filter_centerlines_excluding_highways_by_type(streets, st_type_field="ST_TYPE",
                                                            exclude_keywords=["HIGHWAY", "TRAIL", "WALK", "BRIDGE"])
    print("Building endpoint connectivity...")
    pairs_df, endpoints_df = build_endpoint_pairs(streets, snap_tol_m)
    print(f"Endpoint pairs within {snap_tol_m} m: {len(pairs_df)}")

    segments = []
    attempts = 0
    max_attempts = num_routes * 100

    used_seg_ids: set[int] = set()
    used_union = None

    print(f"Generating {num_routes} non-overlapping routes of {target_m:.2f} meters...")
    while len(segments) < num_routes and attempts < max_attempts:
        attempts += 1
        seg, seg_ids_used = generate_one_route(
            streets, pairs_df, endpoints_df,
            target_m, rng, max_steps, snap_tol_m,
            used_seg_ids=used_seg_ids,
            used_union=used_union,
            avoid_overlap=avoid_overlap,
            overlap_buffer_m=overlap_buffer_m,
            reserve_full_segments=reserve_full_segments
        )
        if seg is None:
            continue
        wkt_proj = seg.wkt
        if any(s["wkt_proj"] == wkt_proj for s in segments):
            continue
        for sid in seg_ids_used:
            used_seg_ids.add(sid)
        if used_union is None:
            used_union = seg if overlap_buffer_m <= 0 else seg.buffer(overlap_buffer_m, cap_style=2, join_style=2)
        else:
            new_piece = seg if overlap_buffer_m <= 0 else seg.buffer(overlap_buffer_m, cap_style=2, join_style=2)
            used_union = unary_union([used_union, new_piece])
        segments.append({"geometry_proj": seg, "wkt_proj": wkt_proj})

    if len(segments) < num_routes:
        raise RuntimeError(
            f"Only generated {len(segments)} routes after {attempts} attempts. "
            f"Try increasing max_attempts, relaxing overlap_buffer_m, or reducing num_routes."
        )

    crs_proj = streets.crs
    gdf_proj = gpd.GeoDataFrame(
        {"Route": [f"R{str(i+1).zfill(3)}" for i in range(len(segments))],
         "geometry": [s["geometry_proj"] for s in segments]},
        geometry="geometry",
        crs=crs_proj
    )
    gdf_proj["length_m"] = gdf_proj.geometry.length

    gdf = gdf_proj.to_crs(epsg=4326)
    gdf["min_lon"] = gdf.geometry.bounds.minx
    gdf["min_lat"] = gdf.geometry.bounds.miny
    gdf["max_lon"] = gdf.geometry.bounds.maxx
    gdf["max_lat"] = gdf.geometry.bounds.maxy

    return gdf, gdf_proj

# -----------------------------
# Run + Export (inside deployment)
# -----------------------------

if __name__ == "__main__":
    # 1) Load & filter centerlines
    streets = load_centerlines(CENTERLINES_PATH, CENTERLINES_LAYER)
    streets = filter_centerlines_excluding_vdot(streets, vdot_field="VDOT", excluded_values=(7, 8, 9))
    streets = filter_centerlines_excluding_highways_by_type(
        streets_gdf=streets,
        st_type_field="ST_TYPE",
        exclude_keywords=["HIGHWAY", "TRAIL", "WALK", "BRIDGE"],
    )

    # 2) Load wards (to same projected CRS)
    wards = load_wards(WARDS_PATH, WARDS_LAYER, target_crs=streets.crs)
    if WARD_ID_FIELD not in wards.columns:
        raise ValueError(f"Field '{WARD_ID_FIELD}' not found in wards.")

    # 3) For each ward, generate routes
    all_wgs84 = []
    all_proj = []
    for _, row in wards.iterrows():
        ward_name = str(row[WARD_ID_FIELD])
        ward_poly = row.geometry
        g_wgs84, g_proj = generate_routes_for_ward(
            streets_full_proj=streets,
            ward_poly=ward_poly,
            ward_name=ward_name,
            num_routes=ROUTES_PER_WARD,
            target_m=TARGET_M,
            seed=SEED,
            snap_tol_m=SNAP_TOLERANCE_M,
            max_steps=MAX_STEPS,
            avoid_overlap=AVOID_OVERLAP,
            overlap_buffer_m=OVERLAP_BUFFER_M,
            reserve_full_segments=RESERVE_FULL_SEGMENTS
        )
        if g_wgs84 is None:
            continue
        all_wgs84.append(g_wgs84)
        all_proj.append(g_proj)

    if not all_wgs84:
        raise RuntimeError("No ward routes generated. Check ward filter or data coverage.")

    routes_wgs84 = pd.concat(all_wgs84, ignore_index=True)
    routes_proj = pd.concat(all_proj, ignore_index=True)

    # 4) Export inside the current deployment
    print(f"📁 Deployment outputs will be saved to: {LATEST_DEPLOYMENT_PATH}")

    # Try FileGDB first (requires Fiona/GDAL with FileGDB write support)
    can_write_fgdb = ("FileGDB" in fiona.supported_drivers) and (fiona.supported_drivers["FileGDB"] == "rw")
    if can_write_fgdb:
        print(f"Saving FileGDB at: {FGDB_PATH}")
        # Write each layer; Fiona will create the .gdb directory automatically
        routes_wgs84.to_file(FGDB_PATH, layer="routes_wgs84", driver="FileGDB")
        # Projected layer with length_m
        routes_proj.to_file(FGDB_PATH, layer="routes_proj", driver="FileGDB")
    else:
        print("⚠️ FileGDB write driver not available; saving GeoPackage instead.")
        routes_wgs84.to_file(GPKG_PATH, layer="routes_wgs84", driver="GPKG")
        routes_proj.to_file(GPKG_PATH, layer="routes_proj", driver="GPKG")

    # Optional: Shapefile (one layer) — comment out if not needed
    # print(f"Saving Shapefile at: {SHP_PATH}")
    # routes_wgs84.to_file(SHP_PATH)

    # 5) Save CSV (WKT + bounds) for detection pipeline
    print(f"Saving CSV at: {CSV_PATH}")
    df_csv = pd.DataFrame({
        "Ward": routes_wgs84["Ward"],
        "Route": routes_wgs84["Route"],
        "WKT": routes_wgs84.geometry.apply(lambda g: g.wkt),
        "length_m": routes_proj["length_m"],
        "min_lon": routes_wgs84["min_lon"],
        "min_lat": routes_wgs84["min_lat"],
        "max_lon": routes_wgs84["max_lon"],
        "max_lat": routes_wgs84["max_lat"],
    })
    df_csv.to_csv(CSV_PATH, index=False)

    print("✅ Done.")
    if can_write_fgdb:
        print(f"Outputs:\n - {FGDB_PATH}\\routes_wgs84\n - {FGDB_PATH}\\routes_proj\n - {CSV_PATH}")
    else:
        print(f"Outputs:\n - {GPKG_PATH} (layers: routes_wgs84, routes_proj)\n - {CSV_PATH}")


