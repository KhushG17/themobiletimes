"""
fill_empty_categories.py
Publishes one news post in each of 5 empty categories using Claude Sonnet.
"""
import os, sys, re, json, base64, logging
from datetime import datetime
from dotenv import load_dotenv
import requests, anthropic, pytz

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

WP_URL  = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
AI_KEY  = os.getenv("ANTHROPIC_API_KEY")
IST     = pytz.timezone("Asia/Kolkata")
YEAR    = str(datetime.now(IST).year)

creds  = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR    = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
ai     = anthropic.Anthropic(api_key=AI_KEY)

AUTHOR_NAME = "Sanjay Goyal"
AUTHOR_URL  = "https://themobiletimes.com/author/sanjay/"

# 5 empty categories to fill
TARGETS = [
    {
        "cat_id":   129,
        "cat_slug": "devices-hardware",
        "topic":    f"India smartphone hardware trends {YEAR}",
        "focus_kw": "smartphone hardware India",
        "hint":     "Cover latest device launches, chipset upgrades, or display/battery technology trends "
                    "in the Indian smartphone market. Include specific models, brands (Samsung, OnePlus, Vivo, Oppo), "
                    "and what India buyers care about.",
    },
    {
        "cat_id":   159,
        "cat_slug": "industry-trends",
        "topic":    f"India telecom industry trends {YEAR}",
        "focus_kw": "India telecom industry trends",
        "hint":     "Cover macro trends shaping India's telecom industry: ARPU growth, subscriber churn, "
                    "rural penetration, enterprise 5G adoption, or operator revenue trends. "
                    "Include data points and analyst perspectives.",
    },
    {
        "cat_id":   161,
        "cat_slug": "tech-innovation",
        "topic":    f"technology innovation India telecom {YEAR}",
        "focus_kw": "tech innovation India telecom",
        "hint":     "Cover a breakthrough technology being adopted by Indian telecom or tech companies: "
                    "network slicing, open RAN, satellite internet, or AI-driven network management. "
                    "Explain the real-world impact for Indian users and businesses.",
    },
    {
        "cat_id":   154,
        "cat_slug": "software",
        "topic":    f"telecom software apps India {YEAR}",
        "focus_kw": "telecom software India",
        "hint":     "Cover software, apps, or SaaS tools transforming India's telecom or mobile industry: "
                    "billing software, network management platforms, consumer apps, or enterprise mobility solutions. "
                    "Include specific product names and India-specific use cases.",
    },
    {
        "cat_id":   157,
        "cat_slug": "data-analytics",
        "topic":    f"data analytics telecom India {YEAR}",
        "focus_kw": "data analytics telecom India",
        "hint":     "Cover how Indian telecom operators are using big data and analytics: "
                    "churn prediction, network optimisation, personalised plans, fraud detection, "
                    "or revenue assurance. Include real operator examples (Jio, Airtel, Vi).",
    },
]

PROMPT_TEMPLATE = """You are a senior journalist at The Mobile Times — India's leading telecom and technology news publication.

Write a well-researched news article for the following topic:

Topic: {topic}
Category: {cat_slug}
Focus keyword: {focus_kw}
Hint: {hint}
Current year: {year}

Requirements:
- Length: 520-620 words of body content
- Structure: H2 subheadings every 120-150 words (use <h2> tags)
- Opening: strong news hook — state the key fact or development in the first sentence
- Include: 3-5 specific data points or statistics relevant to India
- Include: named companies, products, or government bodies where relevant
- Tone: professional, factual, trade-focused (audience = mobile retailers and telecom industry professionals)
- End with a brief "What This Means" or "Industry Outlook" section

Format the article as clean HTML (h2, p, ul/li only — no divs, no inline styles).
Do NOT wrap in ```html fences.

After the article HTML, output exactly:

META_JSON:
{{
  "article_title": "compelling SEO title under 65 chars, includes focus keyword and year",
  "slug": "url-slug-here",
  "focus_keyword": "{focus_kw}",
  "meta_description": "compelling meta description 140-155 chars with focus keyword",
  "tags": ["India telecom", "technology"]
}}"""


def generate_post(target: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        topic=target["topic"], cat_slug=target["cat_slug"],
        focus_kw=target["focus_kw"], hint=target["hint"], year=YEAR
    )
    r = ai.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = r.content[0].text.strip()

    if "META_JSON:" in raw:
        parts        = raw.split("META_JSON:", 1)
        html_content = parts[0].strip()
        try:
            ms   = parts[1].strip()
            ms   = re.sub(r"^```(?:json)?\s*", "", ms)
            ms   = re.sub(r"\s*```$", "", ms)
            meta = json.loads(ms)
        except Exception:
            meta = {}
    else:
        html_content = raw
        meta = {}

    # Strip any accidental markdown fences
    html_content = re.sub(r"^```html?\s*\n?", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"\n?```\s*$", "", html_content)

    date_str = datetime.now(IST).isoformat()
    schema = {
        "@context":  "https://schema.org",
        "@type":     "NewsArticle",
        "headline":  meta.get("article_title", target["topic"])[:110],
        "datePublished": date_str,
        "dateModified":  date_str,
        "author":    {"@type": "Person", "name": AUTHOR_NAME, "url": AUTHOR_URL},
        "publisher": {
            "@type": "NewsMediaOrganization",
            "name":  "The Mobile Times",
            "url":   WP_URL,
            "logo":  {"@type": "ImageObject", "url": f"{WP_URL}/wp-content/uploads/circle-logo.png"},
        },
        "inLanguage": "en-IN",
        "keywords":  target["focus_kw"],
    }
    html_content += f'\n<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return {
        "title":       meta.get("article_title", target["topic"]),
        "slug":        meta.get("slug", target["cat_slug"] + f"-news-{YEAR}"),
        "content":     html_content,
        "focus_kw":    meta.get("focus_keyword", target["focus_kw"]),
        "meta_desc":   meta.get("meta_description", ""),
        "tags":        meta.get("tags", []),
        "cat_id":      target["cat_id"],
        "cat_slug":    target["cat_slug"],
    }


def get_or_create_tags(tag_names: list) -> list:
    ids = []
    for name in tag_names[:5]:
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower().strip())[:50]
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags", headers=HDR,
            params={"slug": slug}, timeout=10)
        if r.ok and r.json():
            ids.append(r.json()[0]["id"])
        else:
            r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", headers=HDR,
                json={"name": name, "slug": slug}, timeout=10)
            if r2.ok:
                ids.append(r2.json()["id"])
    return ids


def publish(post: dict) -> bool:
    tag_ids = get_or_create_tags(post["tags"])
    payload = {
        "title":      post["title"],
        "content":    post["content"],
        "status":     "publish",
        "slug":       post["slug"],
        "categories": [post["cat_id"]],
        "tags":       tag_ids,
        "author":     1,
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=HDR, json=payload, timeout=30)
    if not r.ok:
        log.error(f"  Publish failed: {r.status_code} {r.text[:200]}")
        return False

    pid = r.json()["id"]
    link = r.json().get("link", "")

    # Push Rank Math meta
    rm = requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta", headers=HDR,
        json={"objectID": pid, "objectType": "post",
              "meta": {"rank_math_focus_keyword": post["focus_kw"],
                       "rank_math_description":   post["meta_desc"]}},
        timeout=15)
    seo_ok = rm.ok and rm.json().get("slug") is True

    log.info(f"  Published [{pid}]: {link}")
    log.info(f"  SEO meta: {'OK' if seo_ok else 'check manually'}")
    return True


def main():
    log.info(f"Filling 5 empty categories — {YEAR}")
    log.info("=" * 60)

    for t in TARGETS:
        log.info(f"\nCategory: {t['cat_slug']} [{t['cat_id']}]")
        log.info(f"Topic: {t['topic']}")
        try:
            post = generate_post(t)
            log.info(f"  Title: {post['title']}")
            log.info(f"  Keyword: {post['focus_kw']}")
            log.info(f"  Desc ({len(post['meta_desc'])} chars): {post['meta_desc']}")
            ok = publish(post)
            if not ok:
                log.error("  FAILED to publish")
        except Exception as e:
            log.error(f"  ERROR: {e}")

    log.info("\n" + "=" * 60)
    log.info("Done.")


if __name__ == "__main__":
    main()
