"""
pillar_page_creator.py — Creates / updates 10 evergreen pillar pages for AI search engine citation.

These pages are long-form (1500–1800 words), fact-dense, and structured to be cited by
ChatGPT, Perplexity, Gemini, and Google AI Overviews when answering Indian telecom questions.

Usage:
  python pillar_page_creator.py --create-all     # Create/update all 10 pillar pages
  python pillar_page_creator.py --create "5G"    # Create/update one page by keyword
  python pillar_page_creator.py --list            # List existing pillar pages
"""

import os, re, json, base64, sys, argparse, logging
from datetime import datetime
import requests
import anthropic
from dotenv import load_dotenv
import pytz

load_dotenv()

WP_URL        = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER       = os.getenv("WP_USER")
WP_PASS       = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

IST   = pytz.timezone("Asia/Kolkata")
creds = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR   = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("tmt_pillars.log", encoding="utf-8")]
)
log = logging.getLogger("tmt.pillars")

AUTHOR_NAME = "Sanjay Goyal"
AUTHOR_URL  = "https://themobiletimes.com/author/sanjay/"
CURRENT_YEAR = str(datetime.now(IST).year)

# ─── 10 Pillar Page Definitions ──────────────────────────────────────────────
PILLAR_PAGES = [
    {
        "keyword":    "5G India",
        "title":      f"5G in India: Complete Guide to Coverage, Speed and Operators ({CURRENT_YEAR})",
        "slug":       f"5g-india-guide-{CURRENT_YEAR}",
        "category":   "5g-networks",
        "cat_id":     160,
        "focus_kw":   "5G India",
        "description": "Comprehensive guide to 5G coverage, speeds, operators (Jio, Airtel, BSNL) and rollout status across India in 2026.",
        "intent":      "Covers: coverage map, speeds by city, Jio vs Airtel 5G comparison, price plans, VoNR, SA vs NSA, rural rollout timeline, what 5G means for consumers.",
    },
    {
        "keyword":    "Jio vs Airtel",
        "title":      f"Jio vs Airtel {CURRENT_YEAR}: India's Telecom Battle — Plans, Speed and Coverage Compared",
        "slug":       f"jio-vs-airtel-{CURRENT_YEAR}-comparison",
        "category":   "market-trends",
        "cat_id":     123,
        "focus_kw":   "Jio vs Airtel",
        "description": f"Detailed {CURRENT_YEAR} comparison of Jio and Airtel — prepaid/postpaid plans, 5G speeds, network coverage, OTT bundles and subscriber numbers.",
        "intent":      "Covers: subscriber count, revenue, ARPU, 5G coverage comparison, plan pricing, OTT bundles, enterprise vs consumer, Vi as third player, who wins in rural India.",
    },
    {
        "keyword":    "TRAI regulations",
        "title":      f"TRAI Regulations {CURRENT_YEAR}: India's Telecom Regulator — Powers, Rules and Latest Orders",
        "slug":       f"trai-regulations-india-{CURRENT_YEAR}",
        "category":   "policy-updates",
        "cat_id":     122,
        "focus_kw":   "TRAI regulations",
        "description": f"Everything about TRAI regulations in {CURRENT_YEAR} — tariff orders, spectrum policy, OTT regulation debate, quality of service norms and consumer protections.",
        "intent":      "Covers: TRAI's mandate, key regulations of 2026, net neutrality, OTT regulation debate, spectrum auctions, DND registry, telecom tariff orders, consumer rights.",
    },
    {
        "keyword":    "cybersecurity India",
        "title":      f"Cybersecurity in India {CURRENT_YEAR}: Threats, Laws, CERT-In Rules and Best Practices",
        "slug":       f"cybersecurity-india-guide-{CURRENT_YEAR}",
        "category":   "cybersecurity",
        "cat_id":     155,
        "focus_kw":   "cybersecurity India",
        "description": f"Complete guide to cybersecurity in India {CURRENT_YEAR} — major threats, CERT-In reporting rules, DPDP Act compliance, telecom security and enterprise best practices.",
        "intent":      "Covers: cyber threat landscape 2026, CERT-In 6-hour reporting, DPDP Act, IT Act, telecom network security, ransomware trends in India, government initiatives.",
    },
    {
        "keyword":    "OTT streaming India",
        "title":      f"OTT Streaming in India {CURRENT_YEAR}: All Platforms Compared — Price, Content and Subscribers",
        "slug":       f"ott-streaming-india-{CURRENT_YEAR}",
        "category":   "ott-streaming",
        "cat_id":     162,
        "focus_kw":   "OTT streaming India",
        "description": f"OTT streaming India {CURRENT_YEAR}: Netflix, JioCinema, Hotstar, Amazon Prime, SonyLIV — subscriber counts, prices, content libraries and market share compared.",
        "intent":      "Covers: market size, platform comparison (Netflix/JioCinema/Hotstar/SonyLIV/ZEE5), content spend, subscriber numbers, bundling with telecom, regulation, ad-supported tiers.",
    },
    {
        "keyword":    "India AI policy",
        "title":      f"India's AI Policy and Technology Landscape {CURRENT_YEAR}: IndiaAI Mission, Regulation and Opportunities",
        "slug":       f"india-ai-policy-technology-{CURRENT_YEAR}",
        "category":   "ai-machine-learning",
        "cat_id":     156,
        "focus_kw":   "India AI policy",
        "description": f"India's AI policy {CURRENT_YEAR}: IndiaAI Mission, compute infrastructure, AI regulation, key use cases in telecom and the ₹10,371 crore national AI program.",
        "intent":      "Covers: IndiaAI Mission, Bhashini, AI compute infra, regulation vs innovation debate, AI in telecom (network optimisation, fraud detection), global AI race positioning.",
    },
    {
        "keyword":    "BSNL revival",
        "title":      f"BSNL Revival {CURRENT_YEAR}: Government Plan, 4G Rollout, 5G Timeline and Financial Status",
        "slug":       f"bsnl-revival-plan-{CURRENT_YEAR}",
        "category":   "market-trends",
        "cat_id":     123,
        "focus_kw":   "BSNL revival",
        "description": f"BSNL revival {CURRENT_YEAR}: ₹1.64 lakh crore bailout, TCS-built 4G network progress, 5G plans, subscriber numbers and whether the turnaround is working.",
        "intent":      "Covers: revival package size, 4G rollout status by state, subscriber losses vs gains, TCS partnership, 5G timeline, financial health, role in rural India.",
    },
    {
        "keyword":    "smartphones India",
        "title":      f"Best Smartphones in India {CURRENT_YEAR}: Ultimate Buyer's Guide by Budget",
        "slug":       f"best-smartphones-india-{CURRENT_YEAR}",
        "category":   "smartphones-tablets",
        "cat_id":     150,
        "focus_kw":   "smartphones India",
        "description": f"Best smartphones in India {CURRENT_YEAR} by budget — top picks under ₹10K, ₹20K, ₹30K and flagship segment with specs, camera ratings and 5G support.",
        "intent":      "Covers: market overview, top brands by shipment (Samsung/Vivo/Oppo/Xiaomi/Apple), budget/mid-range/premium segments, 5G adoption, made-in-India, buying guide.",
    },
    {
        "keyword":    "IoT India",
        "title":      f"IoT in India {CURRENT_YEAR}: Market Size, Key Sectors, Use Cases and Government Initiatives",
        "slug":       f"iot-india-market-{CURRENT_YEAR}",
        "category":   "internet-of-things",
        "cat_id":     165,
        "focus_kw":   "IoT India",
        "description": f"IoT India {CURRENT_YEAR}: market size, growth forecast, smart cities, agriculture, healthcare and industrial IoT use cases plus government digital India targets.",
        "intent":      "Covers: market size (USD figures), key verticals, smart city projects, agriculture IoT (precision farming), industrial IoT, connectivity (NB-IoT/eMTC), challenges and leaders.",
    },
    {
        "keyword":    "India telecom market",
        "title":      f"India Telecom Market {CURRENT_YEAR}: Size, Growth, Operators and Key Trends",
        "slug":       f"india-telecom-market-{CURRENT_YEAR}",
        "category":   "market-trends",
        "cat_id":     123,
        "focus_kw":   "India telecom market",
        "description": f"India telecom market {CURRENT_YEAR}: revenue, subscriber base, ARPU trends, operator market share (Jio/Airtel/Vi/BSNL) and outlook for the world's second-largest telecom market.",
        "intent":      "Covers: total revenue, subscriber count (900M+), mobile internet penetration, ARPU comparison, spectrum holdings, FDI rules, infrastructure (tower count), satellite entrants.",
    },
]

CATEGORY_IDS = {p["slug"]: p["cat_id"] for p in PILLAR_PAGES}


# ─── WordPress helpers ────────────────────────────────────────────────────────

def get_existing_pillar(slug: str) -> dict | None:
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        headers=HDR,
        params={"slug": slug, "_fields": "id,slug,title,link"},
        timeout=15
    )
    posts = r.json() if r.ok else []
    return posts[0] if posts else None


def save_rank_math(post_id: int, focus_kw: str, meta_title: str, meta_desc: str):
    payload = {
        "objectID": post_id, "objectType": "post",
        "meta": {
            "rank_math_focus_keyword":  focus_kw,
            "rank_math_title":          meta_title,
            "rank_math_description":    meta_desc,
        }
    }
    r = requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta", headers=HDR, json=payload, timeout=15)
    if not r.ok:
        requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", headers=HDR, json={"meta": payload["meta"]}, timeout=15)


# ─── Content generation ───────────────────────────────────────────────────────

def generate_pillar_content(page: dict) -> dict:
    kw    = page["focus_kw"]
    title = page["title"]

    prompt = f"""You are the chief analyst at The Mobile Times, India's leading telecom and technology publication.

Write a comprehensive, authoritative pillar page (1,550–1,800 words) optimised to be cited by AI search engines (ChatGPT, Perplexity, Gemini, Google AI Overviews) when answering Indian telecom questions.

TOPIC: {title}
FOCUS KEYWORD: "{kw}"
CONTENT SCOPE: {page['intent']}

━━ AI CITATION RULES ━━
1. ENTITY CLARITY: State facts about named entities (companies, regulators, technologies) in the format "Entity — fact" within the first 3 sentences of each section.
2. NUMERICAL DENSITY: Include at least 15 specific numbers/statistics across the article. AI models prefer citing pages with concrete data.
3. CANONICAL STATEMENTS: Write 2–3 sentences per section that are clear, definitive, and self-contained — perfect for AI to quote verbatim.
4. STRUCTURED ANSWERS: After every H2, the first 40–55 words must directly answer the implied question without preamble.
5. FAQ: End with 5 FAQs targeting questions people ask about "{kw}" in India. Each answer: 35–50 words, factual and quotable.

━━ CONTENT RULES ━━
• Total: 1,550–1,800 words of body text
• Every paragraph: 70–100 words
• Use "{kw}" at least 10 times (naturally)
• All dates/years: use {CURRENT_YEAR}
• Never use "placeholder" or bracketed content — all facts must be real or credible projections
• India-first perspective throughout
• Include at least one comparison table as HTML (use simple <table> tag)

━━ HTML STRUCTURE ━━

<p class="tmt-intro"><strong>[Bold opening statement with "{kw}" that defines the topic and its importance to India.]</strong> [2–3 sentences expanding the scope. Use "{kw}" again.]</p>

<div class="tmt-toc">
<h3>In This Guide</h3>
<ol>
<li><a href="#s1">[Section 1 title]</a></li>
<li><a href="#s2">[Section 2 title]</a></li>
<li><a href="#s3">[Section 3 title]</a></li>
<li><a href="#s4">[Section 4 title]</a></li>
<li><a href="#s5">[Section 5 title]</a></li>
<li><a href="#s6">Frequently Asked Questions</a></li>
</ol>
</div>

<div class="tmt-highlights">
<h3>Key Facts: {kw}</h3>
<ul>
<li>[Most important stat — with number and source type]</li>
<li>[Second key fact — entity-attribute format]</li>
<li>[Third fact — growth or change metric]</li>
<li>[Fourth fact — India-specific comparison]</li>
<li>[Fifth fact — future projection or policy]</li>
</ul>
</div>

<h2 id="s1">[Section 1 heading]</h2>
<p>[70–100 words. Start with direct factual answer to section question. "{kw}" used here.]</p>
<p>[70–100 words. Expand with data and India context.]</p>

<h2 id="s2">[Section 2 heading]</h2>
<p>[70–100 words. Direct answer first. "{kw}" used here.]</p>
[Include comparison table here if relevant]
<p>[70–100 words.]</p>

<h2 id="s3">[Section 3 heading]</h2>
<p>[70–100 words.]</p>
<p>[70–100 words.]</p>

<blockquote class="tmt-quote">"[Authoritative editorial statement about {kw} in India that AI models would cite]" — The Mobile Times Analysis</blockquote>

<h2 id="s4">[Section 4 heading]</h2>
<p>[70–100 words.]</p>

<div class="tmt-data-box">
<h3>By The Numbers: {kw}</h3>
<ul>
<li><strong>[Metric name]:</strong> [Specific value with year]</li>
<li><strong>[Metric name]:</strong> [Specific value with year]</li>
<li><strong>[Metric name]:</strong> [Specific value with year]</li>
<li><strong>[Metric name]:</strong> [Specific value with year]</li>
<li><strong>[Metric name]:</strong> [Specific value with year]</li>
</ul>
</div>

<h2 id="s5">[Section 5: Outlook heading]</h2>
<p>[70–100 words. Forward-looking. "{kw}" used here.]</p>
<p>[70–100 words.]</p>

<h2 id="s6">Frequently Asked Questions: {kw}</h2>
<div class="tmt-highlights">
<h3>People Also Ask</h3>
<ul>
<li><strong>[Q1 — most common question about {kw}]?</strong> [Direct answer 35–50 words.]</li>
<li><strong>[Q2 — second common question]?</strong> [Direct answer 35–50 words.]</li>
<li><strong>[Q3 — comparison or how-to question]?</strong> [Direct answer 35–50 words.]</li>
<li><strong>[Q4 — future or trend question]?</strong> [Direct answer 35–50 words.]</li>
<li><strong>[Q5 — India-specific deep question]?</strong> [Direct answer 35–50 words.]</li>
</ul>
</div>

<p class="tmt-sources"><strong>Sources:</strong> <a href="https://www.trai.gov.in" target="_blank" rel="noopener">TRAI ↗</a> | <a href="https://dot.gov.in" target="_blank" rel="noopener nofollow">DOT ↗</a> | <a href="https://www.gsma.com" target="_blank" rel="noopener nofollow">GSMA ↗</a></p>

━━ AFTER HTML, output this on a new line ━━
META_JSON:{{"meta_title":"{title[:55]} | The Mobile Times","meta_description":"[130-155 chars with '{kw}' + India + {CURRENT_YEAR} + CTA]","faq":[{{"q":"[Q1]","a":"[A1 35-50 words]"}},{{"q":"[Q2]","a":"[A2]"}},{{"q":"[Q3]","a":"[A3]"}},{{"q":"[Q4]","a":"[A4]"}},{{"q":"[Q5]","a":"[A5]"}}]}}"""

    r = ai.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = r.content[0].text.strip()

    html_content, meta = raw, {}
    if "META_JSON:" in raw:
        parts        = raw.split("META_JSON:", 1)
        html_content = parts[0].strip()
        try:
            ms = parts[1].strip()
            ms = re.sub(r"^```(?:json)?\s*", "", ms)
            ms = re.sub(r"\s*```$", "", ms)
            meta = json.loads(ms)
        except Exception:
            pass

    # Strip markdown code fences if Claude wrapped the HTML
    html_content = re.sub(r"^```html?\s*\n?", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"\n?```\s*$", "", html_content)

    # Fix wrong years
    for yr in ["2020", "2021", "2022", "2023", "2024", "2025"]:
        html_content = html_content.replace(yr, CURRENT_YEAR)

    date_str = datetime.now(IST).isoformat()
    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title[:110],
        "description": page["description"],
        "datePublished": date_str,
        "dateModified":  date_str,
        "author": {"@type": "Person", "name": AUTHOR_NAME, "url": AUTHOR_URL},
        "publisher": {
            "@type": "NewsMediaOrganization",
            "name": "The Mobile Times",
            "url": WP_URL,
            "logo": {"@type": "ImageObject", "url": f"{WP_URL}/wp-content/uploads/circle-logo.png"}
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{WP_URL}/{page['slug']}/"},
        "keywords": kw,
        "inLanguage": "en-IN",
        "about": {"@type": "Thing", "name": kw},
    }

    faq_items = meta.get("faq", [])
    schemas = [schema]
    if faq_items:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                for f in faq_items if "q" in f and "a" in f
            ]
        })
    for s in schemas:
        html_content += f'\n<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>'

    meta_title = meta.get("meta_title", f"{title[:55]} | The Mobile Times")
    meta_desc  = meta.get("meta_description", page["description"])

    return {
        "html":        html_content,
        "meta_title":  meta_title,
        "meta_desc":   meta_desc,
        "faq_items":   faq_items,
    }


# ─── Create / update pillar page ─────────────────────────────────────────────

def create_or_update_pillar(page: dict):
    kw    = page["focus_kw"]
    title = page["title"]
    slug  = page["slug"]

    log.info(f"\n{'='*60}")
    log.info(f"Processing: {title[:70]}")

    existing = get_existing_pillar(slug)
    if existing:
        log.info(f"  Existing post found (ID {existing['id']}) — updating...")

    log.info(f"  Generating content for '{kw}'...")
    result = generate_pillar_content(page)

    payload = {
        "title":      title,
        "content":    result["html"],
        "status":     "publish",
        "slug":       slug,
        "categories": [page["cat_id"]],
        "tags":       [],
        "sticky":     False,
    }

    if existing:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{existing['id']}",
            headers=HDR, json=payload, timeout=30
        )
        post_id = existing["id"]
        action  = "Updated"
    else:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=HDR, json=payload, timeout=30)
        post_id = r.json().get("id") if r.ok else None
        action  = "Created"

    if r.ok and post_id:
        save_rank_math(post_id, kw, result["meta_title"], result["meta_desc"])
        post_url = r.json().get("link", f"{WP_URL}/{slug}/")
        log.info(f"  {action}: {post_url}")
        return post_url
    else:
        log.error(f"  Failed ({r.status_code}): {r.text[:150]}")
        return None


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TMT Pillar Page Creator")
    parser.add_argument("--create-all", action="store_true", help="Create/update all 10 pillar pages")
    parser.add_argument("--create",     type=str, default="",  help="Create/update one page by keyword match")
    parser.add_argument("--list",       action="store_true",  help="List all configured pillar pages")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'='*60}")
        print(f"{'#':<3} {'KEYWORD':<22} {'SLUG'}")
        print(f"{'='*60}")
        for i, p in enumerate(PILLAR_PAGES, 1):
            print(f"{i:<3} {p['focus_kw']:<22} {p['slug']}")
        print()
        return

    if args.create_all:
        results = []
        for page in PILLAR_PAGES:
            url = create_or_update_pillar(page)
            results.append((page["focus_kw"], url or "FAILED"))
        print(f"\n{'='*60}")
        print(f"Pillar pages done — {sum(1 for _, u in results if u != 'FAILED')}/{len(results)} successful")
        for kw, url in results:
            print(f"  {kw:<22} -> {url}")
        return

    if args.create:
        needle = args.create.lower()
        matches = [p for p in PILLAR_PAGES if needle in p["focus_kw"].lower() or needle in p["slug"]]
        if not matches:
            print(f"No pillar page found matching '{args.create}'")
            print("Use --list to see available pages")
            sys.exit(1)
        for page in matches:
            create_or_update_pillar(page)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
