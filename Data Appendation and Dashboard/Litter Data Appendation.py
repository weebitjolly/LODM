
import os
import re
from pathlib import Path
import pandas as pd

# --- Where your deployment folders live ---
DEPLOYMENTS_ROOT = r"C:\Litter Production\Deployments"

# --- Where your results live ---
INDIVIDUAL_DIR = r"K:\Data Science\KNB\Litter Master\Results\individual_results"
MASTER_PATH    = r"K:\Data Science\KNB\Litter Master\Results\litter_results_master.csv"

def get_latest_deployment_path(deployments_root: str) -> Path:
    """
    Return Path to latest 'deployment_<int>' under deployments_root.
    Raises ValueError if not found.
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
    _, latest_path = candidates[0]
    return latest_path

def main():
    # 1) Resolve latest deployment tag and the newest individual CSV path
    latest_path = get_latest_deployment_path(DEPLOYMENTS_ROOT)
    deployment_tag = latest_path.name                 # e.g., 'deployment_4'
    newest_individual = fr"{INDIVIDUAL_DIR}\litter_results_{deployment_tag}.csv"

    if not os.path.isfile(newest_individual):
        raise FileNotFoundError(
            f"Newest individual results not found:\n  {newest_individual}\n"
            f"Make sure the detection script wrote its output for {deployment_tag}."
        )

    # 2) Read newest individual results
    df_new = pd.read_csv(newest_individual)

    # 3) Read (or initialize) master
    if os.path.isfile(MASTER_PATH):
        df_master = pd.read_csv(MASTER_PATH)
        existing_rows = len(df_master)
    else:
        df_master = pd.DataFrame(columns=df_new.columns)  # initialize with same schema
        existing_rows = 0

    # 4) Append newest into master
    final_df = pd.concat([df_master, df_new], ignore_index=True)

    # 5) Normalize timestamp for the portal (same behavior you used earlier)
    #    - Input format appears as 'YYYY:MM:DD HH:MM:SS'
    #    - Non-parsable values become NaT (kept in master)
    parsed_ts = pd.to_datetime(final_df['timestamp'],
                               format='%Y:%m:%d %H:%M:%S',
                               errors='coerce')
    final_df['timestamp'] = parsed_ts.dt.strftime('%Y-%m-%dT%H:%M:%S.000')

    # Optional: de-duplicate (uncomment if you want to avoid repeats)
    # final_df = final_df.drop_duplicates(subset=["filename", "timestamp", "latitude", "longitude"], keep="last")

    # 6) Save back to master
    final_df.to_csv(MASTER_PATH, index=False)

    # 7) Summary
    print(f"Latest deployment: {deployment_tag}")
    print(f"Newest individual file: {newest_individual}")
    print(f"Master path: {MASTER_PATH}")
    print(f"Rows previously in master: {existing_rows}")
    print(f"Rows in newest individual: {len(df_new)}")
    print(f"Total rows in master after append: {len(final_df)}")
    print(f"Timestamps successfully parsed: {parsed_ts.notna().sum()}")
    print("\nPreview of first 5 rows (timestamp):")
    print(final_df[['timestamp']].head())

if __name__ == "__main__":
    main()
