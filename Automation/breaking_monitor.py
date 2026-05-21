"""
breaking_monitor.py — 24/7 Breaking News Monitor for The Mobile Times

Runs as a SEPARATE background process. Polls RSS feeds + Google Trends every
15–20 minutes. When a high-scoring story is found it publishes immediately to
the "Industry Trends" bucket — without duplicating stories already published
in the daily run.

Limits: max 3 breaking posts per calendar day (IST).

Usage:
  python breaking_monitor.py            # run continuously
  python breaking_monitor.py --once     # single scan (for testing)
"""

import os, sys, re, json, base64, time, random, io, hashlib, logging, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser
import anthropic
import schedule
from PIL import Image
from dotenv import load_dotenv
import pytz

load_dotenv()

WP_URL        = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER       = os.getenv("WP_USER")
WP_PASS       = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
PEXELS_KEY    = os.getenv("PEXELS_API_KEY")
LOGO_PATH     = os.getenv("LOGO_PATH", r"e:\Projects\Clients\TMT\Logo\Circle Logo.png")
INDEXNOW_KEY  = os.getenv("INDEXNOW_KEY", "")

IST           = pytz.timezone("Asia/Kolkata")
creds         = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
WP_HDR        = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

CURRENT_YEAR  = str(datetime.now(IST).year)
WRONG_YEARS   = ["2020", "2021", "2022", "2023", "2024", "2025"]
AUTHOR_NAME   = "Sanjay Goyal"
AUTHOR_URL    = "https://themobiletimes.com/author/sanjay/"
BREAKING_WORD_TARGET = "380-440"

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tmt_breaking.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("tmt.breaking")

MAX_BREAKING_PER_DAY = 3
POLL_INTERVAL_MIN    = 17          # minutes between polls
SCORE_THRESHOLD      = 65          # 0-100; only publish if story scores above this
SEEN_FILE            = Path(__file__).resolve().parent / "breaking_seen.json"

BREAKING_CATEGORY_IDS = {
    "5g-networks":     160,
    "industry-trends": 159,
    "ott-streaming":   162,
    "ev-smart-grids":  164,
    "internet-of-things": 165,
    "tech-innovation": 161,
    "policy-updates":  122,
    "market-trends":   123,
}

TAG_IDS = {
    "trending":      167,
    "breaking-news": 166,
    "new-launch":    169,
}

RSS_FEEDS = [
    "https://economictimes.indiatimes.com/tech/telecom/rssfeeds/13357270.cms",
    "https://telecomtalk.info/feed/",
    "https://www.medianama.com/feed/",
    "https://entrackr.com/feed/",
    "https://www.lightreading.com/rss.xml",
    "https://www.fiercetelecom.com/rss.xml",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/feed/",
]

AUTHORITY_LINKS = [
    ("TRAI",     "https://www.trai.gov.in"),
    ("DOT",      "https://dot.gov.in"),
    ("GSMA",     "https://www.gsma.com"),
    ("COAI",     "https://www.coai.in"),
]


# ─── Seen-story deduplication ─────────────────────────────────────────────────

def _load_seen() -> dict:
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"published": [], "daily": {}}

def _save_seen(data: dict):
    SEEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _story_hash(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()

def get_today_count() -> int:
    data = _load_seen()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    return data.get("daily", {}).get(today, 0)

def mark_published(title: str):
    data = _load_seen()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    data.setdefault("published", []).append(_story_hash(title))
    data.setdefault("daily", {})[today] = data["daily"].get(today, 0) + 1
    # Trim seen list to last 500 entries
    data["published"] = data["published"][-500:]
    _save_seen(data)

def already_seen(title: str) -> bool:
    data = _load_seen()
    return _story_hash(title) in data.get("published", [])


def already_published_on_wp(title: str) -> bool:
    """Check WP REST API for a similar post in the last 24 h — stateless dedup for GitHub Actions."""
    try:
        cutoff = (datetime.now(IST) - timedelta(hours=24)).astimezone(timezone.utc).isoformat()
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=WP_HDR,
            params={"per_page": 20, "status": "publish,future", "_fields": "title", "after": cutoff},
            timeout=10
        )
        if not r.ok:
            return False
        STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "are",
                     "was", "has", "its", "have", "will", "india", "2026"}
        title_words = set(re.findall(r"\b\w{3,}\b", title.lower())) - STOPWORDS
        for post in r.json():
            pub_title = re.sub(r"<[^>]+>", "", post["title"]["rendered"]).lower()
            pub_words = set(re.findall(r"\b\w{3,}\b", pub_title)) - STOPWORDS
            if not pub_words:
                continue
            overlap = len(title_words & pub_words) / max(len(title_words), 1)
            if overlap >= 0.4:
                log.info(f"  WP dedup: skipping '{title[:55]}' ({overlap:.0%} overlap with recent post)")
                return True
        return False
    except Exception as e:
        log.debug(f"WP dedup check failed: {e}")
        return False


# ─── Image helpers (copied from main agent) ──────────────────────────────────

_cached_logo = None

def get_cleaned_logo():
    global _cached_logo
    if _cached_logo:
        return _cached_logo
    logo = Image.open(LOGO_PATH).convert("RGBA")
    data = logo.load()
    for y in range(logo.height):
        for x in range(logo.width):
            r, g, b, a = data[x, y]
            if r < 40 and g < 40 and b < 40:
                data[x, y] = (r, g, b, 0)
    _cached_logo = logo
    return logo

def add_watermark(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    logo = get_cleaned_logo().copy()
    logo_w = int(img.width * 0.14)
    logo_h = int(logo.height * (logo_w / logo.width))
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    r, g, b, a = logo.split()
    a = a.point(lambda p: int(p * 0.88))
    logo = Image.merge("RGBA", (r, g, b, a))
    pad = 22
    x = img.width  - logo_w - pad
    y = img.height - logo_h - pad
    img.paste(logo, (x, y), logo)
    return img.convert("RGB")

def resize_image(img: Image.Image, w=1200, h=628) -> Image.Image:
    ratio = max(w / img.width, h / img.height)
    new_w, new_h = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - w) // 2, (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))

def fetch_pexels_image(keyword: str) -> bytes | None:
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": f"{keyword} India technology", "per_page": 5, "orientation": "landscape"},
            timeout=15
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos[:3])
        img_r = requests.get(photo["src"]["large2x"], timeout=20)
        img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
        img = resize_image(img)
        img = add_watermark(img)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        log.warning(f"Pexels fetch failed: {e}")
        return None

def extract_source_image(url: str) -> bytes | None:
    if not url:
        return None
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TMTBot/1.0)"}
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if not r.ok:
            return None
        soup = BeautifulSoup(r.text, "lxml")
        img_url = None
        for attr in [("property", "og:image"), ("name", "og:image"),
                     ("name", "twitter:image"), ("property", "twitter:image")]:
            tag = soup.find("meta", attrs={attr[0]: attr[1]})
            if tag and tag.get("content", "").startswith("http"):
                img_url = tag["content"]
                break
        if not img_url:
            return None
        img_r = requests.get(img_url, headers=headers, timeout=15)
        if not img_r.ok or len(img_r.content) < 5000:
            return None
        img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
        img = resize_image(img)
        img = add_watermark(img)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
        return buf.getvalue()
    except Exception as e:
        log.warning(f"Source image extraction failed: {e}")
        return None

def make_fallback_image(title: str) -> bytes:
    img = Image.new("RGB", (1200, 628), color=(10, 22, 40))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()

def upload_image_to_wp(img_bytes: bytes, filename: str, alt: str) -> int | None:
    try:
        upload_headers = {
            "Authorization": f"Basic {creds}",
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "image/jpeg",
        }
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=upload_headers, data=img_bytes, timeout=30)
        r.raise_for_status()
        media_id = r.json()["id"]
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            headers=WP_HDR,
            json={"alt_text": alt, "caption": "© The Mobile Times"},
        )
        return media_id
    except Exception as e:
        log.warning(f"Image upload failed: {e}")
        return None


# ─── RSS Polling ──────────────────────────────────────────────────────────────

def poll_rss() -> list[dict]:
    stories = []
    seen_hashes = set()
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                if not title or not link:
                    continue
                h = _story_hash(title)
                if h in seen_hashes or already_seen(title) or already_published_on_wp(title):
                    continue
                seen_hashes.add(h)
                summary = re.sub(r"<[^>]+>", " ", summary)[:600].strip()
                stories.append({"title": title, "summary": summary, "url": link,
                                 "source": feed.feed.get("title", url)})
        except Exception as e:
            log.debug(f"RSS feed failed ({url}): {e}")
    log.info(f"Poll: {len(stories)} new stories")
    return stories


# ─── Story Scoring ────────────────────────────────────────────────────────────

BREAKING_KEYWORDS = [
    "breaking", "urgent", "just in", "first", "launch", "launches", "announces",
    "ban", "banned", "shutdown", "outage", "down", "breach", "hack", "arrest",
    "regulation", "fined", "penalty", "acquired", "merger", "ipo", "funding",
    "5g", "jio", "airtel", "vi", "vodafone", "bsnl", "trai", "doi", "dot",
    "india", "crore", "billion", "million", "record", "highest", "lowest",
]

def score_story(story: dict) -> int:
    text = (story["title"] + " " + story["summary"]).lower()
    score = 0
    for kw in BREAKING_KEYWORDS:
        if kw in text:
            score += 5
    # Recency boost: titles with today's date string
    today = datetime.now(IST).strftime("%Y")
    if today in text:
        score += 10
    # India relevance
    india_terms = ["india", "indian", "jio", "airtel", "bsnl", "trai"]
    if any(t in text for t in india_terms):
        score += 15
    return min(score, 100)


def validate_and_fix(content: str, title: str) -> tuple[str, str, list[str]]:
    warnings = []
    for yr in WRONG_YEARS:
        if yr in content:
            content = content.replace(yr, CURRENT_YEAR)
            warnings.append(f"Fixed year {yr}→{CURRENT_YEAR} in content")
        if yr in title:
            title = title.replace(yr, CURRENT_YEAR)
            warnings.append(f"Fixed year {yr}→{CURRENT_YEAR} in title")
    placeholders = re.findall(r"\[(?!a |/a)[^\]]{3,60}\]", content)
    if placeholders:
        warnings.append(f"Unfilled placeholders: {placeholders[:3]}")
    word_count = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", content)))
    if word_count < 350:
        warnings.append(f"Article too short: {word_count} words")
    if warnings:
        log.warning(f"  Breaking QA: {'; '.join(warnings)}")
    else:
        log.info(f"  Breaking QA: passed ({word_count} words)")
    return content, title, warnings


# ─── Breaking Content Generation ──────────────────────────────────────────────

def generate_breaking_post(story: dict, date_str: str) -> dict:
    prompt = f"""You are a breaking news journalist at The Mobile Times, India's leading telecom publication.
Writing style: urgent breaking news desk — punchy sentences, active voice, high energy.

SOURCE STORY:
Headline: {story['title']}
Summary: {story['summary']}
URL: {story['url']}

━━ MANDATORY TITLE RULES ━━
Generate a new SEO-optimized breaking news title:
• Derive the best 2–4 word focus keyword from this story
• Must contain that focus keyword
• Must start with or contain a power word: Breaking, Major, Urgent, Live, Just In, Alert, Launches, Warns, Reveals, Expands, Hits, Surges
• Must contain 1 number (year 2026, percentage, or statistic)
• 55–70 characters total

━━ WORD COUNT ━━
Total article: {BREAKING_WORD_TARGET} words. No padding, no repetition.

━━ KEYWORD DENSITY RULE ━━
Use the focus keyword EXACTLY 7 times in the article body.
Distribution: intro (1), H2 headings (2), body paragraphs (3), outlook (1).

━━ PARAGRAPH LENGTH RULE ━━
Every <p> tag must be 60–90 words. Split any longer content.

━━ YEAR RULE ━━
Every date reference must use 2026. Never use 2025 or any earlier year.

━━ META DESCRIPTION RULE ━━
meta_description MUST contain the exact focus keyword verbatim. 120–155 characters.

━━ OUTPUT FORMAT (HTML only) ━━

<p class="tmt-intro"><strong>[First sentence with focus keyword.]</strong> [2 sentences of context.]</p>

<div class="tmt-toc">
<h3>In This Article</h3>
<ol>
<li><a href="#s1">[Section 1]</a></li>
<li><a href="#s2">[Section 2]</a></li>
<li><a href="#s3">What Happens Next</a></li>
</ol>
</div>

<div class="tmt-highlights">
<h3>Key Highlights</h3>
<ul>
<li>[Fact with number]</li>
<li>[Fact 2]</li>
<li>[Fact 3]</li>
</ul>
</div>

<h2 id="s1">[Heading with focus keyword]</h2>
<p>[70–100 words. Core facts. Real data. India angle.]</p>

<h2 id="s2">[Impact heading with focus keyword]</h2>
<p>[70–100 words. Industry impact.]</p>

<blockquote class="tmt-quote">"[Expert quote on this development]" — Industry Analyst, Telecom Sector</blockquote>

<h2 id="s3">What Happens Next</h2>
<p>[70–90 words. Immediate next steps. Use focus keyword.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>

<div class="tmt-highlights">
<h3>People Also Ask</h3>
<ul>
<li><strong>[Question 1 about the topic people search on Google]?</strong> [Direct answer in 30–40 words.]</li>
<li><strong>[Question 2 — different angle on the topic]?</strong> [Direct answer in 30–40 words.]</li>
<li><strong>[Question 3 — impact or what-next angle]?</strong> [Direct answer in 30–40 words.]</li>
</ul>
</div>

━━ NEW LINE AFTER HTML ━━
META_JSON:{{"article_title":"[title]","slug":"[slug]-2026-india","focus_keyword":"[2-4 words]","meta_title":"[50-60 chars | The Mobile Times]","meta_description":"[120-155 chars MUST contain focus keyword]","og_title":"[60-70 chars]","og_description":"[180-200 chars]","category":"[one of: 5g-networks, industry-trends, ott-streaming, ev-smart-grids, internet-of-things, tech-innovation, policy-updates, market-trends]","faq":[{{"q":"[Q1]","a":"[A1]"}},{{"q":"[Q2]","a":"[A2]"}},{{"q":"[Q3]","a":"[A3]"}}]}}"""

    r = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = r.content[0].text.strip()

    if "META_JSON:" in raw:
        parts = raw.split("META_JSON:", 1)
        html_content = parts[0].strip()
        try:
            ms = parts[1].strip()
            ms = re.sub(r"^```(?:json)?\s*", "", ms)
            ms = re.sub(r"\s*```$", "", ms)
            meta = json.loads(ms)
        except Exception:
            meta = {}
    else:
        html_content = raw
        meta = {}

    html_content = re.sub(r"^```html?\s*\n?", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"\n?```\s*$", "", html_content)

    kw    = meta.get("focus_keyword", "India telecom breaking news")
    title = meta.get("article_title", story["title"])

    # QA: fix years and detect placeholders before publishing
    html_content, title, _ = validate_and_fix(html_content, title)

    # Inject authority links (first one dofollow)
    sources = random.sample(AUTHORITY_LINKS, min(2, len(AUTHORITY_LINKS)))
    link_parts = []
    for idx, (name, url) in enumerate(sources):
        rel = 'rel="noopener"' if idx == 0 else 'rel="noopener nofollow"'
        link_parts.append(f'<a href="{url}" target="_blank" {rel}>{name} ↗</a>')
    source_html = ' | '.join(link_parts)
    old_src = '<p class="tmt-sources"><strong>Sources:</strong>'
    new_src = f'<p class="tmt-sources"><strong>Sources:</strong> {source_html}'
    html_content = html_content.replace(old_src, new_src, 1) if old_src in html_content else html_content + f'\n{new_src}</p>'

    html_content = '<span class="tmt-breaking-badge">BREAKING NEWS</span>\n' + html_content

    slug     = meta.get("slug", re.sub(r"[^a-z0-9-]", "", kw.lower().replace(" ", "-")))
    meta_t   = meta.get("meta_title",   f"{title[:50]} | The Mobile Times")
    meta_d   = meta.get("meta_description", f"Breaking: {kw} news from India.")
    og_title = meta.get("og_title",     meta_t)
    og_desc  = meta.get("og_description", meta_d)
    cat_slug = meta.get("category", "industry-trends")

    if kw.lower() not in meta_d.lower():
        meta_d = f"{kw}: {meta_d}"[:155]

    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title[:110],
        "description": meta_d,
        "datePublished": date_str,
        "dateModified":  date_str,
        "author": {"@type": "Person", "name": AUTHOR_NAME, "url": AUTHOR_URL},
        "publisher": {
            "@type": "NewsMediaOrganization",
            "name": "The Mobile Times",
            "url": WP_URL,
            "logo": {"@type": "ImageObject", "url": f"{WP_URL}/wp-content/uploads/circle-logo.png"}
        },
        "keywords": kw,
        "articleSection": "Breaking News",
        "inLanguage": "en-IN",
    }
    schemas = [schema]
    faq_items = meta.get("faq", [])
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
        html_content += f'\n<script type="application/ld+json">{json.dumps(s)}</script>'

    slug = slug.replace("2025", CURRENT_YEAR).replace("2024", CURRENT_YEAR)

    return {
        "title":            title,
        "content":          html_content,
        "slug":             slug,
        "focus_keyword":    kw,
        "meta_title":       meta_t,
        "meta_description": meta_d,
        "og_title":         og_title,
        "og_description":   og_desc,
        "category_slug":    cat_slug if cat_slug in BREAKING_CATEGORY_IDS else "industry-trends",
        "tags":             ["breaking-news"],
        "is_breaking":      True,
        "is_launch":        False,
        "source_url":       story["url"],
    }


# ─── WordPress Publishing ─────────────────────────────────────────────────────

def save_rank_math_meta(post_id: int, post_data: dict):
    meta_payload = {
        "objectID":   post_id,
        "objectType": "post",
        "meta": {
            "rank_math_title":               post_data["meta_title"],
            "rank_math_description":         post_data["meta_description"],
            "rank_math_focus_keyword":       post_data["focus_keyword"],
            "rank_math_og_title":            post_data["og_title"],
            "rank_math_og_description":      post_data["og_description"],
            "rank_math_twitter_title":       post_data["og_title"],
            "rank_math_twitter_description": post_data["og_description"],
        }
    }
    r = requests.post(
        f"{WP_URL}/wp-json/rankmath/v1/updateMeta",
        headers=WP_HDR,
        json=meta_payload,
        timeout=15
    )
    if not r.ok:
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=WP_HDR,
            json={"meta": meta_payload["meta"]},
            timeout=15
        )

def publish_breaking_post(post_data: dict, media_id: int | None) -> dict | None:
    cat_id  = BREAKING_CATEGORY_IDS.get(post_data["category_slug"], BREAKING_CATEGORY_IDS["industry-trends"])
    tag_ids = [TAG_IDS["breaking-news"]]

    payload = {
        "title":          post_data["title"],
        "content":        post_data["content"],
        "status":         "publish",
        "slug":           post_data["slug"],
        "categories":     [cat_id],
        "tags":           tag_ids,
        "sticky":         True,
        "featured_media": media_id or 0,
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=WP_HDR, json=payload, timeout=30)
    if r.ok:
        post = r.json()
        save_rank_math_meta(post["id"], post_data)
        return post
    log.error(f"Breaking publish failed ({r.status_code}): {r.text[:200]}")
    return None

def ping_indexing(post_url: str):
    try:
        if INDEXNOW_KEY:
            requests.get("https://api.indexnow.org/indexnow",
                         params={"url": post_url, "key": INDEXNOW_KEY}, timeout=5)
        requests.get("https://www.google.com/ping",
                     params={"sitemap": f"{WP_URL}/sitemap.xml"}, timeout=5)
        requests.post(f"{WP_URL}/wp-json/litespeed/v1/purge/all", headers=WP_HDR, timeout=10)
    except Exception:
        pass


# ─── Main Scan Loop ───────────────────────────────────────────────────────────

def run_scan():
    now_ist  = datetime.now(IST)
    date_str = now_ist.isoformat()

    count_today = get_today_count()
    if count_today >= MAX_BREAKING_PER_DAY:
        log.info(f"Daily cap reached ({count_today}/{MAX_BREAKING_PER_DAY}) — skipping scan")
        return

    stories = poll_rss()
    if not stories:
        log.info("No new stories found")
        return

    # Score all stories and pick the best candidate
    scored = [(score_story(s), s) for s in stories]
    scored.sort(key=lambda x: x[0], reverse=True)

    log.info(f"Top story score: {scored[0][0]} — {scored[0][1]['title'][:60]}")

    if scored[0][0] < SCORE_THRESHOLD:
        log.info(f"Score {scored[0][0]} below threshold {SCORE_THRESHOLD} — no breaking post")
        return

    best = scored[0][1]
    log.info(f"Breaking story selected: {best['title'][:70]}")

    post_data = generate_breaking_post(best, date_str)
    log.info(f"  Title: {post_data['title'][:70]}")
    log.info(f"  Category: {post_data['category_slug']}  KW: {post_data['focus_keyword']}")

    img_bytes = (
        extract_source_image(best.get("url", "")) or
        fetch_pexels_image(post_data["focus_keyword"]) or
        make_fallback_image(best["title"])
    )
    today_str = now_ist.strftime("%Y-%m-%d")
    filename  = f"tmt-breaking-{today_str}-{count_today+1}.jpg"
    media_id  = upload_image_to_wp(img_bytes, filename, f"Breaking: {post_data['focus_keyword']}")

    result = publish_breaking_post(post_data, media_id)
    if result:
        post_url = result.get("link", "")
        log.info(f"  BREAKING PUBLISHED: {post_url}")
        mark_published(best["title"])
        ping_indexing(post_url)

        try:
            from social_poster import post_to_all
            post_to_all(post_data["title"], post_url, post_data["tags"], category=post_data["category_slug"])
        except Exception as e:
            log.warning(f"Social posting failed: {e}")
    else:
        log.error("Breaking post publish failed")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TMT Breaking News Monitor")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    args = parser.parse_args()

    if args.once:
        log.info("Single scan mode")
        run_scan()
        sys.exit(0)

    log.info(f"Breaking news monitor started — polling every {POLL_INTERVAL_MIN} min (max {MAX_BREAKING_PER_DAY}/day)")

    schedule.every(POLL_INTERVAL_MIN).minutes.do(run_scan)

    # Run once immediately on startup
    run_scan()

    while True:
        schedule.run_pending()
        time.sleep(30)
