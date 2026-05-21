import os, re, base64, requests, time
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR     = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
TIMEOUT = 45

def get(path, params=""):
    try:
        r = requests.get(f"{WP_URL}/wp-json/{path}{params}", headers=HDR, timeout=TIMEOUT)
        if r.ok:
            return r.json()
        print(f"  [HTTP {r.status_code}] {path}")
        return []
    except Exception as e:
        print(f"  [ERROR] {path}: {e}")
        return []

print("=" * 65)
print("  THE MOBILE TIMES — Full WordPress Audit")
print("=" * 65)

# ── Pages ──────────────────────────────────────────────────────────────────────
pages = get("wp/v2/pages", "?per_page=50&status=any")
print(f"\n=== PAGES ({len(pages)}) ===")
for p in pages:
    print(f"  [{p['status']:10}] ID:{p['id']:5}  /{p['slug']}/")
    print(f"               Title: {p['title']['rendered']}")

# ── Posts ──────────────────────────────────────────────────────────────────────
posts = get("wp/v2/posts", "?per_page=100&status=any")
statuses = Counter(p["status"] for p in posts)
print(f"\n=== POSTS SUMMARY ===")
for s, c in statuses.items():
    print(f"  {s}: {c}")

drafts = [p for p in posts if p["status"] == "draft"]
if drafts:
    print(f"\n  Drafts to review/delete:")
    for p in drafts:
        print(f"    ID:{p['id']}  {p['title']['rendered'][:70]}")

# ── Tags ───────────────────────────────────────────────────────────────────────
tags = get("wp/v2/tags", "?per_page=50")
print(f"\n=== TAGS ({len(tags)}) ===")
for t in tags:
    print(f"  ID:{t['id']:5}  {t['slug']:25}  {t['count']} posts")

# ── Categories ─────────────────────────────────────────────────────────────────
cats = get("wp/v2/categories", "?per_page=100")
used  = sorted([c for c in cats if c.get("count", 0) > 0],  key=lambda x: -x["count"])
empty = [c for c in cats if c.get("count", 0) == 0]
print(f"\n=== CATEGORIES IN USE ({len(used)}) ===")
for c in used:
    print(f"  ID:{c['id']:5}  {c['slug']:30}  {c['count']} posts")
print(f"\n=== EMPTY CATEGORIES ({len(empty)}) — safe to leave, don't affect speed ===")
for c in empty:
    print(f"  ID:{c['id']:5}  {c['slug']}")

# ── Plugins ───────────────────────────────────────────────────────────────────
plugins = get("wp/v2/plugins", "?per_page=100")
if plugins and isinstance(plugins, list):
    active   = [p for p in plugins if p.get("status") == "active"]
    inactive = [p for p in plugins if p.get("status") != "active"]
    print(f"\n=== PLUGINS ACTIVE ({len(active)}) ===")
    for p in active:
        print(f"  {p.get('name', p.get('plugin','?'))[:45]:45}  v{p.get('version','?')}")
    if inactive:
        print(f"\n=== PLUGINS INACTIVE ({len(inactive)}) — DELETE THESE ===")
        for p in inactive:
            print(f"  {p.get('name', p.get('plugin','?'))[:45]:45}  v{p.get('version','?')}")
else:
    print("\n=== PLUGINS ===")
    print("  (Need to check manually: WP Admin > Plugins)")

# ── Media count ───────────────────────────────────────────────────────────────
media = get("wp/v2/media", "?per_page=100")
total_size = sum(m.get("media_details", {}).get("filesize", 0) for m in media)
print(f"\n=== MEDIA LIBRARY ===")
print(f"  Items (first 100): {len(media)}")
print(f"  Size of first 100: {total_size/1024/1024:.1f} MB")

# ── Site speed + HTML analysis ────────────────────────────────────────────────
print(f"\n=== SITE SPEED & HEALTH ===")
try:
    t0   = time.time()
    resp = requests.get(WP_URL, timeout=40)
    ms   = (time.time() - t0) * 1000
    html = resp.text
    kb   = len(resp.content) / 1024

    server   = resp.headers.get("Server", "unknown")
    encoding = resp.headers.get("Content-Encoding", "none")
    ls_hit   = resp.headers.get("X-LiteSpeed-Cache", resp.headers.get("x-litespeed-cache", ""))
    cf_cache = resp.headers.get("CF-Cache-Status", "")

    print(f"  Load time:           {ms:.0f} ms")
    print(f"  HTML size:           {kb:.0f} KB")
    print(f"  Server:              {server}")
    print(f"  Compression:         {encoding}")
    print(f"  LiteSpeed cache hdr: {ls_hit or 'NOT SET — cache may be off'}")
    print(f"  Cloudflare:          {cf_cache or 'not detected'}")

    scripts  = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    styles   = re.findall(r'<link[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']stylesheet', html)
    inline_s = re.findall(r'<style[\s>]', html)
    fonts    = [s for s in scripts + styles if "fonts.googleapis" in s or "fonts.gstatic" in s]
    emoji    = "wp-emoji" in html
    elementor_on = "elementor" in html.lower()

    print(f"\n  Script files loaded: {len(scripts)}")
    print(f"  CSS files loaded:    {len(styles)}")
    print(f"  Inline <style> blks: {len(inline_s)}")
    print(f"  Google Fonts calls:  {len(fonts)}")
    print(f"  Emoji JS (slow):     {'YES — should be OFF' if emoji else 'Off (good)'}")
    print(f"  Elementor detected:  {'YES' if elementor_on else 'No'}")

    # Speed verdict
    print(f"\n  Speed verdict: ", end="")
    if ms < 1500:
        print("FAST (under 1.5s)")
    elif ms < 3000:
        print("MODERATE (1.5–3s) — room to improve")
    elif ms < 5000:
        print("SLOW (3–5s) — needs optimisation")
    else:
        print("VERY SLOW (5s+) — critical fix needed")

    print(f"\n=== ALL SCRIPTS LOADED ON HOMEPAGE ===")
    for src in scripts:
        short = src.split("/wp-content/")[-1] if "/wp-content/" in src else src
        print(f"  {short[:85]}")

    print(f"\n=== ALL STYLESHEETS LOADED ON HOMEPAGE ===")
    for href in styles:
        short = href.split("/wp-content/")[-1] if "/wp-content/" in href else href
        print(f"  {short[:85]}")

except Exception as e:
    print(f"  ERROR loading homepage: {e}")

# ── WP Settings ───────────────────────────────────────────────────────────────
print(f"\n=== SITE SETTINGS ===")
try:
    rs = requests.get(f"{WP_URL}/wp-json/wp/v2/settings", headers=HDR, timeout=30)
    if rs.ok:
        s = rs.json()
        print(f"  Site title:     {s.get('title','?')}")
        print(f"  Tagline:        {s.get('description','?')}")
        print(f"  URL:            {s.get('url','?')}")
        print(f"  Timezone:       {s.get('timezone_string','?')}")
        print(f"  Posts per page: {s.get('posts_per_page','?')}")
        print(f"  Default cat:    {s.get('default_category','?')}")
except Exception as e:
    print(f"  {e}")

print("\n" + "=" * 65)
print("  Audit complete.")
print("=" * 65)
