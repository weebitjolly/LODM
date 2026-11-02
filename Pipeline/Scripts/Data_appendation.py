def data_append_upload():

    import os
    import re
    from pathlib import Path
    import pandas as pd
    
    from dotenv import load_dotenv
    import os

    load_dotenv()

    # --- Where your deployment folders live ---
    DEPLOYMENTS_ROOT = os.getenv("DEPLOYMENTS_ROOT")

    # --- Where your results live ---
    INDIVIDUAL_DIR = os.getenv("RESULTS_OUTPUT_DIR")
    MASTER_PATH = os.getenv("MASTER_RESULTS_CSV")

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
                    num = int(m.group(1))
                    candidates.append((num, entry))

        if not candidates:
            raise ValueError(f"No 'deployment_<number>' folders found in: {deployments_root}")

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, latest_path = candidates[0]
        return latest_path

    # ------------------------------------------------------------
    #                MAIN EXECUTION NOW RUNS HERE
    # ------------------------------------------------------------

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
    df_master = pd.read_csv(MASTER_PATH)

    # Convert NEW timestamps only
    parsed_new = pd.to_datetime(
        df_new['timestamp'],
        format='%Y:%m:%d %H:%M:%S',
        errors='coerce'
    )

    df_new['timestamp'] = parsed_new.dt.strftime('%Y-%m-%dT%H:%M:%S.000')

    # Append to master
    final_df = pd.concat([df_master, df_new], ignore_index=True)


    # # 5) Normalize timestamp for the portal
    # parsed_ts = pd.to_datetime(
    #     final_df['timestamp'],
    #     format='%Y:%m:%d %H:%M:%S',
    #     errors='coerce'
    # )
    # final_df['timestamp'] = parsed_ts.dt.strftime('%Y-%m-%dT%H:%M:%S.000')

    # 6) Save back to master
    final_df.to_csv(MASTER_PATH, index=False)

    # 7) Summary
    print(f"Latest deployment: {deployment_tag}")
    print(f"Newest individual file: {newest_individual}")
    print(f"Master path: {MASTER_PATH}")
    print(f"Rows in newest individual: {len(df_new)}")
    print(f"Total rows in master after append: {len(final_df)}")
    print("\nPreview of first 5 rows (timestamp):")
    print(final_df[['timestamp']].head())
