"""
wp_design_audit.py — Read theme, active template, and article HTML structure
"""
import os, re, base64, requests
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR     = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

# ── Active theme ──────────────────────────────────────────────────────────────
print("=== ACTIVE THEME ===")
r = requests.get(f"{WP_URL}/wp-json/wp/v2/themes?status=active", headers=HDR, timeout=30)
if r.ok:
    themes = r.json()
    for t in themes:
        print(f"  Name:        {t.get('name', {}).get('rendered', t.get('name', '?'))}")
        print(f"  Slug:        {t.get('stylesheet', '?')}")
        print(f"  Template:    {t.get('template', '?')}")
        print(f"  Version:     {t.get('version', '?')}")
        print(f"  Description: {str(t.get('description', {}).get('rendered', t.get('description', '')))[:100]}")
else:
    print(f"  HTTP {r.status_code}")

# ── Get latest published post URL ─────────────────────────────────────────────
print("\n=== LATEST PUBLISHED POSTS ===")
r2 = requests.get(f"{WP_URL}/wp-json/wp/v2/posts?per_page=5&status=publish", headers=HDR, timeout=30)
posts = r2.json() if r2.ok else []
article_url = None
for p in posts:
    url  = p.get("link", "")
    title = p["title"]["rendered"]
    print(f"  {url}")
    print(f"  Title: {title[:70]}")
    print()
    if not article_url:
        article_url = url

# ── Fetch the article page HTML and analyse structure ─────────────────────────
if article_url:
    print(f"=== ARTICLE PAGE STRUCTURE ({article_url}) ===")
    try:
        resp = requests.get(article_url, timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        html = resp.text
        kb   = len(resp.content) / 1024

        print(f"  Page size: {kb:.0f} KB")
        print(f"  Server:    {resp.headers.get('Server','?')}")
        print(f"  Cache:     {resp.headers.get('X-LiteSpeed-Cache', resp.headers.get('x-litespeed-cache','?'))}")

        # Detect key classes and IDs used
        body_class = re.findall(r'<body[^>]+class=["\']([^"\']+)["\']', html)
        if body_class:
            print(f"\n  Body classes: {body_class[0][:120]}")

        # Article/post wrapper classes
        article_tags = re.findall(r'<article[^>]+class=["\']([^"\']+)["\']', html)
        for cls in article_tags[:3]:
            print(f"  Article class: {cls[:100]}")

        # Main content wrapper
        main_tags = re.findall(r'<main[^>]+class=["\']([^"\']+)["\']', html)
        for cls in main_tags[:2]:
            print(f"  Main class:    {cls[:100]}")

        # Post content div
        content_divs = re.findall(r'<div[^>]+class=["\']([^"\']*entry[^"\']*)["\']', html)
        for cls in content_divs[:3]:
            print(f"  Content div:   {cls[:100]}")

        # Elementor data
        elementor_sections = len(re.findall(r'elementor-section', html))
        elementor_widgets  = len(re.findall(r'elementor-widget-wrap', html))
        print(f"\n  Elementor sections: {elementor_sections}")
        print(f"  Elementor widgets:  {elementor_widgets}")

        # Check if our tmt-* classes are rendering
        tmt_classes = re.findall(r'class="(tmt-[^"]+)"', html)
        if tmt_classes:
            print(f"\n  TMT custom classes found:")
            for cls in set(tmt_classes):
                print(f"    .{cls}")
        else:
            print("\n  WARNING: No tmt-* classes found in article HTML")

        # Title and heading structure
        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
        print(f"\n  H1 tags: {len(h1s)}")
        for h in h1s[:2]:
            print(f"    {re.sub(r'<[^>]+>','',h).strip()[:80]}")
        print(f"  H2 tags: {len(h2s)}")

        # Featured image
        og_img = re.findall(r'og:image.*?content=["\']([^"\']+)["\']', html)
        if not og_img:
            og_img = re.findall(r'content=["\']([^"\']+\.jpg[^"\']*)["\']', html)
        if og_img:
            print(f"\n  Featured image: {og_img[0][:80]}")

        # Check fonts being used
        font_families = re.findall(r"font-family:\s*([^;\"'{}]+)", html)
        if font_families:
            unique_fonts = list(dict.fromkeys(f.strip() for f in font_families))[:8]
            print(f"\n  Fonts in use: {', '.join(unique_fonts)}")

        # Sidebar
        has_sidebar = "sidebar" in html.lower()
        print(f"\n  Has sidebar: {has_sidebar}")

        # Content width check
        widths = re.findall(r'max-width:\s*([\d]+px)', html)
        unique_widths = list(dict.fromkeys(widths))[:10]
        print(f"  Max-widths found: {unique_widths}")

        # Check for social share buttons
        share_indicators = ["share", "sharethis", "addtoany", "social-share"]
        found_share = [s for s in share_indicators if s in html.lower()]
        print(f"  Social share: {found_share if found_share else 'None found'}")

        # Check for related posts
        related = "related" in html.lower() or "you-may-also" in html.lower()
        print(f"  Related posts section: {related}")

        # Print raw snippet of post content area
        content_match = re.search(r'<div[^>]+class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)
        if content_match:
            snippet = re.sub(r'<[^>]+>', '', content_match.group(1))[:300].strip()
            print(f"\n  Content snippet: {snippet[:200]}")

    except Exception as e:
        print(f"  ERROR: {e}")

# ── Check homepage structure ──────────────────────────────────────────────────
print(f"\n=== HOMEPAGE STRUCTURE ===")
try:
    resp2 = requests.get(WP_URL, timeout=30,
        headers={"User-Agent": "Mozilla/5.0"})
    html2 = resp2.text
    kb2   = len(resp2.content) / 1024
    print(f"  Size: {kb2:.0f} KB")

    # Elementor data
    el_sections = len(re.findall(r'elementor-section', html2))
    el_widgets  = len(re.findall(r'elementor-widget-wrap', html2))
    el_columns  = len(re.findall(r'elementor-column', html2))
    print(f"  Elementor sections: {el_sections}")
    print(f"  Elementor columns:  {el_columns}")
    print(f"  Elementor widgets:  {el_widgets}")

    # Post card structure
    post_cards = re.findall(r'<article[^>]+class=["\']([^"\']+)["\']', html2)
    if post_cards:
        print(f"  Post card classes: {post_cards[0][:100]}")

    # Check what post listing classes exist
    listing_classes = re.findall(r'class="([^"]*post[^"]*)"', html2)[:5]
    for cls in listing_classes:
        print(f"  Post listing class: {cls[:80]}")

except Exception as e:
    print(f"  ERROR: {e}")

print("\nDesign audit complete.")
