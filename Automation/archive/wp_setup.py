"""
wp_setup.py — One-time WordPress foundation setup for The Mobile Times
Run this ONCE before starting the daily automation agent.

What it does:
  1. Fixes homepage Rank Math meta (title + description)
  2. Deletes rogue tags (main-breaking, main-launch)
  3. Ensures the 3 correct tags exist
  4. Adds SEO descriptions to all 25 categories
  5. Injects TMT article CSS via WordPress Customizer
  6. Adds performance code via custom plugin
  7. Triggers sitemap regeneration
  8. Pings Google + Bing with sitemap
"""

import os, sys, base64, json, requests
from dotenv import load_dotenv

load_dotenv()

WP_URL   = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER  = os.getenv("WP_USER")
WP_PASS  = os.getenv("WP_APP_PASS")

creds    = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS  = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def log(msg): print(f"  {msg}")
def ok(msg):  print(f"  ✅ {msg}")
def warn(msg):print(f"  ⚠️  {msg}")
def err(msg): print(f"  ❌ {msg}")


# ─── 1. HOMEPAGE META ────────────────────────────────────────────────────────

def fix_homepage_meta():
    print("\n[1] Fixing homepage Rank Math meta...")
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/pages?slug=home&per_page=5", headers=HEADERS)
    pages = r.json() if r.ok else []

    # Also try front page
    r2 = requests.get(f"{WP_URL}/wp-json/wp/v2/settings", headers=HEADERS)
    if r2.ok:
        settings = r2.json()
        page_on_front = settings.get("page_on_front", 0)
        if page_on_front:
            meta_payload = {
                "meta": {
                    "rank_math_title":       "India Telecom News, 5G & Tech Updates | The Mobile Times",
                    "rank_math_description": "India's leading telecom trade publication covering 5G, smartphones, AI, cybersecurity and telecom policy. Daily news and expert analysis since 2009.",
                }
            }
            r3 = requests.post(
                f"{WP_URL}/wp-json/wp/v2/pages/{page_on_front}",
                headers=HEADERS, json=meta_payload
            )
            if r3.ok:
                ok(f"Homepage meta fixed on page ID {page_on_front}")
            else:
                warn(f"Could not update page meta via REST ({r3.status_code}). May need Rank Math REST API enabled.")
                warn("Manual fix: WP Admin → Rank Math → General Settings → REST API → ON")
        else:
            warn("No static front page set. Homepage uses blog index — set meta via Rank Math Dashboard manually.")
    else:
        err(f"Could not fetch WP settings: {r2.status_code}")


# ─── 2. TAG CLEANUP ──────────────────────────────────────────────────────────

# Known rogue tag IDs from audit
ROGUE_TAG_IDS = [168, 170]  # main-breaking, main-launch

REQUIRED_TAGS = [
    {"name": "Trending",      "slug": "trending"},
    {"name": "Breaking News", "slug": "breaking-news"},
    {"name": "New Launch",    "slug": "new-launch"},
]

def fix_tags():
    print("\n[2] Fixing tags (delete rogues, ensure 3 correct tags exist)...")

    # Delete rogue tags
    for tag_id in ROGUE_TAG_IDS:
        r = requests.delete(f"{WP_URL}/wp-json/wp/v2/tags/{tag_id}?force=true", headers=HEADERS)
        if r.ok:
            ok(f"Deleted rogue tag ID {tag_id}")
        elif r.status_code == 404:
            log(f"Tag {tag_id} already gone")
        else:
            warn(f"Could not delete tag {tag_id}: {r.status_code}")

    # Fetch existing tags
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?per_page=50", headers=HEADERS)
    existing = {t["slug"]: t["id"] for t in r.json()} if r.ok else {}

    for tag in REQUIRED_TAGS:
        if tag["slug"] in existing:
            ok(f"Tag '{tag['slug']}' already exists (ID {existing[tag['slug']]})")
        else:
            r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", headers=HEADERS, json=tag)
            if r2.ok:
                ok(f"Created tag '{tag['slug']}' (ID {r2.json()['id']})")
            else:
                err(f"Failed to create tag '{tag['slug']}': {r2.status_code}")


# ─── 3. CATEGORY DESCRIPTIONS ────────────────────────────────────────────────

CATEGORY_DESCRIPTIONS = {
    "5g-networks": (160, "Stay ahead with the latest 5G network news in India. Covering spectrum auctions, tower rollouts, NR technology, fiber backhaul, and India's 5G leadership ambitions across Jio, Airtel, and BSNL."),
    "accessories-wearables": (151, "The latest in mobile accessories and wearables for India. Reviews, launches, and analysis of smartwatches, earbuds, fitness bands, chargers, and connected personal devices across all price segments."),
    "ai-machine-learning": (156, "AI and machine learning transforming India's tech landscape. Coverage of LLMs, generative AI, ML deployments in telecom, enterprise automation, ChatGPT developments, and India's AI policy push."),
    "ar-vr": (163, "Augmented and virtual reality innovation in India and globally. Tracking spatial computing, metaverse platforms, AR enterprise applications, VR gaming, and the next generation of immersive technology."),
    "case-studies": (143, "In-depth case studies from India's telecom and technology sector. Real-world implementations, digital transformation stories, network deployments, and enterprise technology success stories."),
    "cybersecurity": (155, "Critical cybersecurity news and analysis for India. Covering data breaches, hacking incidents, malware threats, VPN regulations, privacy laws, and enterprise security strategy across Indian businesses."),
    "data-analytics": (157, "Big data and analytics powering India's digital economy. Coverage of cloud analytics, data science trends, enterprise BI tools, open data initiatives, and data-driven decision-making across industries."),
    "devices-hardware": (129, "Complete coverage of mobile devices and hardware launches in India. Smartphones, tablets, routers, accessories, and network equipment — specs, prices, reviews, and availability."),
    "ev-smart-grids": (164, "Electric vehicles and smart grid technology reshaping India's energy future. EV charging infrastructure, smart grid deployments, energy tech startups, and the intersection of telecom and clean energy."),
    "exclusive": (121, "TMT Exclusive — original reporting, deep analysis, and insider scoops from The Mobile Times editorial team. Stories you won't find anywhere else on India's telecom and technology landscape."),
    "how-to-guides": (142, "Practical how-to guides for consumers and professionals in India's tech ecosystem. Step-by-step tutorials on mobile settings, network optimisation, app usage, security hardening, and more."),
    "industry-insights": (141, "Expert industry insights and strategic analysis from The Mobile Times. Opinion, commentary, and forward-looking perspectives on India's telecom, tech, and digital infrastructure sectors."),
    "industry-trends": (159, "Macro trends shaping India's technology and telecom industry. In-depth trend analysis across 5G, OTT, IoT, EV, AR/VR, and emerging sectors driving the next wave of digital growth."),
    "insights": (140, "The Mobile Times Insights — long-form analysis, how-to guides, case studies, and press releases for professionals in India's telecom and technology industry."),
    "internet-of-things": (165, "IoT and connected devices transforming industries in India. Smart home, Industrial IoT, M2M connectivity, connected agriculture, smart city deployments, and the policy landscape for connected India."),
    "market-trends": (123, "Market intelligence and business trends for India's telecom sector. Revenue data, M&A activity, market share analysis, funding rounds, and strategic moves by Jio, Airtel, BSNL, and global tech players."),
    "network-smart-devices": (152, "Routers, modems, mesh networks, and smart networking gear for Indian consumers and enterprises. Coverage of home networking, enterprise Wi-Fi, SD-WAN, and smart connectivity hardware."),
    "ott-streaming": (162, "India's booming OTT and streaming landscape. Tracking Netflix, JioCinema, Amazon Prime, Hotstar, Zee5, SonyLIV — content deals, subscriber data, pricing wars, and India-first strategies."),
    "policy-updates": (122, "Regulatory and policy developments shaping India's telecom industry. TRAI rulings, DOT spectrum decisions, government digital initiatives, licensing updates, and compliance requirements for operators."),
    "press-releases": (144, "Official press releases and announcements from India's leading telecom and technology companies. Product launches, partnerships, financial results, and corporate developments as they happen."),
    "smartphones-tablets": (150, "India's smartphone and tablet market — launch coverage, price analysis, spec comparisons, and buyer guides across premium, mid-range, and budget segments from Apple, Samsung, OnePlus, and more."),
    "softwares": (154, "Software, apps, and SaaS transforming India's digital economy. Enterprise software, consumer apps, OS updates, developer tools, and the Indian startup ecosystem building the next wave of tech products."),
    "tech-innovation": (161, "Breakthrough technology and innovation from India and the world. Startup launches, R&D milestones, emerging technologies, patents, and the entrepreneurs and engineers building India's tech future."),
    "technologies": (153, "Core technology coverage from The Mobile Times — software, cybersecurity, AI, and data analytics shaping how India connects, communicates, and computes in the digital age."),
}

def add_category_descriptions():
    print("\n[3] Adding SEO descriptions to all categories...")
    updated = 0
    for slug, (cat_id, description) in CATEGORY_DESCRIPTIONS.items():
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/categories/{cat_id}",
            headers=HEADERS,
            json={"description": description}
        )
        if r.ok:
            ok(f"{slug}")
            updated += 1
        else:
            err(f"{slug} failed: {r.status_code} — {r.text[:100]}")
    print(f"\n  {updated}/{len(CATEGORY_DESCRIPTIONS)} categories updated")


# ─── 4. TMT CSS ──────────────────────────────────────────────────────────────

TMT_CSS = """
/* ── TMT Article Styles ─────────────────────────────── */
.tmt-featured-image{margin:0 0 2rem;border-radius:8px;overflow:hidden}
.tmt-featured-image img{width:100%;height:auto;display:block}
.tmt-featured-image figcaption{font-size:12px;color:#888;padding:6px 10px;background:#f7f7f7;text-align:right}
.tmt-intro{font-size:1.15rem;line-height:1.75;border-left:4px solid #CC0000;padding-left:1.25rem;margin-bottom:2rem}
.tmt-highlights{background:#fff5f5;border:1px solid #ffb3b3;border-radius:8px;padding:1.25rem 1.5rem;margin:1.75rem 0}
.tmt-highlights h3{font-size:1rem;font-weight:700;color:#CC0000;margin:0 0 .75rem;text-transform:uppercase;letter-spacing:.04em}
.tmt-highlights ul{margin:0;padding-left:1.25rem}
.tmt-highlights ul li{margin-bottom:.4rem;font-size:.95rem;line-height:1.55}
.tmt-toc{background:#f8f9fa;border:1px solid #e0e0e0;border-radius:8px;padding:1.25rem 1.5rem;margin:1.75rem 0}
.tmt-toc h3{font-size:.95rem;font-weight:700;color:#333;margin:0 0 .75rem;text-transform:uppercase}
.tmt-toc ol{margin:0;padding-left:1.4rem}
.tmt-toc ol li a{color:#CC0000;text-decoration:none;font-weight:500}
.tmt-quote{border-top:3px solid #CC0000;border-bottom:3px solid #CC0000;margin:2rem 0;padding:1.25rem 1.5rem;font-size:1.12rem;font-style:italic;background:#fff9f9;line-height:1.65}
.tmt-data-box{background:#0A1628;color:#e0f0ff;border-radius:8px;padding:1.25rem 1.5rem;margin:1.75rem 0}
.tmt-data-box h3{font-size:.95rem;font-weight:700;color:#ff9999;margin:0 0 .75rem;text-transform:uppercase}
.tmt-data-box ul{margin:0;padding:0;list-style:none}
.tmt-data-box ul li{border-bottom:1px solid rgba(255,255,255,.08);padding:.45rem 0;font-size:.93rem}
.tmt-data-box ul li strong{color:#ff9999}
.tmt-verdict{background:#fff5f5;border:1px solid #ffb3b3;border-radius:8px;padding:1.25rem 1.5rem;font-weight:500;line-height:1.7}
.tmt-sources{font-size:.82rem;color:#888;border-top:1px solid #eee;padding-top:.75rem;margin-top:2rem}
.tmt-sources a{color:#CC0000;text-decoration:none;margin:0 4px}
.tmt-breaking-badge{background:#CC0000;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.tmt-launch-badge{background:#0A1628;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.tmt-trending-badge{background:#FF6B00;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.tmt-exclusive-badge{background:#6B21A8;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.entry-content h2{font-size:1.35rem;font-weight:700;margin:2rem 0 .75rem;padding-bottom:.4rem;border-bottom:2px solid #f0f0f0}
.entry-content a[href*="themobiletimes.com"]{color:#CC0000;font-weight:500}
"""

def inject_css():
    print("\n[4] Injecting TMT CSS via WordPress Customizer...")
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/settings",
        headers=HEADERS,
        json={"custom_css_post_id": -1}
    )

    # Try the custom CSS endpoint directly
    r2 = requests.get(f"{WP_URL}/wp-json/wp/v2/custom_css", headers=HEADERS)
    if r2.ok and r2.json():
        css_id = r2.json()[0]["id"]
        r3 = requests.post(
            f"{WP_URL}/wp-json/wp/v2/custom_css/{css_id}",
            headers=HEADERS,
            json={"content": TMT_CSS}
        )
        if r3.ok:
            ok("CSS updated via existing custom_css post")
            return

    # Create new custom CSS post
    r4 = requests.post(
        f"{WP_URL}/wp-json/wp/v2/custom_css",
        headers=HEADERS,
        json={"content": TMT_CSS, "status": "publish", "title": "tmt-styles"}
    )
    if r4.ok:
        ok("CSS injected as new custom_css post")
    else:
        warn(f"CSS injection via REST failed ({r4.status_code}). Add manually:")
        warn("WP Admin → Appearance → Customize → Additional CSS → paste TMT_CSS")


# ─── 5. PERFORMANCE PLUGIN ───────────────────────────────────────────────────

PERF_PLUGIN_CODE = '''<?php
/**
 * Plugin Name: TMT Performance & Auto-Unsticky
 * Description: Removes emoji scripts, strips query strings, auto-removes sticky from posts older than 24h.
 * Version: 1.0
 */
if (!defined("ABSPATH")) exit;

// Remove emoji scripts (~15KB saved per page)
remove_action("wp_head",         "print_emoji_detection_script", 7);
remove_action("wp_print_styles", "print_emoji_styles");
remove_action("admin_print_scripts", "print_emoji_detection_script");
remove_action("admin_print_styles",  "print_emoji_styles");

// Strip query strings from static assets
function tmt_remove_query_strings($src) {
    if (strpos($src, "?ver=")) $src = remove_query_arg("ver", $src);
    return $src;
}
add_filter("style_loader_src",  "tmt_remove_query_strings", 10, 2);
add_filter("script_loader_src", "tmt_remove_query_strings", 10, 2);

// Auto-remove sticky flag from posts older than 24 hours
add_action("wp", "tmt_unsticky_old_posts");
function tmt_unsticky_old_posts() {
    $sticky_ids = get_option("sticky_posts");
    if (empty($sticky_ids)) return;
    foreach ($sticky_ids as $post_id) {
        $post_date = get_post_field("post_date", $post_id);
        if (strtotime($post_date) < strtotime("-24 hours")) {
            unstick_post($post_id);
        }
    }
}

// Disable XML-RPC (security)
add_filter("xmlrpc_enabled", "__return_false");

// Remove unnecessary header tags
remove_action("wp_head", "wp_generator");
remove_action("wp_head", "wlwmanifest_link");
remove_action("wp_head", "rsd_link");
'''

def install_performance_plugin():
    print("\n[5] Installing TMT performance plugin via WP REST API...")

    # Upload plugin as a file via the plugins endpoint
    plugin_content = PERF_PLUGIN_CODE.encode("utf-8")

    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tmt-performance/tmt-performance.php", PERF_PLUGIN_CODE)
    buf.seek(0)

    upload_headers = {
        "Authorization": f"Basic {creds}",
        "Content-Disposition": "attachment; filename=tmt-performance.zip",
        "Content-Type": "application/zip",
    }
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/plugins",
        headers=upload_headers,
        data=buf.read()
    )
    if r.ok:
        plugin_slug = r.json().get("plugin", "")
        # Activate it
        r2 = requests.put(
            f"{WP_URL}/wp-json/wp/v2/plugins/{plugin_slug}",
            headers=HEADERS,
            json={"status": "active"}
        )
        ok("TMT performance plugin installed and activated") if r2.ok else warn("Installed but activation failed — activate manually in WP Admin → Plugins")
    else:
        warn(f"Plugin upload failed ({r.status_code}). Manual install needed.")
        warn("Save this file as tmt-performance.php inside wp-content/plugins/tmt-performance/ and activate.")


# ─── 6. SITEMAP REGENERATION + PING ──────────────────────────────────────────

def fix_sitemap():
    print("\n[6] Regenerating sitemap and pinging search engines...")

    # Trigger Rank Math sitemap regeneration
    r = requests.get(
        f"{WP_URL}/wp-json/rankmath/v1/sitemap/regenerate",
        headers=HEADERS
    )
    if r.ok:
        ok("Rank Math sitemap regenerated")
    else:
        # Try alternate endpoint
        r2 = requests.delete(
            f"{WP_URL}/wp-json/rankmath/v1/sitemap/cache",
            headers=HEADERS
        )
        if r2.ok:
            ok("Rank Math sitemap cache cleared")
        else:
            warn("Sitemap regeneration via REST not available — go to: WP Admin → Rank Math → Sitemap → Save Changes (force regeneration)")

    # Verify sitemap is accessible
    r3 = requests.get(f"{WP_URL}/sitemap.xml", timeout=10)
    if r3.status_code == 200:
        ok(f"sitemap.xml is live ({len(r3.content)} bytes)")
    else:
        err(f"sitemap.xml still returning {r3.status_code} — needs manual fix in WP Admin")

    # Ping Google
    try:
        r4 = requests.get(
            "https://www.google.com/ping",
            params={"sitemap": f"{WP_URL}/sitemap.xml"},
            timeout=10
        )
        ok(f"Google sitemap ping: {r4.status_code}")
    except Exception as e:
        warn(f"Google ping failed: {e}")

    # Ping Bing (IndexNow)
    try:
        r5 = requests.get(
            "https://www.bing.com/indexnow",
            params={"url": WP_URL, "key": "tmt-indexnow-key"},
            timeout=10
        )
        ok(f"Bing IndexNow ping: {r5.status_code}")
    except Exception as e:
        warn(f"Bing ping failed: {e}")


# ─── 7. SCHEMA — ORGANIZATION + WEBSITE ──────────────────────────────────────

ORG_SCHEMA = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "NewsMediaOrganization",
            "@id": "https://themobiletimes.com/#organization",
            "name": "The Mobile Times",
            "url": "https://themobiletimes.com",
            "logo": {
                "@type": "ImageObject",
                "url": "https://themobiletimes.com/wp-content/uploads/circle-logo.png",
                "width": 512,
                "height": 512
            },
            "sameAs": [
                "https://x.com/themobile_times",
                "https://www.linkedin.com/company/themobiletimes",
                "https://www.instagram.com/themobiletimes",
                "https://www.facebook.com/themobiletime"
            ],
            "foundingDate": "2009",
            "description": "India's leading telecom trade publication covering 5G, smartphones, AI, cybersecurity and telecom policy.",
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "IN",
                "addressLocality": "Jaipur"
            },
            "publishingPrinciples": "https://themobiletimes.com/about/",
            "masthead": "https://themobiletimes.com/about/"
        },
        {
            "@type": "WebSite",
            "@id": "https://themobiletimes.com/#website",
            "url": "https://themobiletimes.com",
            "name": "The Mobile Times",
            "publisher": {"@id": "https://themobiletimes.com/#organization"},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": "https://themobiletimes.com/?s={search_term_string}"
                },
                "query-input": "required name=search_term_string"
            }
        }
    ]
}

SCHEMA_PLUGIN_CODE = f'''<?php
/**
 * Plugin Name: TMT Global Schema
 * Description: Injects Organization + WebSite JSON-LD schema on every page.
 * Version: 1.0
 */
if (!defined("ABSPATH")) exit;

add_action("wp_head", "tmt_inject_global_schema", 1);
function tmt_inject_global_schema() {{
    $schema = {json.dumps(ORG_SCHEMA, ensure_ascii=False, indent=2)};
    echo "<script type=\\"application/ld+json\\">" . json_encode($schema) . "</script>\\n";
}}
'''

def install_schema_plugin():
    print("\n[7] Installing TMT global schema plugin...")
    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tmt-schema/tmt-schema.php", SCHEMA_PLUGIN_CODE)
    buf.seek(0)

    upload_headers = {
        "Authorization": f"Basic {creds}",
        "Content-Disposition": "attachment; filename=tmt-schema.zip",
        "Content-Type": "application/zip",
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/plugins", headers=upload_headers, data=buf.read())
    if r.ok:
        plugin_slug = r.json().get("plugin", "")
        r2 = requests.put(
            f"{WP_URL}/wp-json/wp/v2/plugins/{plugin_slug}",
            headers=HEADERS, json={"status": "active"}
        )
        ok("Schema plugin installed and activated") if r2.ok else warn("Schema plugin installed but needs manual activation")
    else:
        warn(f"Schema plugin upload failed ({r.status_code}) — see manual steps below")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  The Mobile Times — WordPress Foundation Setup")
    print("=" * 60)

    if not WP_USER or not WP_PASS:
        err("Missing WP_USER or WP_APP_PASS in .env — aborting")
        sys.exit(1)

    # Verify connection first
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/users/me", headers=HEADERS)
    if not r.ok:
        err(f"Cannot connect to WordPress ({r.status_code}). Check credentials.")
        sys.exit(1)
    ok(f"Connected as: {r.json().get('name', 'unknown')}")

    fix_homepage_meta()
    fix_tags()
    add_category_descriptions()
    inject_css()
    install_performance_plugin()
    install_schema_plugin()
    fix_sitemap()

    print("\n" + "=" * 60)
    print("  Setup complete.")
    print("\n  MANUAL STEPS STILL NEEDED:")
    print("  1. WP Admin → Rank Math → General Settings → REST API → ON")
    print("  2. WP Admin → Rank Math → Sitemap → Save Changes (if sitemap still 404)")
    print("  3. Submit sitemaps in Google Search Console:")
    print("     - https://themobiletimes.com/sitemap.xml")
    print("     - https://themobiletimes.com/news-sitemap.xml")
    print("=" * 60)


if __name__ == "__main__":
    main()
