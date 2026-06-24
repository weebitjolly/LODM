import os
import shutil
import exifread
import cv2
from PIL import Image, ImageOps
import numpy as np

# === CONFIG ===
input_folder = r"C:\Litter Production\Deployments\deployment_2\Raw Deployment Images" #right now these raw images run from the GoPro directly to the Data science computer
duplicates_folder = os.path.join(input_folder, "Duplicates")
intermediate_folder = os.path.join(input_folder, "Cropped")
output_folder = os.path.join(input_folder, "Preprocessed")

os.makedirs(duplicates_folder, exist_ok=True)
os.makedirs(intermediate_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# === Crop Settings (as % of image height) ===
CROP_TOP_PERCENT = 0.2963
CROP_BOTTOM_PERCENT = 0.1678

# === EXIF GPS Extraction (matches your first script's logic) ===
def extract_gps(filepath):
    """
    Returns (lat, lon) rounded to 5 decimals if present, else None.
    """
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f, details=False)

    gps_lat = tags.get('GPS GPSLatitude')
    gps_lon = tags.get('GPS GPSLongitude')
    gps_lat_ref = tags.get('GPS GPSLatitudeRef')
    gps_lon_ref = tags.get('GPS GPSLongitudeRef')

    def to_decimal(value):
        d, m, s = [float(x.num) / float(x.den) for x in value.values]
        return d + m / 60 + s / 3600

    if gps_lat and gps_lon and gps_lat_ref and gps_lon_ref:
        lat = to_decimal(gps_lat)
        if str(gps_lat_ref.values[0]).upper() == 'S':
            lat = -lat
        lon = to_decimal(gps_lon)
        if str(gps_lon_ref.values[0]).upper() == 'W':
            lon = -lon
        return round(lat, 5), round(lon, 5)

    return None

# === Preprocessing (crop + LAB CLAHE + GaussianBlur) with EXIF preserved ===
def preprocess_image_with_exif(original_path, cropped_path, output_path):
    """
    - Normalize orientation
    - Crop top/bottom by percentage
    - Save cropped with EXIF preserved
    - Apply LAB-CLAHE (clipLimit=2.0) to L channel
    - Apply Gaussian blur (5x5)
    - Save final with EXIF preserved
    """
    # Step 1: Open original and normalize orientation
    with Image.open(original_path) as img:
        img = ImageOps.exif_transpose(img)
        exif_bytes = img.info.get('exif')  # JPEG/TIFF: bytes; PNG typically None

        width, height = img.size
        top_crop = int(height * CROP_TOP_PERCENT)
        bottom_crop = int(height * CROP_BOTTOM_PERCENT)
        cropped_img = img.crop((0, top_crop, width, height - bottom_crop))

        # Save the cropped image with EXIF preserved
        save_kwargs = {}
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        cropped_img.save(cropped_path, **save_kwargs)

        # Convert cropped PIL image to OpenCV (BGR) for processing
        cropped_arr = np.array(cropped_img)  # RGB
        img_cv = cv2.cvtColor(cropped_arr, cv2.COLOR_RGB2BGR)  # BGR

    # Step 2: CLAHE on L channel (LAB) — aligns with your old script
    lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    merged = cv2.merge((cl, a, b))
    clahe_img = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    # Step 3: Gaussian blur (5x5) — aligns with your old script
    blurred = cv2.GaussianBlur(clahe_img, (5, 5), 0)

    # Step 4: Save final with EXIF preserved
    final_rgb = cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)
    final_pil = Image.fromarray(final_rgb)

    save_kwargs = {}
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_pil.save(output_path, **save_kwargs)

# === Main Processing with immediate duplicate handling (GPS-only) ===
seen_coords = set()
dup_count = 0
proc_count = 0

for filename in os.listdir(input_folder):
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue

    filepath = os.path.join(input_folder, filename)
    gps = extract_gps(filepath)

    if gps is None:
        print(f"⚠️ No GPS in {filename} — skipping (cannot deduplicate).")
        continue

    # GPS-only dedup (matches your first script)
    if gps in seen_coords:
        # Move duplicate immediately and skip processing
        dest = os.path.join(duplicates_folder, filename)
        # Collision-safe rename in duplicates folder
        if os.path.exists(dest):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(dest):
                dest = os.path.join(duplicates_folder, f"{base}_dup{i}{ext}")
                i += 1
        shutil.move(filepath, dest)
        dup_count += 1
        print(f"📂 Moved duplicate: {filename} -> {os.path.basename(dest)}")
        continue
    else:
        seen_coords.add(gps)

    # Paths for intermediate and final outputs
    cropped_path = os.path.join(intermediate_folder, filename)
    final_output_path = os.path.join(output_folder, filename)

    try:
        preprocess_image_with_exif(filepath, cropped_path, final_output_path)
        proc_count += 1
        print(f"✅ Cropped and preprocessed (EXIF preserved): {filename}")
    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")

print(f"\nSummary: {proc_count} unique processed, {dup_count} duplicates moved.")
print("🎉 All images cropped and preprocessed. Final images saved to 'Preprocessed' folder.")