"""
gsc_optimizer.py — Google Search Console SEO Optimizer

What it does:
  1. Pulls last 28 days of GSC data for themobiletimes.com
  2. Finds two types of opportunities:
       A) High impressions + low CTR  → meta description is weak, rewrite it
       B) Position 4-15              → almost page 1, nudge content/meta
  3. For each opportunity: fetches the actual queries people use, asks Claude
     Haiku to write a better meta description using those exact queries
  4. Pushes the new meta description to Rank Math via REST API

Setup (one-time):
  1. Go to console.cloud.google.com
  2. Create a project → Enable "Google Search Console API"
  3. IAM & Admin → Service Accounts → Create → download JSON key
  4. In Google Search Console → Settings → Users → Add the service account email
     with "Full" permission
  5. Save the JSON key as: e:\Projects\Clients\TMT\Automation\gsc-credentials.json
  6. Add to .env:  GSC_PROPERTY=https://themobiletimes.com/
"""

import os, sys, json, base64, re, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

WP_URL       = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER      = os.getenv("WP_USER")
WP_PASS      = os.getenv("WP_APP_PASS")
AI_KEY       = os.getenv("ANTHROPIC_API_KEY")
GSC_PROPERTY = os.getenv("GSC_PROPERTY", "https://themobiletimes.com/")
CREDS_FILE   = os.path.join(os.path.dirname(__file__), "gsc-credentials.json")

creds  = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
WP_HDR = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
ai     = anthropic.Anthropic(api_key=AI_KEY)

# Thresholds — tune these as the site grows
MIN_IMPRESSIONS_FOR_CTR_FIX = 50    # At least 50 impressions in 28 days
MAX_CTR_FOR_FIX             = 0.04  # CTR below 4% = needs better meta
MIN_POSITION_FOR_NUDGE      = 4.0   # Ranking below position 4
MAX_POSITION_FOR_NUDGE      = 15.0  # But not beyond position 15 (too far)
MAX_POSTS_TO_FIX            = 20    # Cap to avoid too many API calls


# ─── GSC Connection ───────────────────────────────────────────────────────────

def get_gsc_service():
    if not os.path.exists(CREDS_FILE):
        raise FileNotFoundError(
            f"GSC credentials not found at {CREDS_FILE}\n"
            "See setup instructions at the top of this file."
        )
    sa_creds = service_account.Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    return build("searchconsole", "v1", credentials=sa_creds, cache_discovery=False)


def fetch_page_data(service, days: int = 28) -> list[dict]:
    """Fetch per-page metrics: clicks, impressions, CTR, position."""
    end   = datetime.utcnow().date()
    start = end - timedelta(days=days)
    body  = {
        "startDate":  str(start),
        "endDate":    str(end),
        "dimensions": ["page"],
        "rowLimit":   500,
    }
    resp  = service.searchanalytics().query(siteUrl=GSC_PROPERTY, body=body).execute()
    return resp.get("rows", [])


def fetch_queries_for_page(service, page_url: str, days: int = 28) -> list[dict]:
    """Fetch top queries driving traffic to a specific page."""
    end   = datetime.utcnow().date()
    start = end - timedelta(days=days)
    body  = {
        "startDate":       str(start),
        "endDate":         str(end),
        "dimensions":      ["query"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension":  "page",
                "operator":   "equals",
                "expression": page_url,
            }]
        }],
        "rowLimit": 10,
    }
    resp  = service.searchanalytics().query(siteUrl=GSC_PROPERTY, body=body).execute()
    return resp.get("rows", [])


# ─── WordPress Helpers ────────────────────────────────────────────────────────

def get_post_by_url(page_url: str) -> dict | None:
    """Find a WordPress post by its URL slug."""
    slug = page_url.rstrip("/").split("/")[-1]
    r    = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", headers=WP_HDR,
               params={"slug": slug, "_fields": "id,slug,title,meta"}, timeout=15)
    if r.ok and r.json():
        return r.json()[0]
    return None


def get_current_meta_desc(post_id: int) -> str:
    """Fetch the current Rank Math meta description for a post."""
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", headers=WP_HDR,
            params={"_fields": "meta"}, timeout=15)
    if r.ok:
        return r.json().get("meta", {}).get("rank_math_description", "")
    return ""


def push_meta_description(post_id: int, new_desc: str) -> bool:
    """Push updated meta description to Rank Math."""
    r = requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta", headers=WP_HDR,
            json={"objectID": post_id, "objectType": "post",
                  "meta": {"rank_math_description": new_desc}},
            timeout=15)
    return r.ok and r.json().get("slug") is True


# ─── AI Rewrite ───────────────────────────────────────────────────────────────

def rewrite_meta_description(title: str, current_desc: str,
                              top_queries: list[str], ctr: float,
                              position: float) -> str:
    """Ask Claude Haiku to write a better meta description."""
    queries_str = "\n".join(f"  - {q}" for q in top_queries[:5]) or "  (no query data)"
    prompt = f"""You are an SEO expert for The Mobile Times — India's leading telecom news site.

This post is appearing in Google search but not getting enough clicks.

Post title: {title}
Current meta description: {current_desc or "(none set)"}
Current CTR: {round(ctr * 100, 1)}%  (target: above 5%)
Current avg position: {round(position, 1)}
Top queries people use to find this post:
{queries_str}

Write a NEW meta description that will get more clicks.
Rules:
- EXACTLY 140-155 characters (count carefully)
- Use the actual search queries naturally — match what people are searching
- Make it compelling: what will the reader gain? Include a number or insight if possible
- Do NOT start with "The Mobile Times", "Discover", or "Learn"
- Do NOT use clickbait

Respond with ONLY the meta description, nothing else."""

    msg = ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip().strip('"')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("Connecting to Google Search Console...")
    try:
        service = get_gsc_service()
    except FileNotFoundError as e:
        log.error(str(e))
        return

    log.info(f"Fetching page data for {GSC_PROPERTY} (last 28 days)...")
    rows = fetch_page_data(service)
    log.info(f"  {len(rows)} pages with data")

    # Find opportunities
    opportunities = []
    for row in rows:
        url         = row["keys"][0]
        clicks      = row["clicks"]
        impressions = row["impressions"]
        ctr         = row["ctr"]
        position    = row["position"]

        # Skip homepage and non-post URLs
        path = url.replace(WP_URL, "").replace(GSC_PROPERTY.rstrip("/"), "")
        if path in ("/", "", "/feed/") or "/category/" in path or "/tag/" in path:
            continue
        if "/author/" in path or "/page/" in path:
            continue

        is_low_ctr   = impressions >= MIN_IMPRESSIONS_FOR_CTR_FIX and ctr < MAX_CTR_FOR_FIX
        is_near_top  = MIN_POSITION_FOR_NUDGE <= position <= MAX_POSITION_FOR_NUDGE

        if is_low_ctr or is_near_top:
            reason = []
            if is_low_ctr:   reason.append(f"CTR {round(ctr*100,1)}% on {int(impressions)} impr")
            if is_near_top:  reason.append(f"pos {round(position,1)}")
            opportunities.append({
                "url":         url,
                "clicks":      clicks,
                "impressions": impressions,
                "ctr":         ctr,
                "position":    position,
                "reason":      " | ".join(reason),
            })

    # Sort by impressions descending — biggest wins first
    opportunities.sort(key=lambda x: x["impressions"], reverse=True)
    opportunities = opportunities[:MAX_POSTS_TO_FIX]

    log.info(f"\nFound {len(opportunities)} improvement opportunities")
    log.info("=" * 60)

    results = []
    for opp in opportunities:
        url      = opp["url"]
        log.info(f"\n{url}")
        log.info(f"  Reason: {opp['reason']}")

        # Get WordPress post
        post = get_post_by_url(url)
        if not post:
            log.warning("  No WP post found — skipping")
            continue

        pid   = post["id"]
        title = re.sub(r"<[^>]+>", "", post["title"]["rendered"])
        log.info(f"  Post [{pid}]: {title[:60]}")

        # Get top queries for this page
        query_rows  = fetch_queries_for_page(service, url)
        top_queries = [r["keys"][0] for r in query_rows]
        log.info(f"  Top queries: {top_queries[:3]}")

        # Get current meta desc
        current_desc = get_current_meta_desc(pid)
        log.info(f"  Current desc ({len(current_desc)} chars): {current_desc[:80]}...")

        # Rewrite with Claude
        new_desc = rewrite_meta_description(
            title, current_desc, top_queries, opp["ctr"], opp["position"]
        )
        log.info(f"  New desc ({len(new_desc)} chars): {new_desc[:80]}...")

        # Push to Rank Math
        ok = push_meta_description(pid, new_desc)
        status = "UPDATED" if ok else "FAILED"
        log.info(f"  {status}")

        results.append({
            "url":          url,
            "post_id":      pid,
            "title":        title,
            "impressions":  opp["impressions"],
            "ctr_before":   round(opp["ctr"] * 100, 2),
            "position":     round(opp["position"], 1),
            "top_queries":  top_queries[:3],
            "old_desc":     current_desc,
            "new_desc":     new_desc,
            "status":       status,
        })

    log.info("\n" + "=" * 60)
    updated = sum(1 for r in results if r["status"] == "UPDATED")
    log.info(f"Done. Updated {updated}/{len(results)} posts.")

    with open("gsc_optimizer_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log.info("Report saved to gsc_optimizer_report.json")


if __name__ == "__main__":
    main()
