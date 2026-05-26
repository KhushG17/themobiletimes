"""
seed_views.py — One-time script to seed random view counts on all existing posts.

Uses the tmt-admin-api views/seed endpoint which writes directly to the
Light Views Counter plugin's wp_lvc_post_views table.

Usage:
    python seed_views.py              # seed all posts that have no views yet
    python seed_views.py --force      # overwrite ALL posts, even ones with existing counts
"""

import os, sys, argparse, logging
import requests
from dotenv import load_dotenv

load_dotenv()

WP_URL     = os.getenv("WP_URL", "").rstrip("/")
TMT_SECRET = os.getenv("TMT_SECRET", "TMT2026xK9mSEO")

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def seed_all(force: bool = False):
    if not WP_URL:
        log.error("WP_URL not set. Add it to your .env file.")
        sys.exit(1)

    log.info(f"Seeding views on {WP_URL} (force={force}) ...")
    r = requests.post(
        f"{WP_URL}/wp-json/tmt/v1/views/seed",
        json={"secret": TMT_SECRET, "bulk": True, "force": force},
        timeout=120,
    )
    if not r.ok:
        log.error(f"Request failed: {r.status_code} — {r.text[:300]}")
        sys.exit(1)

    data = r.json()
    if not data.get("success"):
        log.error(f"API error: {data}")
        sys.exit(1)

    log.info(f"Done. Seeded {data['seeded']} of {data['total']} posts with random views (300–2000).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing view counts (default: skip posts already counted)")
    args = parser.parse_args()
    seed_all(force=args.force)
