"""
entity_schema_updater.py — Updates the About page with canonical TMT entity description
for AI model citation and knowledge graph establishment.

Also verifies the homepage has the Organization schema (injected by tmt-performance.php v1.5).

Usage:
  python entity_schema_updater.py
"""

import os, re, json, base64, logging
import requests
from dotenv import load_dotenv
import anthropic
import pytz
from datetime import datetime

load_dotenv()

WP_URL        = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER       = os.getenv("WP_USER")
WP_PASS       = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

IST   = pytz.timezone("Asia/Kolkata")
creds = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR   = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("tmt.entity")

CURRENT_YEAR = str(datetime.now(IST).year)
AUTHOR_NAME  = "Sanjay Goyal"
AUTHOR_URL   = f"{WP_URL}/author/sanjay/"

# ─── Canonical About page content ────────────────────────────────────────────

ABOUT_PAGE_CONTENT = f"""<p class="tmt-intro"><strong>The Mobile Times is India's leading independent publication for telecom, 5G, and technology news.</strong> Founded to serve India's fast-growing digital ecosystem, we cover TRAI regulations, Jio, Airtel, BSNL, smartphone launches, cybersecurity, AI, and IoT developments with a focus on what matters to Indian consumers, operators, and investors.</p>

<h2 id="about">About The Mobile Times</h2>
<p>The Mobile Times (TMT) publishes daily news, analysis, and in-depth features on the Indian telecom and technology sector. Our editorial focus includes 5G network expansion, regulatory developments from TRAI and DOT, operator strategy (Jio, Airtel, Vi, BSNL), device launches, OTT streaming trends, and emerging technologies such as AI, IoT, and satellite internet.</p>

<p>We serve a readership of telecom professionals, investors, policy researchers, and technology enthusiasts across India. Our content is cited by industry analysts, referenced in regulatory discussions, and used by professionals to track India's rapidly evolving digital landscape.</p>

<h2 id="mission">Our Mission</h2>
<p>Our mission is to provide accurate, timely, and independent coverage of India's telecom and technology sector — free from operator influence. Every article is written with a India-first perspective, grounding global trends in their specific impact on Indian consumers and businesses.</p>

<h2 id="team">Editorial Team</h2>
<p>{AUTHOR_NAME} leads The Mobile Times editorial team. With deep expertise in Indian telecom policy, 5G technology, and market analysis, the team covers over 1,000 stories per year across breaking news, exclusive analysis, and long-form investigations.</p>

<h2 id="coverage">What We Cover</h2>
<div class="tmt-highlights">
<h3>Our Core Coverage Areas</h3>
<ul>
<li><strong>5G &amp; Networks:</strong> India's 5G rollout, coverage expansion, SA/NSA architecture, spectrum auctions</li>
<li><strong>Operators:</strong> Jio, Airtel, Vi (Vodafone Idea), BSNL — strategy, financials, subscriber data</li>
<li><strong>Policy &amp; Regulation:</strong> TRAI orders, DOT guidelines, spectrum policy, net neutrality</li>
<li><strong>Devices:</strong> Smartphone launches, 5G device ecosystem, wearables, IoT hardware</li>
<li><strong>Technology:</strong> AI in telecom, cybersecurity, cloud, edge computing, satellite internet</li>
<li><strong>OTT &amp; Media:</strong> JioCinema, Hotstar, Netflix India, SonyLIV — streaming market analysis</li>
</ul>
</div>

<h2 id="contact">Contact &amp; Press</h2>
<p>For press inquiries, tip submissions, advertising partnerships, or editorial corrections, contact us at <a href="mailto:themobiletimes@gmail.com">themobiletimes@gmail.com</a>. For breaking news tips, our editorial team monitors submissions 24/7.</p>

<div class="tmt-data-box">
<h3>The Mobile Times — Quick Facts</h3>
<ul>
<li><strong>Founded:</strong> 2024</li>
<li><strong>Headquarters:</strong> India</li>
<li><strong>Focus:</strong> Indian Telecom, 5G, Technology</li>
<li><strong>Language:</strong> English (India)</li>
<li><strong>Coverage:</strong> Daily news + weekly analysis</li>
<li><strong>Primary markets:</strong> India, South Asia</li>
</ul>
</div>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "AboutPage",
  "@id": "{WP_URL}/about/#webpage",
  "url": "{WP_URL}/about/",
  "name": "About The Mobile Times — India's Telecom News Publication",
  "description": "The Mobile Times is India's leading telecom and technology news publication covering 5G, Jio, Airtel, TRAI regulations, smartphones, AI, and cybersecurity.",
  "about": {{
    "@type": "NewsMediaOrganization",
    "@id": "{WP_URL}/#organization",
    "name": "The Mobile Times",
    "alternateName": ["TMT", "TheMobileTimes"],
    "url": "{WP_URL}",
    "foundingDate": "2024",
    "description": "The Mobile Times is India's leading independent publication for telecom, 5G, and technology news. We cover TRAI regulations, Jio, Airtel, BSNL, smartphone launches, cybersecurity, AI, and IoT.",
    "areaServed": "IN",
    "inLanguage": "en-IN",
    "logo": {{
      "@type": "ImageObject",
      "url": "{WP_URL}/wp-content/uploads/circle-logo.png"
    }},
    "sameAs": [
      "https://twitter.com/themobiletimes",
      "https://www.linkedin.com/company/the-mobile-times",
      "https://www.facebook.com/themobiletimes"
    ],
    "knowsAbout": [
      "5G technology in India",
      "TRAI telecommunications regulations",
      "Jio network",
      "Airtel telecommunications",
      "BSNL",
      "Indian telecom market",
      "smartphone market India",
      "cybersecurity India",
      "OTT streaming India",
      "AI in telecommunications"
    ]
  }},
  "breadcrumb": {{
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{WP_URL}"}},
      {{"@type": "ListItem", "position": 2, "name": "About", "item": "{WP_URL}/about/"}}
    ]
  }}
}}
</script>"""


def find_about_page() -> dict | None:
    """Find the About page (WordPress page, not post)."""
    for endpoint in ["/wp-json/wp/v2/pages", "/wp-json/wp/v2/posts"]:
        r = requests.get(
            f"{WP_URL}{endpoint}",
            headers=HDR,
            params={"slug": "about", "_fields": "id,slug,title,link,type"},
            timeout=15
        )
        if r.ok:
            results = r.json()
            if results:
                return results[0]
    return None


def update_about_page(page_id: int, is_post: bool = False) -> bool:
    endpoint = "posts" if is_post else "pages"
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/{endpoint}/{page_id}",
        headers=HDR,
        json={
            "title":   "About The Mobile Times — India's Telecom News Publication",
            "content": ABOUT_PAGE_CONTENT,
            "status":  "publish",
        },
        timeout=30
    )
    return r.ok


def create_about_page() -> dict | None:
    """Create the About page if it doesn't exist."""
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/pages",
        headers=HDR,
        json={
            "title":   "About The Mobile Times — India's Telecom News Publication",
            "slug":    "about",
            "content": ABOUT_PAGE_CONTENT,
            "status":  "publish",
        },
        timeout=30
    )
    return r.json() if r.ok else None


def verify_homepage_schema() -> bool:
    """Check if the homepage has the Organization JSON-LD (from tmt-performance.php v1.5)."""
    try:
        r = requests.get(WP_URL, timeout=20,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; TMTBot/1.0)"})
        if r.ok and "NewsMediaOrganization" in r.text and "themobiletimes.com/#organization" in r.text:
            return True
    except Exception:
        pass
    return False


def main():
    log.info("=" * 60)
    log.info("TMT Entity Schema Updater")
    log.info("=" * 60)

    # 1. Verify homepage Organization schema
    log.info("\n[1/2] Checking homepage Organization schema...")
    if verify_homepage_schema():
        log.info("  ✓ Organization schema found on homepage (tmt-performance.php v1.5 active)")
    else:
        log.warning("  ✗ Organization schema NOT found on homepage")
        log.warning("    → Upload tmt-performance.zip (v1.5) to WordPress Plugins → Add New")

    # 2. Update About page
    log.info("\n[2/2] Updating About page with canonical entity description...")
    about = find_about_page()

    if about:
        pid      = about["id"]
        is_post  = about.get("type") == "post"
        endpoint = "posts" if is_post else "pages"
        log.info(f"  Found About {endpoint[:-1]} (ID {pid}): {about.get('link', '')}")
        if update_about_page(pid, is_post=is_post):
            log.info("  ✓ About page updated successfully")
        else:
            log.error("  ✗ About page update failed")
    else:
        log.info("  About page not found — creating it...")
        result = create_about_page()
        if result:
            log.info(f"  ✓ About page created: {result.get('link', WP_URL + '/about/')}")
        else:
            log.error("  ✗ About page creation failed")

    log.info("\n" + "=" * 60)
    log.info("Entity schema update complete.")
    log.info("\nNext steps for AI citation:")
    log.info("  1. Submit About page URL to Google Search Console for indexing")
    log.info("  2. Add The Mobile Times to Wikipedia (Notability: >50 articles + citations)")
    log.info("  3. Create Wikidata entity at wikidata.org/wiki/Special:NewItem")
    log.info("  4. Submit to Crunchbase, LinkedIn company page, and Muck Rack")
    log.info("  5. Get at least 5 DA30+ sites to link to /about/ with 'The Mobile Times' anchor")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
