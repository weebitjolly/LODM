import os
import re
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2
import exifread
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from PIL import Image
from ultralytics import YOLO
 
# === CONFIG ===

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
                    # Non-integer suffix; ignore gracefully
                    pass

    if not candidates:
        raise ValueError(f"No 'deployment_<number>' folders found in: {deployments_root}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    latest_num, latest_path = candidates[0]
    print(f"📂 Selected latest deployment: {latest_path.name} (#{latest_num})")
    return latest_path
# ======================================================

# === CONFIG ===

# Root folder that contains deployment_* subfolders
DEPLOYMENTS_ROOT = r"C:\Litter Production\Deployments"

# Resolve latest deployment and build the images path (Raw Deployment Images\Preprocessed)
LATEST_DEPLOYMENT_PATH = get_latest_deployment_path(DEPLOYMENTS_ROOT)
image_folder = str(LATEST_DEPLOYMENT_PATH / "Raw Deployment Images" / "Preprocessed")
print(f"🔍 Image folder: {image_folder}")

model_path = r"C:\Litter Production\Models\OG Litter.pt" 
wards_shape_file = r"K:\Data Science\GIS Reference\Wards.shp" 
deployment_tag = LATEST_DEPLOYMENT_PATH.name  # e.g. 'deployment_4'
output_csv = fr"K:\Data Science\KNB\Litter Master\Results\individual_results\litter_results_{deployment_tag}.csv"
output_image_folder = str(LATEST_DEPLOYMENT_PATH / "Annotated Results")
label_output_folder = str(LATEST_DEPLOYMENT_PATH / "Annotation Day")

OUTPUT_PREFIX = "norfolk_centerlines_random_routes_by_ward_final"

# Build the path to the CSV created by the randomizer (inside the latest deployment)
routes_csv_path = LATEST_DEPLOYMENT_PATH / f"{OUTPUT_PREFIX}.csv"

# Optional: sanity check to fail fast if the CSV isn’t there yet
if not routes_csv_path.exists():
    raise FileNotFoundError(
        f"Routes CSV not found at: {routes_csv_path}\n"
        f"Make sure you ran the route randomizer for this deployment."
    )

# This is the value your current script expects for pd.read_csv(...)
routes_df = str(routes_csv_path)

WARD_FIELD = "WARD"
os.makedirs(output_image_folder, exist_ok=True)
os.makedirs(label_output_folder, exist_ok=True)
 
#YOLO Model
model = YOLO(model_path)
 
#Configuration
#Haversine distance function for litter calculation 
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)

    a = sin(d_phi / 2)**2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

# --- Total Route Distance func ---
def total_route_distance(route_points):
    return sum(
        haversine_distance(*route_points[i], *route_points[i + 1])
        for i in range(len(route_points) - 1)
    )
 
#EXIF Extraction
def extract_exif(filepath):
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f, details=False)
 
    timestamp = tags.get('EXIF DateTimeOriginal')
    gps_lat = tags.get('GPS GPSLatitude')
    gps_lon = tags.get('GPS GPSLongitude')
    gps_lat_ref = tags.get('GPS GPSLatitudeRef')
    gps_lon_ref = tags.get('GPS GPSLongitudeRef')
 
    def to_decimal(value):
        d, m, s = [float(x.num) / float(x.den) for x in value.values]
        return d + m / 60 + s / 3600
 
    lat = lon = None
    if gps_lat and gps_lon:
        lat = to_decimal(gps_lat)
        if gps_lat_ref.values[0] == 'S':
            lat = -lat
        lon = to_decimal(gps_lon)
        if gps_lon_ref.values[0] == 'W':
            lon = -lon
 
    return {
        "timestamp": str(timestamp) if timestamp else None,
        "latitude": lat,
        "longitude": lon
    }
#Spatial Joins

import pandas as pd

# Route Join switch to this on the day of processing
route_bounds = (
    pd.read_csv(routes_df)
      .loc[:, ["Route", "min_lon", "max_lon", "min_lat", "max_lat"]]
      .assign(
          min_lon=lambda df: pd.to_numeric(df["min_lon"], errors="coerce"),
          max_lon=lambda df: pd.to_numeric(df["max_lon"], errors="coerce"),
          min_lat=lambda df: pd.to_numeric(df["min_lat"], errors="coerce"),
          max_lat=lambda df: pd.to_numeric(df["max_lat"], errors="coerce"),
      )
      .dropna(subset=["min_lon", "max_lon", "min_lat", "max_lat"])
      .reset_index(drop=True)
)

# route_bounds = (
#     routes_df.groupby("Route")
#     .agg(min_lon=("POINT_X", "min"),
#          max_lon=("POINT_X", "max"),
#          min_lat=("POINT_Y", "min"),
#          max_lat=("POINT_Y", "max"))
#     .reset_index()
# ) # needs attention need to reference the csv generated from route randomizer 

def match_route(lat, lon, bounds_df):
    for _, row in bounds_df.iterrows():
        if row["min_lat"] <= lat <= row["max_lat"] and row["min_lon"] <= lon <= row["max_lon"]:
            return str(row["Route"])
    return "Not on route"

# Process All Images 
results = []
 
# need to make this a function in order to call it in a multithreading pipeline
for filename in os.listdir(image_folder): 
    if filename is None:
        print("no image")

    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
 
    image_path = os.path.join(image_folder, filename)
    print(f"🔍 Processing {filename}...")
 
    try:
        img = Image.open(image_path).convert("RGB")
        exif = extract_exif(image_path)

        # Run YOLO inference
        yolo_result = model(img)[0]

        # Save annotated image (original detections view)
        annotated_img = yolo_result.plot()
        Image.fromarray(annotated_img).save(
            os.path.join(output_image_folder, f"annotated_{filename}")
        )

        confidence_threshold = 0.01
        boxes = yolo_result.boxes

        # --- Default state ---
        count = 0  # litter_count default
        filtered_boxes = None

        # --- Process boxes safely ---
        if boxes is not None:
            # Some versions of Ultralytics expose a tensor via boxes.data
            # Use len(boxes) if supported; otherwise fall back to boxes.data shape.
            try:
                n_boxes = len(boxes)
            except Exception:
                n_boxes = int(getattr(getattr(boxes, "data", None), "shape", [0])[0])

            if n_boxes > 0 and hasattr(boxes, "conf") and boxes.conf is not None:
                # Filter boxes by confidence
                mask = boxes.conf >= confidence_threshold
                filtered_boxes = boxes[mask]

                # Count filtered detections robustly
                try:
                    count = len(filtered_boxes)
                except Exception:
                    # Fallback for versions where __len__ might not be implemented
                    count = int(getattr(getattr(filtered_boxes, "data", None), "shape", [0])[0])

                # If any filtered boxes remain, update plot and write labels
                if count > 0:
                    # Override boxes for plotting (optional)
                    yolo_result.boxes = filtered_boxes
                    filtered_annotated = yolo_result.plot()
                    Image.fromarray(filtered_annotated).save(
                        os.path.join(output_image_folder, f"annotated_{filename}")
                    )

                    # Write filtered labels (ensure .txt extension)
                    label_path = os.path.join(
                        label_output_folder, f"{os.path.splitext(filename)[0]}.txt"
                    )
                    with open(label_path, "w") as f_out:
                        for cls, xywh in zip(filtered_boxes.cls, filtered_boxes.xywh):
                            cls = int(cls.item())
                            x_center, y_center, width, height = xywh.tolist()

                            # Normalize
                            x_center /= img.width
                            y_center /= img.height
                            width /= img.width
                            height /= img.height

                            f_out.write(
                                f"{cls} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"
                            )
            else:
                # boxes present but zero count or missing conf; treat as no detections
                count = 0
        else:
            # No boxes at all (YOLO returned no detections)
            count = 0

        # --- Safe route selection ---
        lat = exif.get("latitude")
        lon = exif.get("longitude")
        has_gps = (lat is not None) and (lon is not None)

        if has_gps:
            route = match_route(lat, lon, route_bounds)
        else:
            route = "No GPS"

        # Always append a row so the image contributes to coverage
        results.append({
            "filename": filename,
            "litter_count": count,
            "timestamp": exif.get("timestamp"),
            "latitude": lat,
            "longitude": lon,
            "route": route
        })

    
    except Exception as e:
            # Log and continue to the next image; don't abort the whole run
            print(f"Error processing {filename}: {e}")
            continue



# ... inside the image processing loop ...

# try:
#     img = Image.open(image_path).convert("RGB")
#     exif = extract_exif(image_path)
#     yolo_result = model(img)[0]

#     # --- annotate original detections (optional) ---
#     annotated_img = yolo_result.plot()
#     annotated_pil = Image.fromarray(annotated_img)
#     annotated_pil.save(os.path.join(output_image_folder, f"annotated_{filename}"))

#     confidence_threshold = 0.01
#     boxes = yolo_result.boxes

#     # Default values
#     filtered_boxes = None
#     count = 0

#     if boxes is not None and boxes.shape[0] > 0:
#         # Filter by confidence
#         mask = boxes.conf >= confidence_threshold
#         filtered_boxes = boxes[mask]

#         # If you want the filtered annotations
#         yolo_result.boxes = filtered_boxes
#         annotated_img = yolo_result.plot()
#         annotated_pil = Image.fromarray(annotated_img)
#         annotated_pil.save(os.path.join(output_image_folder, f"annotated_{filename}"))

#         # Write filtered labels
#         label_path = os.path.join(label_output_folder, f"{os.path.splitext(filename)[0]}.txt")
#         with open(label_path, "w") as f_out:
#             for cls, xywh in zip(filtered_boxes.cls, filtered_boxes.xywh):
#                 cls = int(cls.item())
#                 x_center, y_center, width, height = xywh.tolist()
#                 # Normalize
#                 x_center /= img.width
#                 y_center /= img.height
#                 width /= img.width
#                 height /= img.height
#                 f_out.write(f"{cls} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

#         # Robust count
#         count = int(filtered_boxes.shape[0])

#     # --- Route selection ---
#     lat = exif.get("latitude")
#     lon = exif.get("longitude")
#     has_gps = (lat is not None) and (lon is not None)

#     if has_gps:
#         route = match_route(lat, lon, route_bounds)
#     else:
#         route = "No GPS"

#     results.append({
#         "filename": filename,
#         "litter_count": count,
#         "timestamp": exif.get("timestamp"),
#         "latitude": lat,
#         "longitude": lon,
#         "route": route
#     })

# except Exception as e:
#     print(f"Error processing {filename}: {e}")

 
# Save Results
df = pd.DataFrame(results) 

#Ward Spatial Join

gdf_wards = gpd.read_file(wards_shape_file)
if not gdf_wards.geometry.is_valid.all():
    gdf_wards["geometry"] = gdf_wards.buffer(0)

gdf_points = gpd.GeoDataFrame(
    df.copy(),
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"], crs = "EPSG:4326"),
    crs = "EPSG:4326")
    
valid_mask = gdf_points.geometry.notna()
gdf_valid = gdf_points.loc[valid_mask].copy()

if gdf_valid.crs != gdf_wards.crs:
    gdf_valid = gdf_valid.to_crs(gdf_wards.crs)

joined = gpd.sjoin(
    gdf_valid,
    gdf_wards[[WARD_FIELD, "geometry"]],
    how="left",
    predicate="within"
)
joined_single = joined.groupby(level=0)[WARD_FIELD].first().reindex(gdf_valid.index)

gdf_points.loc[valid_mask, WARD_FIELD] = joined_single.values

df[WARD_FIELD] = gdf_points[WARD_FIELD]

#Litter by distance calculation cont.

route_points_dict = (
    df.groupby('route')
    .apply(lambda g: list(zip(g['latitude'], g['longitude'])))
    .to_dict()
)

# --- Compute Distances ---
route_distances = {
    route: total_route_distance(points)
    for route, points in route_points_dict.items()
}

route_litter_sum = (
    df.groupby("route", dropna=False)["litter_count"]
    .sum(min_count=1)
    .to_dict()
)

phi_by_route = {}
for route in df["route"].dropna().unique():
    total_litter = route_litter_sum.get(route, np.nan)
    total_distance_m = route_distances.get(route, np.nan)
    total_distance = total_distance_m

    if pd.notna(total_litter) and pd.notna(total_distance) and total_distance > 0:
        phi_by_route[route] = total_litter / total_distance
    else:
        phi_by_route[route] = np.nan

df["phi"] = df["route"].map(phi_by_route)

df.to_csv(output_csv, index=False)
print(f"\n Done! Results saved to {output_csv}")

