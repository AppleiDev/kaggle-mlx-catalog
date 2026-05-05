#!/usr/bin/env python3
"""
Auto-update MLX Community Models Catalog on Kaggle.
Fetches all mlx-community models from HuggingFace, saves JSON, pushes new dataset version.

Run manually:  python3 /Users/denn/Kaggle/update_mlx_catalog.py
Scheduled via: ~/Library/LaunchAgents/com.denn.mlx-catalog-update.plist
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(SCRIPT_DIR, "mlx-models-dataset")
OUTPUT_FILE = os.path.join(DATASET_DIR, "mlx_community_models.json")
ROOT_COPY   = os.path.join(SCRIPT_DIR, "mlx_community_models.json")
LOG_FILE    = os.path.join(SCRIPT_DIR, "mlx_catalog_update.log")

HF_API      = "https://huggingface.co/api/models"
AUTHOR      = "mlx-community"
PAGE_SIZE   = 1000


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def fetch_all_models():
    models = []
    page = 0
    while True:
        url = f"{HF_API}?author={AUTHOR}&limit={PAGE_SIZE}&skip={page * PAGE_SIZE}&full=true&sort=lastModified&direction=-1"
        log(f"Fetching page {page + 1} (skip={page * PAGE_SIZE})...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mlx-catalog-updater/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                batch = json.loads(r.read())
        except urllib.error.HTTPError as e:
            log(f"HTTP error {e.code}: {e.reason}")
            sys.exit(1)
        except Exception as e:
            log(f"Fetch error: {e}")
            sys.exit(1)

        log(f"  Got {len(batch)} models (total so far: {len(models)})")
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.5)  # be polite to HF API

    return models


def push_to_kaggle():
    result = subprocess.run(
        ["kaggle", "datasets", "version",
         "-p", DATASET_DIR,
         "-m", f"Auto-update {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log(f"Kaggle push succeeded: {result.stdout.strip()}")
    else:
        log(f"Kaggle push failed: {result.stderr.strip()}")
        sys.exit(1)


def main():
    log("=== MLX Catalog Update Started ===")

    existing_count = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
            existing_count = len(existing)
    log(f"Existing model count: {existing_count}")

    models = fetch_all_models()
    log(f"Fetched {len(models)} models from HuggingFace")

    if len(models) == 0:
        log("No models returned — aborting to avoid overwriting good data")
        sys.exit(1)

    os.makedirs(DATASET_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(models, f, indent=2, default=str)
    log(f"Saved to {OUTPUT_FILE}")

    with open(ROOT_COPY, "w") as f:
        json.dump(models, f, indent=2, default=str)
    log(f"Synced root copy {ROOT_COPY}")

    delta = len(models) - existing_count
    log(f"Delta: {'+' if delta >= 0 else ''}{delta} models")

    push_to_kaggle()
    log("=== Update Complete ===\n")


if __name__ == "__main__":
    main()
