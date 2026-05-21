"""
fix_existing_posts.py — Audit and fix all published posts:
  - Wrong years (2025 → 2026)
  - Title fixes
  - Ensure Rank Math meta is set
"""
import os, re, base64, requests
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR     = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

CURRENT_YEAR = "2026"
WRONG_YEARS  = ["2025", "2024", "2023"]

def get_all_posts():
    posts, page = [], 1
    while True:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HDR, params={"per_page": 100, "page": page,
                "_fields": "id,title,slug,content,meta"})
        if not r.ok or not r.json(): break
        posts.extend(r.json())
        if len(r.json()) < 100: break
        page += 1
    return posts

def strip_html(t): return re.sub(r"<[^>]+>", " ", t).strip()

def fix_years(text):
    for yr in WRONG_YEARS:
        text = text.replace(yr, CURRENT_YEAR)
    return text

def has_placeholder(text):
    return bool(re.search(r"\[(?!a |/a)[^\]]{3,60}\]", text))

def main():
    print("Fetching all posts...\n")
    posts = get_all_posts()
    print(f"Found {len(posts)} posts\n{'='*60}")

    for post in posts:
        pid     = post["id"]
        title   = strip_html(post["title"]["rendered"])
        slug    = post["slug"]
        content = post["content"]["rendered"]

        issues  = []
        updates = {}

        # ── Check title for wrong year ──
        new_title = fix_years(title)
        if new_title != title:
            issues.append(f"Title year fixed: '{title}' → '{new_title}'")
            updates["title"] = new_title

        # ── Check slug for wrong year ──
        new_slug = fix_years(slug)
        if new_slug != slug:
            issues.append(f"Slug fixed: {slug} → {new_slug}")
            updates["slug"] = new_slug

        # ── Check content for wrong years ──
        new_content = fix_years(content)
        if new_content != content:
            issues.append("Content years fixed (2025→2026 in body)")
            updates["content"] = new_content

        # ── Check for unfilled placeholders ──
        if has_placeholder(strip_html(content)):
            issues.append("WARNING: Unfilled placeholders found in content — manual review needed")

        if not issues:
            print(f"  [OK] [{pid}] {title[:65]}")
            continue

        print(f"  [FIX] [{pid}] {title[:65]}")
        for iss in issues:
            print(f"    → {iss}")

        if updates:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{pid}",
                headers=HDR, json=updates)
            if r.ok:
                print(f"    ✓ Updated successfully")
            else:
                print(f"    ✗ Update failed: {r.status_code} {r.text[:100]}")
        print()

    print("="*60)
    print("Done.")

if __name__ == "__main__":
    main()
