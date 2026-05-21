"""
fix_markdown_artifacts.py
Finds and fixes posts/pages that have ```html or ``` artifacts in content.
Checks: published posts, scheduled posts, published pages.
"""
import requests, base64, os, sys, re
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

WP_URL = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
creds = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def strip_markdown_fences(content: str) -> str:
    content = re.sub(r"```html?\s*\n?", "", content)
    content = re.sub(r"```\s*\n?", "", content)
    return content


def fetch_items(endpoint: str, statuses: list) -> list:
    items = []
    for status in statuses:
        page = 1
        while True:
            r = requests.get(f"{WP_URL}/wp-json/wp/v2/{endpoint}", headers=HDR,
                params={"per_page": 100, "page": page, "status": status,
                        "_fields": "id,slug,title,content"}, timeout=15)
            if not r.ok or not r.json():
                break
            batch = r.json()
            items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    return items


def check_and_fix(items: list, endpoint: str):
    fixed = 0
    for p in items:
        # Check both raw and rendered
        raw      = p["content"].get("raw", "")
        rendered = p["content"].get("rendered", "")
        combined = raw + rendered

        if "```" not in combined:
            continue

        pid   = p["id"]
        slug  = p.get("slug", "?")
        title = p["title"]["rendered"][:60]
        print(f"  [{pid}] /{slug}/ — {title}")

        # Show context
        for text in (raw, rendered):
            idx = text.find("```")
            if idx >= 0:
                print(f"    snippet: {text[max(0,idx-30):idx+80].strip()[:120]}")
                break

        # Fix the raw content
        source = raw if raw else rendered
        cleaned = strip_markdown_fences(source)

        r = requests.post(f"{WP_URL}/wp-json/wp/v2/{endpoint}/{pid}", headers=HDR,
            json={"content": cleaned}, timeout=15)
        if r.ok:
            print(f"    FIXED")
            fixed += 1
        else:
            print(f"    ERROR {r.status_code}: {r.text[:100]}")
    return fixed


def main():
    total_fixed = 0

    print("=== POSTS (publish + future) ===")
    posts = fetch_items("posts", ["publish", "future"])
    print(f"Found {len(posts)} posts")
    total_fixed += check_and_fix(posts, "posts")

    print()
    print("=== PAGES (publish) ===")
    pages = fetch_items("pages", ["publish"])
    print(f"Found {len(pages)} pages")
    total_fixed += check_and_fix(pages, "pages")

    print()
    print(f"Total fixed: {total_fixed}")


if __name__ == "__main__":
    main()
