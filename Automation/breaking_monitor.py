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
NEWS_API_KEY   = os.getenv("NEWS_API_KEY", "")
TMT_SECRET     = os.getenv("TMT_SECRET", "")
LOGO_PATH      = os.getenv("LOGO_PATH", "assets/Circle_Logo.png")
INDEXNOW_KEY   = os.getenv("INDEXNOW_KEY", "")
UNSPLASH_KEY   = os.getenv("UNSPLASH_ACCESS_KEY", "")

IST           = pytz.timezone("Asia/Kolkata")
creds         = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
WP_HDR        = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

CURRENT_YEAR  = str(datetime.now(IST).year)
WRONG_YEARS   = ["2020", "2021", "2022", "2023", "2024", "2025"]
AUTHOR_NAME   = "Sanjay Goyal"
AUTHOR_URL    = "https://themobiletimes.com/author/sanjay/"
BREAKING_WORD_TARGET = "600-750"

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
SCORE_THRESHOLD      = 45          # 0-100; only publish if story scores above this

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
    # India — Telecom & Tech
    "https://economictimes.indiatimes.com/tech/telecom/rssfeeds/13357270.cms",
    "https://telecomtalk.info/feed/",
    "https://www.medianama.com/feed/",
    "https://entrackr.com/feed/",
    "https://www.business-standard.com/rss/technology-10.rss",
    "https://www.livemint.com/rss/technology",
    "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "https://www.financialexpress.com/industry/technology/feed/",
    "https://inc42.com/feed/",
    "https://yourstory.com/feed",
    # India — Gadgets & Devices
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://www.91mobiles.com/hub/feed/",
    "https://www.digit.in/rss/news",
    # Global — Telecom
    "https://www.lightreading.com/rss.xml",
    "https://www.fiercetelecom.com/rss.xml",
    "https://www.rcrwireless.com/feed",
    "https://telecomramblings.com/feed/",
    "https://www.capacitymedia.com/rss",
    "https://www.totaltele.com/rss.ashx",
    # Global — Tech & AI
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://arstechnica.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    # Cybersecurity
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://krebsonsecurity.com/feed/",
    # Semiconductors & Hardware
    "https://www.eetimes.com/rss/",
    "https://www.anandtech.com/rss/",
    # Policy & Regulation
    "https://www.telecompaper.com/rss/news",
    "https://policywatch.in/feed/",
    # OTT & Digital Media
    "https://www.afaqs.com/rss/news.xml",
    "https://www.exchange4media.com/rss/technology-news.xml",
]

NEWS_API_QUERIES = [
    "5G India telecom Jio Airtel",
    "TRAI DOT India broadband policy",
    "India tech startup funding fintech",
    "cybersecurity breach India",
    "smartphone launch India 2026",
]

AUTHORITY_LINKS = [
    ("TRAI",     "https://www.trai.gov.in"),
    ("DOT",      "https://dot.gov.in"),
    ("GSMA",     "https://www.gsma.com"),
    ("COAI",     "https://www.coai.in"),
]


# ─── Seen-story deduplication ─────────────────────────────────────────────────

def _load_seen() -> dict:
    """Load breaking news seen state from WordPress (persists across ephemeral runners)."""
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/tmt/v1/state/get",
            json={"secret": TMT_SECRET, "name": "breaking_seen"},
            timeout=10,
        )
        if r.ok:
            data = r.json().get("value")
            if data:
                return data
    except Exception:
        pass
    return {"published": [], "daily": {}}

def _save_seen(data: dict):
    """Persist breaking news seen state to WordPress."""
    try:
        requests.post(
            f"{WP_URL}/wp-json/tmt/v1/state/set",
            json={"secret": TMT_SECRET, "name": "breaking_seen", "value": data},
            timeout=10,
        )
    except Exception:
        pass

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
    logo_w = int(img.width * 0.09)
    logo_h = int(logo.height * (logo_w / logo.width))
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    r, g, b, a = logo.split()
    a = a.point(lambda p: int(p * 0.80))
    logo = Image.merge("RGBA", (r, g, b, a))
    pad = 18
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

def fetch_unsplash_image(query: str) -> bytes | None:
    """Search Unsplash for free-to-use images (Unsplash License — commercial use allowed, no attribution required). Always watermarks."""
    if not UNSPLASH_KEY:
        return None
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            params={
                "query":          query,
                "orientation":    "landscape",
                "per_page":       10,
                "content_filter": "high",
                "page":           random.randint(1, 5),
            },
            timeout=15,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None
        candidates = list(results[:6])
        random.shuffle(candidates)
        for photo in candidates:
            img_url = photo["urls"]["regular"]
            try:
                img_r = requests.get(img_url, timeout=20)
                if not img_r.ok or len(img_r.content) < 10_000:
                    continue
                img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
                if img.width < 400 or img.height < 300:
                    continue
                img = resize_image(img)
                img = add_watermark(img)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=90)
                log.info(f"  Unsplash image: {photo.get('id','')} by {photo.get('user',{}).get('name','')}")
                return buf.getvalue()
            except Exception:
                continue
        return None
    except Exception as e:
        log.warning(f"Unsplash fetch failed: {e}")
        return None


def extract_source_image(url: str, direct_img_url: str = "") -> bytes | None:
    """Download the OG image from a story.
    If direct_img_url is provided (e.g. from News API), use it directly instead of scraping."""
    if not url and not direct_img_url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TMTBot/1.0)"}
        img_url = direct_img_url
        if not img_url:
            from bs4 import BeautifulSoup
            r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if not r.ok:
                return None
            soup = BeautifulSoup(r.text, "lxml")
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
        log.info(f"  Source image from {'direct URL' if direct_img_url else url[:60]}")
        return buf.getvalue()
    except Exception as e:
        log.warning(f"Source image extraction failed: {e}")
        return None

def make_fallback_image(title: str) -> bytes:
    img = Image.new("RGB", (1200, 628), color=(10, 22, 40))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()

def upload_image_to_wp(img_bytes: bytes, filename: str, alt: str,
                       img_title: str = "") -> int | None:
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={
                "Authorization":       f"Basic {creds}",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type":        "image/jpeg",
            },
            data=img_bytes,
            timeout=60,
        )
        r.raise_for_status()
        media_id = r.json()["id"]
        requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            headers={"Authorization": f"Basic {creds}", "Content-Type": "application/json"},
            json={
                "alt_text": alt[:125],
                "title":    alt[:125],   # use full alt so Foxiz theme renders correct alt attribute
                "caption":  "© The Mobile Times",
            },
            timeout=15,
        )
        return media_id
    except Exception as e:
        log.warning(f"Image upload failed: {e}")
        return None


# ─── RSS Polling ──────────────────────────────────────────────────────────────

def _fetch_recent_wp_titles() -> list[str]:
    """Fetch titles of posts published in the last 24h — cached once per poll."""
    try:
        after = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {creds}"},
            params={"per_page": 20, "status": "publish", "_fields": "title", "after": after},
            timeout=10,
        )
        if r.ok:
            return [re.sub(r"<[^>]+>", "", p["title"]["rendered"]).lower() for p in r.json()]
    except Exception:
        pass
    return []

def _title_overlaps(title: str, recent_titles: list[str], threshold: float = 0.6) -> bool:
    STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "are",
                 "was", "has", "its", "have", "will", "india", "2026"}
    title_words = set(re.findall(r"\b\w{3,}\b", title.lower())) - STOPWORDS
    for pub_title in recent_titles:
        pub_words = set(re.findall(r"\b\w{3,}\b", pub_title)) - STOPWORDS
        if not pub_words:
            continue
        overlap = len(title_words & pub_words) / max(len(title_words), 1)
        if overlap >= threshold:
            log.info(f"  WP dedup: skipping '{title[:55]}' ({overlap:.0%} overlap with recent post)")
            return True
    return False

BREAKING_WINDOW_HOURS = 3   # only consider stories published in the last N hours

def _entry_is_fresh(entry) -> bool:
    """Return True if the RSS entry was published within BREAKING_WINDOW_HOURS."""
    import calendar
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            pub_utc = datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
            age = datetime.now(timezone.utc) - pub_utc
            return age.total_seconds() <= BREAKING_WINDOW_HOURS * 3600
    # No timestamp — include it (some feeds omit dates)
    return True

def poll_rss() -> list[dict]:
    stories = []
    seen_hashes = set()
    # Load state and recent WP posts ONCE for the whole poll (not per-story)
    seen_data = _load_seen()
    seen_published = set(seen_data.get("published", []))
    recent_wp_titles = _fetch_recent_wp_titles()
    stale_count = 0
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                if not title or not link:
                    continue
                # Skip anything older than BREAKING_WINDOW_HOURS
                if not _entry_is_fresh(entry):
                    stale_count += 1
                    continue
                h = _story_hash(title)
                if h in seen_hashes or h in seen_published:
                    continue
                if _title_overlaps(title, recent_wp_titles):
                    continue
                seen_hashes.add(h)
                summary = re.sub(r"<[^>]+>", " ", summary)[:600].strip()
                stories.append({"title": title, "summary": summary, "url": link,
                                 "source": feed.feed.get("title", url)})
        except Exception as e:
            log.debug(f"RSS feed failed ({url}): {e}")
    log.info(f"RSS poll: {len(stories)} fresh stories ({stale_count} older than {BREAKING_WINDOW_HOURS}h skipped)")
    return stories



def fetch_all_breaking_stories() -> list[dict]:
    """RSS-only breaking story feed. News API removed to preserve daily quota for slots."""
    stories = poll_rss()
    log.info(f"Total breaking candidates: {len(stories)}")
    return stories


# ─── Story Scoring ────────────────────────────────────────────────────────────

BREAKING_KEYWORDS = [
    # ── Urgency signals ──────────────────────────────────────────────────────
    "breaking", "urgent", "just in", "exclusive", "alert", "live",
    "first", "new", "latest", "official", "confirmed",

    # ── Action verbs ─────────────────────────────────────────────────────────
    "launches", "launch", "announces", "announced", "unveils", "unveiled",
    "acquires", "acquired", "merger", "merges", "partners", "partnership",
    "raises", "raised", "invests", "invested", "funding", "ipo",
    "fined", "penalty", "penalised", "arrested", "raided", "seized",
    "banned", "ban", "blocked", "shutdown", "suspended", "revoked",
    "outage", "down", "breach", "hack", "hacked", "leak", "leaked",
    "cuts", "layoffs", "fired", "resigns", "resigned", "appoints", "appointed",
    "hikes", "hike", "reduces", "slashes", "price cut", "price hike",
    "record", "highest", "lowest", "first ever", "largest", "biggest",

    # ── Indian telecom operators ──────────────────────────────────────────────
    "jio", "airtel", "bsnl", "vi", "vodafone idea", "vodafone",
    "mtnl", "tata communications", "tata tele", "reliance",

    # ── Regulators & government bodies ───────────────────────────────────────
    "trai", "dot", "doi", "meity", "mnre", "cci", "sebi", "rbi",
    "supreme court", "high court", "parliament", "government", "ministry",
    "telecom bill", "digital india", "bharat net", "pm wani",

    # ── Global telcos & tech giants ───────────────────────────────────────────
    "samsung", "apple", "xiaomi", "realme", "oppo", "vivo", "oneplus",
    "google", "meta", "microsoft", "amazon", "tesla", "spacex", "starlink",
    "nokia", "ericsson", "huawei", "qualcomm", "mediatek", "snapdragon",

    # ── Technology terms ──────────────────────────────────────────────────────
    "5g", "6g", "4g", "lte", "volte", "fiber", "fibre", "broadband",
    "spectrum", "spectrum auction", "satellite", "leo", "esim",
    "ai", "artificial intelligence", "cybersecurity", "ransomware",
    "smartphone", "chip", "processor", "iot",

    # ── Business metrics ──────────────────────────────────────────────────────
    "crore", "lakh", "billion", "million", "revenue", "profit", "loss",
    "subscribers", "subscriber", "market share", "quarterly", "results",
    "agr", "dues", "license fee",

    # ── India signals ─────────────────────────────────────────────────────────
    "india", "indian", "delhi", "mumbai", "bangalore", "hyderabad",
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

    # Hard-stop: unfilled placeholders mean the template wasn't completed
    placeholders = re.findall(r"\[(?!a |/a)[^\]]{3,60}\]", content)
    if placeholders:
        raise ValueError(f"Unfilled placeholders in breaking content: {placeholders[:3]}. Aborting.")

    # Hard-stop: article too short
    word_count = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", content)))
    if word_count < 500:
        raise ValueError(f"Breaking article too short: {word_count} words (min 500). Aborting.")

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

━━ HUMANIZATION RULES (CRITICAL — AI DETECTION PREVENTION) ━━
• Write like a real journalist. Specific facts, company names, and numbers — not vague claims.
• BANNED PHRASES (AI tells — never use): "In today's fast-paced world", "In conclusion", "Furthermore", "It is worth noting", "delve into", "landscape", "game-changer", "revolutionize", "paradigm shift", "leverage", "cutting-edge", "seamlessly", "robust solution", "Additionally", "Moreover", "It is important to note", "It is crucial to", "plays a crucial role", "plays a key role", "When it comes to", "In terms of", "This ensures that", "This allows", "not only...but also", "In summary", "To summarize", "At the end of the day", "shed light on", "underscore", "holistic", "synergy", "ecosystem".
• BANNED PUNCTUATION — never use em dashes (—) anywhere in the article or title. Rewrite as a new sentence instead.
• BANNED SENTENCE STARTERS — never begin 3 consecutive sentences with the same word. Never start a sentence with "This" followed by a verb ("This means", "This shows", "This highlights").
• No opinions or editorialising. Report facts only.
• No passive voice openers. Subject first, then action.
• Vary sentence length: mix short punchy sentences (8–12 words) with detailed ones (22–28 words).
• Name specific companies, people, prices, and dates — never "industry observers" or "market players".

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
META_JSON:{{"article_title":"[title]","slug":"[slug]-2026","focus_keyword":"[2-4 words]","meta_title":"[50-60 chars | The Mobile Times]","meta_description":"[120-155 chars MUST contain focus keyword — NO em dashes]","og_title":"[60-70 chars]","og_description":"[180-200 chars]","category":"[one of: 5g-networks, industry-trends, ott-streaming, ev-smart-grids, internet-of-things, tech-innovation, policy-updates, market-trends]","faq":[{{"q":"[Q1]","a":"[A1]"}},{{"q":"[Q2]","a":"[A2]"}},{{"q":"[Q3]","a":"[A3]"}}]}}"""

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
        link_parts.append(f'<a href="{url}" target="_blank" rel="noopener">{name} ↗</a>')
    source_html = ' | '.join(link_parts)
    old_src = '<p class="tmt-sources"><strong>Sources:</strong>'
    new_src = f'<p class="tmt-sources"><strong>Sources:</strong> {source_html}'
    html_content = html_content.replace(old_src, new_src, 1) if old_src in html_content else html_content + f'\n{new_src}</p>'

    slug     = meta.get("slug", re.sub(r"[^a-z0-9-]", "", kw.lower().replace(" ", "-")))
    meta_t   = meta.get("meta_title",   f"{title[:50]} | The Mobile Times")
    meta_d   = meta.get("meta_description", f"Breaking: {kw} news from India.")
    og_title = meta.get("og_title",     meta_t)
    og_desc  = meta.get("og_description", meta_d)
    cat_slug = meta.get("category", "industry-trends")

    if kw.lower() not in meta_d.lower():
        meta_d = f"{kw}: {meta_d}"[:155]

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
    requests.post(
        f"{WP_URL}/wp-json/tmt/v1/update-meta",
        json={
            "secret":     TMT_SECRET,
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
            },
        },
        timeout=15,
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
        "featured_media": media_id or 0,
        "sticky":         False,
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=WP_HDR, json=payload, timeout=30)
    if r.ok:
        post = r.json()
        save_rank_math_meta(post["id"], post_data)
        return post
    log.error(f"Breaking publish failed ({r.status_code}): {r.text[:200]}")
    return None

def seed_post_views(post_id: int):
    """Seed a random view count (300–2000) on a newly published post via tmt-admin-api."""
    if not post_id:
        return
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/tmt/v1/views/seed",
            json={"secret": TMT_SECRET, "post_id": post_id},
            timeout=10,
        )
        if r.ok:
            data = r.json()
            log.info(f"  Views seeded: {data.get('count')} (meta: {data.get('meta_key')})")
        else:
            log.warning(f"  Views seed responded {r.status_code}")
    except Exception as e:
        log.warning(f"Views seed failed: {e}")


def ping_indexing(post_url: str):
    try:
        if INDEXNOW_KEY:
            requests.get("https://api.indexnow.org/indexnow",
                         params={"url": post_url, "key": INDEXNOW_KEY}, timeout=5)
        requests.get("https://www.google.com/ping",
                     params={"sitemap": f"{WP_URL}/sitemap.xml"}, timeout=5)
        # Flush LiteSpeed Cache via tmt-admin-api plugin
        r = requests.post(
            f"{WP_URL}/wp-json/tmt/v1/cache/flush",
            json={"secret": TMT_SECRET},
            timeout=10,
        )
        if r.ok:
            log.info("  Cache flushed via tmt-admin-api")
        else:
            log.warning(f"  Cache flush responded {r.status_code}")
    except Exception as e:
        log.warning(f"Ping failed: {e}")


# ─── Main Scan Loop ───────────────────────────────────────────────────────────

def run_scan():
    now_ist  = datetime.now(IST)
    date_str = now_ist.isoformat()

    count_today = get_today_count()
    if count_today >= MAX_BREAKING_PER_DAY:
        log.info(f"Daily cap reached ({count_today}/{MAX_BREAKING_PER_DAY}) — skipping scan")
        return

    stories = fetch_all_breaking_stories()
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
        extract_source_image(best.get("url", ""), best.get("_og_image", "")) or
        fetch_unsplash_image(post_data["focus_keyword"]) or
        fetch_pexels_image(post_data["focus_keyword"]) or
        make_fallback_image(best["title"])
    )
    today_str = now_ist.strftime("%Y-%m-%d")
    kw_fn     = re.sub(r"[^a-z0-9-]", "", post_data["focus_keyword"].lower().replace(" ", "-"))
    filename  = f"{kw_fn}-breaking-{today_str}.jpg"
    img_alt   = f"{post_data['title']} | The Mobile Times"
    media_id  = upload_image_to_wp(img_bytes, filename, img_alt,
                                   img_title=post_data["focus_keyword"])

    result = publish_breaking_post(post_data, media_id)
    if result:
        post_url = result.get("url", result.get("link", ""))
        log.info(f"  BREAKING PUBLISHED: {post_url}")
        mark_published(best["title"])
        seed_post_views(result.get("id"))
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
