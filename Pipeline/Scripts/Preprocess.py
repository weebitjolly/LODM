def pre_process():

    import os
    import shutil
    import exifread
    import cv2
    from pathlib import Path
    from PIL import Image, ImageOps
    import numpy as np
    import re

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

    # === CONFIG ===
    
    from dotenv import load_dotenv
    import os
    load_dotenv()
    DEPLOYMENTS_ROOT = os.getenv("DEPLOYMENTS_ROOT")
    LATEST_DEPLOYMENT_PATH = get_latest_deployment_path(DEPLOYMENTS_ROOT)
    image_folder = str(
    LATEST_DEPLOYMENT_PATH /
    os.getenv("RAW_IMAGES_FOLDER")
    )

    duplicates_folder = os.path.join(
        image_folder,
        os.getenv("DUPLICATES_FOLDER")
    )

    intermediate_folder = os.path.join(
        image_folder,
        os.getenv("CROPPED_FOLDER")
    )

    output_folder = os.path.join(
        image_folder,
        os.getenv("PREPROCESSED_FOLDER")
    )

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
    def preprocess_image_with_exif(
            original_path, 
            cropped_path, 
            output_path,
            crop_left_percent=0.155891   # NEW: value like 0.10 for 10% left-crop
        ):
        """
        - Normalize orientation
        - Crop top/bottom by percentage
        - Crop left side by percentage (NEW)
        - Save cropped with EXIF preserved
        - Apply LAB-CLAHE (clipLimit=2.0) to L channel
        - Apply Gaussian blur (5x5)
        - Save final with EXIF preserved
        """

        # Step 1: Open original and normalize orientation
        with Image.open(original_path) as img:
            img = ImageOps.exif_transpose(img)
            exif_bytes = img.info.get("exif")

            width, height = img.size

            # Existing top/bottom cropping
            top_crop = int(height * CROP_TOP_PERCENT)
            bottom_crop = int(height * CROP_BOTTOM_PERCENT)

            #left crop
            left_crop = int(width * crop_left_percent)

            # Crop box: (left, top, right, bottom)
            cropped_img = img.crop((
                left_crop,                # left
                top_crop,                 # top
                width,                    # right (full width)
                height - bottom_crop      # bottom
            ))

            # Save cropped with EXIF
            save_kwargs = {}
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            cropped_img.save(cropped_path, **save_kwargs)

            # Convert for OpenCV processing
            cropped_arr = np.array(cropped_img)
            img_cv = cv2.cvtColor(cropped_arr, cv2.COLOR_RGB2BGR)

        # Step 2: CLAHE in LAB space
        lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        merged = cv2.merge((cl, a, b))
        clahe_img = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

        # Step 3: Gaussian blur
        blurred = cv2.GaussianBlur(clahe_img, (5, 5), 0)

        # Step 4: Save final with EXIF
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

    for filename in os.listdir(image_folder):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        filepath = os.path.join(image_folder, filename)
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