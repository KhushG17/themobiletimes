"""
mobiletimes_agent.py — The Mobile Times Daily Automation Engine

Publishes 5 posts per day via GitHub Actions cron (08:00, 10:00, 12:00, 15:00, 18:00 IST):
  Slots 1–4: News posts — AI picks the best story from all categories dynamically
  Slot 5:    Blog / Insights — rotates 15 weekly topics covering Indian telecom

Category is dynamic — Claude Haiku routes each story to the best fitting category
from all 24 categories. No fixed slot→category mapping.

Breaking news (up to 3/day, score ≥ 65) is handled separately by breaking_monitor.py.

Usage:
  python mobiletimes_agent.py --slot N            # Run single slot (1–4 = news, 5 = blog)
  python mobiletimes_agent.py --run-now           # Run all 5 slots immediately
  python mobiletimes_agent.py --single "topic"    # Publish one article on a specific topic
  python mobiletimes_agent.py --url "https://..."  # Rewrite and publish from a source URL
  python mobiletimes_agent.py --tip "hint"         # Inject a manual tip into slot 1 story selection
  python mobiletimes_agent.py --test-post          # Publish 1 draft post for testing
"""

import os, sys, re, json, base64, time, random, io, argparse, logging, hashlib
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

# ─── Config ──────────────────────────────────────────────────────────────────

WP_URL        = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER       = os.getenv("WP_USER")
WP_PASS       = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
PEXELS_KEY    = os.getenv("PEXELS_API_KEY")
FAL_KEY       = os.getenv("FAL_API_KEY")
NEWS_API_KEY  = os.getenv("NEWS_API_KEY", "")
TMT_SECRET    = os.getenv("TMT_SECRET", "")
LOGO_PATH     = os.getenv("LOGO_PATH", "assets/Circle_Logo.png")
INDEXNOW_KEY  = os.getenv("INDEXNOW_KEY", "")
UNSPLASH_KEY   = os.getenv("UNSPLASH_ACCESS_KEY", "")

AUTHOR_NAME    = "Sanjay Goyal"
AUTHOR_URL     = "https://themobiletimes.com/author/sanjay/"
POST_TIMES_IST = ["08:00", "10:00", "12:00", "15:00", "18:00"]  # IST publish slots

IST           = pytz.timezone("Asia/Kolkata")
creds         = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
WP_HDR        = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tmt_agent.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("tmt")

_recent_posts_cache: list[dict] = []   # populated once per run_daily(); used by inject_related_links
_seen_urls: set = set()               # populated once per run_daily(); URL-level dedup


def load_seen_urls() -> set:
    """Load previously processed story URLs from WordPress state (tmt-admin-api)."""
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/tmt/v1/state/get",
            json={"secret": TMT_SECRET, "name": "seen_urls"},
            timeout=10,
        )
        if r.ok:
            data = r.json().get("value") or {}
            return set(data.get("urls", []))
    except Exception as e:
        log.warning(f"load_seen_urls failed: {e}")
    return set()


def save_seen_urls(new_urls: set):
    """Append new story URLs to WP state, keeping last 2,000."""
    existing = load_seen_urls()
    merged   = list(existing | new_urls)[-2000:]
    try:
        requests.post(
            f"{WP_URL}/wp-json/tmt/v1/state/set",
            json={"secret": TMT_SECRET, "name": "seen_urls", "value": {"urls": merged}},
            timeout=10,
        )
    except Exception as e:
        log.warning(f"save_seen_urls failed: {e}")


_used_unsplash_ids: set[str] = set()   # in-memory dedup for this run

def load_pexels_ids() -> set:
    """Load previously used Pexels photo IDs from WordPress state (persists across ephemeral runners)."""
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/tmt/v1/state/get",
            json={"secret": TMT_SECRET, "name": "pexels_used_ids"},
            timeout=10,
        )
        if r.ok:
            data = r.json().get("value") or {}
            return set(data.get("ids", []))
    except Exception:
        pass
    return set()


def save_pexels_id(photo_id: int):
    """Persist a used Pexels photo ID to WordPress state, keeping last 1,000."""
    ids = load_pexels_ids()
    ids.add(photo_id)
    try:
        requests.post(
            f"{WP_URL}/wp-json/tmt/v1/state/set",
            json={"secret": TMT_SECRET, "name": "pexels_used_ids",
                  "value": {"ids": list(ids)[-1000:]}},
            timeout=10,
        )
    except Exception:
        pass

# ─── Category & Tag IDs (fetched from WP audit) ──────────────────────────────

CATEGORY_IDS = {
    "5g-networks":            160,
    "accessories-wearables":  151,
    "ai-machine-learning":    156,
    "ar-vr":                  163,
    "case-studies":           143,
    "cybersecurity":          155,
    "data-analytics":         157,
    "devices-hardware":       129,
    "ev-smart-grids":         164,
    "exclusive":              121,
    "how-to-guides":          142,
    "industry-insights":      141,
    "industry-trends":        159,
    "insights":               140,
    "internet-of-things":     165,
    "market-trends":          123,
    "network-smart-devices":  152,
    "ott-streaming":          162,
    "policy-updates":         122,
    "press-releases":         144,
    "smartphones-tablets":    150,
    "software":               154,
    "tech-innovation":        161,
    "technologies":           153,
}

TAG_IDS = {
    "trending":      167,
    "breaking-news": 166,
    "new-launch":    169,
}

NEWS_WORD_TARGET  = "600-750"   # news articles: punchy, scannable
BLOG_WORD_TARGET  = "900-1000"  # blog/insights: authoritative long-form

WEEKLY_BLOG_TOPICS = {
    0: ("Jio vs Airtel 2026: Who Is Really Winning the Indian Telecom War?",                "industry-insights"),
    1: ("Why India's 5G Rollout Is Slower Than Promised — And What Must Change",            "industry-insights"),
    2: ("BSNL's Revival Plan: A Genuine Comeback or Too Little Too Late?",                  "case-studies"),
    3: ("How AI Is Reshaping Customer Service Across Indian Telecom in 2026",               "industry-insights"),
    4: ("The OTT Battleground: Can Indian Platforms Beat Netflix and Amazon?",              "industry-insights"),
    5: ("Satellite Internet in India: Starlink, OneWeb and Rural Connectivity 2026",        "industry-insights"),
    6: ("India's Smartphone Market in 2026: Rise of Premium, Fall of Budget Phones",        "industry-insights"),
    7: ("5G vs Wi-Fi 7 in India: Which Will Define Connectivity in 2026?",                  "industry-insights"),
    8: ("Why India's Cybersecurity Spending Must Triple by 2027",                            "industry-insights"),
    9: ("TRAI's New Rules in 2026: Winners, Losers, and What Changes for You",              "policy-updates"),
    10: ("How Indian Startups Are Beating Big Telcos at Their Own Game",                     "industry-insights"),
    11: ("The Hidden Cost of India's Data Boom: Infrastructure, Energy, and Water",         "case-studies"),
    12: ("Reliance Jio's Next Big Bet: What the Market Is Missing",                         "market-trends"),
    13: ("Edge Computing in India: The Silent Revolution Operators Are Ignoring",           "industry-insights"),
    14: ("India's IoT Market Will Hit $35 Billion by 2026 — Who Captures It?",             "industry-insights"),
}

RSS_FEEDS = [
    # ── India telecom & tech (primary) ───────────────────────────────────────
    "https://economictimes.indiatimes.com/tech/telecom/rssfeeds/13357270.cms",
    "https://telecomtalk.info/feed/",
    "https://www.medianama.com/feed/",
    "https://entrackr.com/feed/",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://www.91mobiles.com/feed/",
    "https://www.digit.in/rss.xml",
    "https://www.androidauthority.com/feed/",
    # ── India business & financial tech ──────────────────────────────────────
    "https://www.livemint.com/rss/technology",
    "https://www.business-standard.com/rss/technology-10602.rss",
    "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
    "https://inc42.com/feed/",
    "https://yourstory.com/feed",
    "https://www.financialexpress.com/industry/technology/feed/",
    "https://www.ndtv.com/convergence/ndtv/feeds/tech_news.xml",
    "https://timesofindia.indiatimes.com/rss.cms?msid=66949542",
    # ── Global telecom ────────────────────────────────────────────────────────
    "https://www.lightreading.com/rss.xml",
    "https://www.fiercetelecom.com/rss.xml",
    "https://www.telecompaper.com/rss/all-news.xml",
    "https://www.rcrwireless.com/feed",
    "https://www.totaltele.com/rss",
    "https://telecoms.com/feed/",
    "https://www.mobileworldlive.com/feed/",
    "https://www.capacitymedia.com/rss",
    # ── Cybersecurity ─────────────────────────────────────────────────────────
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.darkreading.com/rss.xml",
    # ── AI & global tech ──────────────────────────────────────────────────────
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://thenextweb.com/feed/",
    "https://www.technologyreview.com/feed/",
    # ── Policy & regulation ───────────────────────────────────────────────────
    "https://telecomregulatoryauthority.wordpress.com/feed/",
    "https://dot.gov.in/feeds/all/rss.xml",
    # ── Devices & consumer ────────────────────────────────────────────────────
    "https://www.gsmarena.com/rss-news-articles.php3",
    "https://www.notebookcheck.net/News.40.0.html?id=&txt=&mark=0&archive=0&type=0&typemax=255&or=0&perpage=50&rss=1",
    # ── Google News India (trending-sorted) ───────────────────────────────────
    "https://news.google.com/rss/search?q=telecom+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=5G+smartphone+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=jio+airtel+technology&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=cybersecurity+ai+india&hl=en-IN&gl=IN&ceid=IN:en",
]

# Queries for News API (newsapi.org) — India-telecom focused
NEWS_API_QUERIES = [
    "5G India telecom",
    "Jio Airtel BSNL India telecom",
    "TRAI India regulation spectrum",
    "smartphone launch India 2026",
    "cybersecurity India tech",
]

INTERNAL_LINKS = {
    "5G":             "/category/industry-trends/5g-networks/",
    "cybersecurity":  "/category/technologies/cybersecurity/",
    " AI ":           "/category/technologies/ai-machine-learning/",
    "smartphones":    "/category/devices-hardware/smartphones-tablets/",
    "IoT":            "/category/industry-trends/internet-of-things/",
    "OTT":            "/category/industry-trends/ott-streaming/",
    "telecom policy": "/category/policy-updates/",
    "market trends":  "/category/market-trends/",
    "wearables":      "/category/devices-hardware/accessories-wearables/",
    "data analytics": "/category/technologies/data-analytics/",
    " EV ":           "/category/industry-trends/ev-smart-grids/",
    "software":       "/category/technologies/software/",
}

AUTHORITY_LINKS = [
    ("TRAI",     "https://www.trai.gov.in"),
    ("DOT",      "https://dot.gov.in"),
    ("GSMA",     "https://www.gsma.com"),
    ("COAI",     "https://www.coai.in"),
    ("ITU",      "https://www.itu.int"),
    ("Ericsson", "https://www.ericsson.com/en/reports-and-papers"),
]

# Category → Unsplash/Pexels search term for body images
_CAT_TO_SEARCH: dict[str, str] = {
    "5g-networks":        "5G network India",
    "smartphones-tablets":"smartphone India",
    "cybersecurity":      "cybersecurity data",
    "ai-machine-learning":"artificial intelligence",
    "policy-updates":     "India government policy",
    "market-trends":      "India business market",
    "industry-insights":  "telecom India industry",
    "tech-innovation":    "technology innovation",
    "ott-streaming":      "streaming video India",
    "ev-smart-grids":     "electric vehicle India",
    "internet-of-things": "IoT smart devices",
    "software":           "software technology",
}

# Source credibility scores (0–100). Used to weight story selection.
# Higher = more authoritative. Checked via case-insensitive substring of source name/URL.
SOURCE_AUTHORITY: dict[str, int] = {
    # India national business / financial press
    "economic times":   92,  "economictimes":    92,
    "live mint":        90,  "livemint":         90,
    "business standard":88,  "business-standard":88,
    "financial express":85,  "financialexpress": 85,
    "the hindu":        85,  "thehindu":         85,
    "ndtv":             82,
    "times of india":   82,  "timesofindia":     82,
    # India tech / telecom specialist
    "medianama":        80,
    "telecomtalk":      78,
    "gadgets 360":      76,  "gadgets360":       76,
    "inc42":            75,
    "91mobiles":        72,
    "digit.in":         70,  "digit":            70,
    "yourstory":        68,
    "entrackr":         67,
    # Global tier-1 tech
    "techcrunch":       80,
    "wired":            78,
    "technology review":75,  "technologyreview": 75,
    "venturebeat":      72,
    "android authority":70,  "androidauthority": 70,
    "thenextweb":       68,  "the next web":     68,
    "notebookcheck":    65,
    # Global telecom specialist
    "light reading":    73,  "lightreading":     73,
    "fierce telecom":   70,  "fiercetelecom":    70,
    "rcrwireless":      68,
    "telecompaper":     66,
    "mobile world live":65,  "mobileworldlive":  65,
    "telecoms.com":     62,
    "total telecom":    60,  "totaltele":        60,
    "capacity media":   58,  "capacitymedia":    58,
    # Cybersecurity specialists
    "hacker news":      72,  "thehackernews":    72,
    "bleeping computer":70,  "bleepingcomputer": 70,
    "dark reading":     68,  "darkreading":      68,
    # Government / standards bodies
    "trai.gov":         95,  "dot.gov":          95,
    "gsma":             90,  "itu.int":          90,
    "gsmarena":         70,
}

def get_source_score(source: str) -> int:
    """Return credibility score 0–100 for a source name or URL. Default 50."""
    s = source.lower()
    for key, score in SOURCE_AUTHORITY.items():
        if key in s:
            return score
    return 50


# ─── Logo Watermark ──────────────────────────────────────────────────────────

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
    logo_w = int(img.width * 0.09)   # 9% — subtle but visible
    logo_h = int(logo.height * (logo_w / logo.width))
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

    # Apply 80% opacity
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
    new_w = int(img.width  * ratio)
    new_h = int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top  = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))

def make_fallback_image(title: str) -> bytes:
    img = Image.new("RGB", (1200, 628), color=(10, 22, 40))
    try:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        # Red bottom bar
        draw.rectangle([(0, 620), (1200, 628)], fill=(204, 0, 0))
        # Title text (truncated)
        text = title[:80]
        draw.text((600, 280), text, fill="white", anchor="mm")
        # Tagline
        draw.text((600, 560), "The Mobile Times | India's Telecom Authority", fill=(180, 180, 180), anchor="mm")
    except Exception:
        pass
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


# ─── Image Fetching ───────────────────────────────────────────────────────────

def fetch_pexels_image(keyword: str, watermark: bool = True) -> bytes | None:
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": f"{keyword} India technology", "per_page": 8, "orientation": "landscape"},
            timeout=15
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None
        # Prefer photos not used before; fall back to any if all used
        seen_ids = load_pexels_ids()
        fresh = [p for p in photos[:6] if p["id"] not in seen_ids]
        photo = random.choice(fresh[:3]) if fresh else random.choice(photos[:3])
        save_pexels_id(photo["id"])
        img_url = photo["src"]["large2x"]
        img_r = requests.get(img_url, timeout=20)
        img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
        img = resize_image(img)
        if watermark:
            img = add_watermark(img)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        log.warning(f"Pexels fetch failed: {e}")
        return None

def fetch_fal_image(topic: str) -> bytes | None:
    try:
        import fal_client
        os.environ["FAL_KEY"] = FAL_KEY
        result = fal_client.run(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": f"Professional editorial tech magazine photograph for article about {topic}. Clean, modern, high quality. No text, no watermarks, no faces.",
                "image_size": "landscape_16_9",
                "num_inference_steps": 4,
                "num_images": 1,
            }
        )
        images = result.get("images", [])
        if not images:
            return None
        img_url = images[0]["url"]
        img_r = requests.get(img_url, timeout=30)
        img = Image.open(io.BytesIO(img_r.content)).convert("RGB")
        img = resize_image(img)
        img = add_watermark(img)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except Exception as e:
        log.warning(f"fal.ai fetch failed: {e}")
        return None

def fetch_unsplash_image(query: str, watermark: bool = True) -> bytes | None:
    """Search Unsplash for free-to-use images (Unsplash License — commercial use allowed, no attribution required)."""
    global _used_unsplash_ids
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
        fresh = [p for p in results if p["id"] not in _used_unsplash_ids]
        candidates = fresh[:6] if fresh else results[:6]
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
                if watermark:
                    img = add_watermark(img)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=90)
                _used_unsplash_ids.add(photo["id"])
                log.info(f"  Unsplash image: {photo.get('id','')} by {photo.get('user',{}).get('name','')}")
                return buf.getvalue()
            except Exception:
                continue
        return None
    except Exception as e:
        log.warning(f"Unsplash fetch failed: {e}")
        return None


def fetch_article_from_url(url: str) -> dict | None:
    """Scrape title, summary, and OG data from a source article URL."""
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TMTBot/1.0; +https://themobiletimes.com)"}
        r = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if not r.ok:
            log.warning(f"fetch_article_from_url: HTTP {r.status_code} for {url}")
            return None
        soup = BeautifulSoup(r.text, "lxml")

        # Title — prefer OG, then <title>
        og_title = soup.find("meta", property="og:title")
        title = og_title["content"].strip() if og_title and og_title.get("content") else ""
        if not title:
            t = soup.find("title")
            title = t.get_text(strip=True) if t else ""

        # Description — OG description or meta description
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        desc = og_desc["content"].strip() if og_desc and og_desc.get("content") else ""

        # Body text — try article tag, then largest text block
        article = soup.find("article") or soup.find("main") or soup.body
        paragraphs = article.find_all("p") if article else []
        body_text = " ".join(p.get_text(" ", strip=True) for p in paragraphs[:6])
        summary = (desc or body_text)[:600].strip()

        if not title:
            log.warning(f"fetch_article_from_url: could not extract title from {url}")
            return None

        source_name = soup.find("meta", property="og:site_name")
        source = source_name["content"] if source_name and source_name.get("content") else url[:40]

        return {"title": title, "summary": summary, "url": url, "source": source}
    except Exception as e:
        log.warning(f"fetch_article_from_url failed ({url[:50]}): {e}")
        return None


def extract_source_image(url: str, direct_img_url: str = "") -> bytes | None:
    """Download the OG image from a story.
    If direct_img_url is provided (e.g. from News API), use it directly instead of scraping."""
    if not url and not direct_img_url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TMTBot/1.0; +https://themobiletimes.com)"}
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
        log.warning(f"Source image extraction failed ({url[:50]}): {e}")
        return None


def upload_image_to_wp(img_bytes: bytes, filename: str, alt: str,
                       img_title: str = "") -> tuple[int | None, str | None]:
    """Upload image via WP REST API with Application Password auth."""
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={
                "Authorization":      f"Basic {creds}",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type":       "image/jpeg",
            },
            data=img_bytes,
            timeout=60,
        )
        r.raise_for_status()
        rj = r.json()
        media_id = rj["id"]
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
        return media_id, rj.get("source_url", "")
    except Exception as e:
        log.warning(f"Image upload failed: {e}")
        return None, None


# ─── RSS & Story Selection ────────────────────────────────────────────────────

def get_published_titles(limit: int = 100) -> set[str]:
    """Fetch recent published post titles for duplicate detection."""
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {creds}"},
            params={"per_page": min(limit, 100), "status": "publish,draft",
                    "_fields": "title,slug"},
            timeout=15,
        )
        if not r.ok:
            return set()
        titles = set()
        for p in r.json():
            t = re.sub(r"<[^>]+>", "", p["title"]["rendered"]).lower().strip()
            titles.add(t)
            titles.add(p["slug"].replace("-", " "))
        return titles
    except Exception:
        return set()


def is_duplicate(story_title: str, published: set[str], threshold: float = 0.55) -> bool:
    """Return True if story title has high word-overlap with a recently published post.

    Threshold raised to 0.55 to avoid false positives on generic words.
    Semantic duplicate detection is handled separately by batch_semantic_dedup().
    """
    title = story_title.lower().strip()
    STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "are",
                 "was", "has", "its", "have", "will", "india", "2026", "2025",
                 "new", "how", "why", "who", "what", "now", "first", "last"}
    words = set(re.findall(r"\b\w{3,}\b", title)) - STOPWORDS
    if not words:
        return False

    for pub in published:
        pub_words = set(re.findall(r"\b\w{3,}\b", pub)) - STOPWORDS
        if not pub_words:
            continue
        overlap = len(words & pub_words) / max(len(words), 1)
        if overlap >= threshold:
            log.info(f"  Skipping duplicate: '{story_title[:60]}' ({overlap:.0%} overlap)")
            return True

    return False


def batch_semantic_dedup(stories: list[dict], published: set[str]) -> list[dict]:
    """Use Claude Haiku to remove stories covering the same event as recently published posts.

    One API call per slot — costs ~₹8-10/month total.
    """
    if not stories or not published:
        return stories

    story_titles = [s["title"] for s in stories]
    pub_list = list(published)[:60]  # cap to avoid token overflow

    prompt = (
        "You are a news deduplication assistant. I'll give you two lists:\n"
        "A) Candidate story titles (numbered)\n"
        "B) Recently published post titles\n\n"
        "Task: For each candidate in list A, flag it if it covers the SAME SPECIFIC EVENT "
        "as any title in list B — meaning the same company doing the same thing on the same topic. "
        "Two stories about the same company doing DIFFERENT things are NOT duplicates. "
        "Only flag if the core news event is essentially identical.\n\n"
        "Output ONLY a JSON array of the numbers to EXCLUDE (e.g. [2,5,9]). "
        "Empty array [] if none are duplicates. No explanation.\n\n"
        "LIST A — Candidates:\n"
    )
    for i, t in enumerate(story_titles, 1):
        prompt += f"{i}. {t}\n"
    prompt += "\nLIST B — Recently published:\n"
    for t in pub_list:
        prompt += f"- {t}\n"

    try:
        import anthropic as _ant
        _hc = _ant.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = _hc.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        m = re.search(r"\[.*?\]", text, re.DOTALL)
        exclude = set(json.loads(m.group(0))) if m else set()
        kept = []
        for i, s in enumerate(stories, 1):
            if i in exclude:
                log.info(f"  Semantic dedup removed: '{s['title'][:60]}'")
            else:
                kept.append(s)
        log.info(f"  Semantic dedup: {len(stories) - len(kept)} removed, {len(kept)} remain")
        return kept
    except Exception as e:
        log.warning(f"Semantic dedup failed: {e} — skipping")
        return stories


def get_recent_posts(limit: int = 12) -> list[dict]:
    """Fetch recent published posts for inter-article linking."""
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {creds}"},
            params={"per_page": limit, "status": "publish", "_fields": "title,link"},
            timeout=15,
        )
        if not r.ok:
            return []
        return r.json()
    except Exception:
        return []


def inject_related_links(html: str) -> str:
    """Append a 'Related Reading' block using recent posts from the cache."""
    if not _recent_posts_cache:
        return html
    pool    = [p for p in _recent_posts_cache if p.get("link") and p.get("title")]
    sampled = random.sample(pool, min(3, len(pool)))
    items   = []
    for p in sampled:
        title = re.sub(r"<[^>]+>", "", p["title"]["rendered"]).strip()
        url   = p["link"]
        if title and url:
            items.append(f'  <li><a href="{url}">{title}</a></li>')
    if not items:
        return html
    block = (
        '\n<div class="tmt-related">\n<h3>Related Reading</h3>\n<ul>\n'
        + '\n'.join(items)
        + '\n</ul>\n</div>'
    )
    return html + block


def inject_auto_toc(html: str) -> str:
    """Auto-generate a TOC div before the first H2 for articles with 3+ sections and 800+ words.
    Skips if a tmt-toc block already exists (template already included one)."""
    if 'class="tmt-toc"' in html:
        return html
    word_count = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", html)))
    if word_count < 800:
        return html
    headings = re.findall(r'<h2[^>]*\bid="([^"]+)"[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)
    if len(headings) < 3:
        return html
    items = []
    for hid, htext in headings:
        clean = re.sub(r"<[^>]+>", "", htext).strip()
        if clean:
            items.append(f'<li><a href="#{hid}">{clean}</a></li>')
    toc = (
        '\n<div class="tmt-toc">\n<h3>In This Article</h3>\n<ol>\n'
        + '\n'.join(items)
        + '\n</ol>\n</div>\n'
    )
    first_h2 = re.search(r'<h2', html, re.IGNORECASE)
    if first_h2:
        return html[:first_h2.start()] + toc + html[first_h2.start():]
    return toc + html


def inject_body_image_html(html: str, img_url: str, alt_text: str) -> str:
    """Insert a body image figure after the first H2 section (before the second H2).
    Falls back to appending before the FAQ block if only one H2 exists."""
    if not img_url:
        return html
    figure = (
        f'\n<figure class="tmt-body-img" style="margin:1.5rem 0">'
        f'<img src="{img_url}" alt="{alt_text}" loading="lazy" style="width:100%;height:auto;border-radius:6px" />'
        f'<figcaption style="font-size:.82rem;color:#888;padding:4px 0">© The Mobile Times</figcaption>'
        f'</figure>\n'
    )
    h2_positions = [m.start() for m in re.finditer(r"<h2", html, re.IGNORECASE)]
    if len(h2_positions) >= 2:
        insert_at = h2_positions[1]
    else:
        # Fall back: insert before the People Also Ask / FAQ block
        faq_pos = html.find('<h3>People Also Ask')
        insert_at = faq_pos if faq_pos > 0 else len(html)
    return html[:insert_at] + figure + html[insert_at:]


def fetch_newsapi_stories() -> list[dict]:
    """Fetch recent India-telecom stories from newsapi.org. Falls back to [] on failure.
    Uses 3 queries per call (~15 req/day across 5 slots — well within 100/day free limit)."""
    if not NEWS_API_KEY:
        return []
    stories, seen_urls = [], set()
    from_date = (datetime.now(timezone.utc) - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for query in NEWS_API_QUERIES[:3]:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "language": "en",
                    "sortBy":   "publishedAt",
                    "pageSize": 10,
                    "from":     from_date,
                    "apiKey":   NEWS_API_KEY,
                },
                timeout=12,
            )
            if r.status_code == 426:
                log.warning("News API: upgrade required (too many requests)")
                break
            if not r.ok:
                log.warning(f"News API '{query}': HTTP {r.status_code}")
                continue
            for art in r.json().get("articles", []):
                url   = art.get("url", "")
                title = (art.get("title") or "").strip()
                if not url or not title or title == "[Removed]":
                    continue
                if url in seen_urls or url in _seen_urls:
                    continue
                seen_urls.add(url)
                desc    = art.get("description") or art.get("content") or ""
                summary = re.sub(r"<[^>]+>", " ", desc)[:600].strip()
                src_name = (art.get("source") or {}).get("name", "News API")
                stories.append({
                    "title":       title,
                    "summary":     summary,
                    "url":         url,
                    "source":      src_name,
                    "_og_image":   art.get("urlToImage"),
                    "credibility": get_source_score(src_name),
                })
        except Exception as e:
            log.warning(f"News API '{query}' error: {e}")
    log.info(f"News API: {len(stories)} stories fetched")
    return stories


def fetch_all_stories() -> list[dict]:
    """Fetch from News API (primary) + all RSS feeds (fallback/supplement)."""
    seen, stories = set(), []

    # Primary: News API
    api_stories = fetch_newsapi_stories()
    for s in api_stories:
        key = hashlib.md5(s["title"].encode()).hexdigest()
        if key not in seen and s["url"] not in _seen_urls:
            seen.add(key)
            stories.append(s)

    # Supplement / fallback: RSS feeds
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")
                if not title or not link:
                    continue
                key = hashlib.md5(title.encode()).hexdigest()
                if key in seen or link in _seen_urls:
                    continue
                seen.add(key)
                summary    = re.sub(r"<[^>]+>", " ", summary)[:600].strip()
                feed_title = feed.feed.get("title", url)
                stories.append({
                    "title":       title,
                    "summary":     summary,
                    "url":         link,
                    "source":      feed_title,
                    "credibility": get_source_score(feed_title),
                })
        except Exception as e:
            log.warning(f"RSS feed failed ({url}): {e}")

    log.info(f"Fetched {len(stories)} total stories (News API + RSS)")
    return stories

def get_trending_from_stories(stories: list[dict]) -> list[str]:
    """Extract trending entities from the already-fetched story pool.

    Counts capitalized words (brand/product names) across all headlines.
    Returns entities appearing in 3+ headlines — a free, always-working signal.
    """
    from collections import Counter
    SKIP = {"India", "The", "This", "That", "What", "New", "How", "Why",
            "When", "Its", "For", "Are", "Has", "Was", "Get", "Top", "Big",
            "Key", "Now", "All", "Can", "Says", "Here", "Into"}
    entity_counts: Counter = Counter()
    for s in stories:
        words = re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", s["title"])
        for w in words:
            if w not in SKIP:
                entity_counts[w] += 1
    trending = [w for w, c in entity_counts.most_common(20) if c >= 3][:5]
    if not trending:
        trending = [w for w, _ in entity_counts.most_common(5)]
    log.info(f"Trending from stories: {trending}")
    return trending

ALL_NEWS_CATEGORIES = ", ".join(k for k in CATEGORY_IDS if k not in ("exclusive",))

INSIGHTS_SUBCATEGORIES = ["industry-insights", "how-to-guides", "case-studies", "press-releases"]

def select_story_for_slot(stories: list[dict], slot: int, trending: list[str]) -> dict | None:
    """Select the best story for a single slot — dynamic category, no fixed slot constraint."""
    stories_json = json.dumps(
        [{"i": i, "title": s["title"], "summary": s["summary"][:200],
          "cred": s.get("credibility", 50)}
         for i, s in enumerate(stories)],
        indent=2
    )
    prompt = f"""You are the editor of The Mobile Times, India's leading telecom publication.

Today's trending keywords: {', '.join(trending)}

Pick the single most newsworthy, India-relevant story from the list below.

RULES:
- type: always "news"
- category: choose the best fitting one from: {ALL_NEWS_CATEGORIES}
- tags: exactly ONE from: trending, breaking-news, new-launch
    "breaking-news" = urgent, just happened, major impact
    "new-launch"    = product/service/policy launch or major announcement
    "trending"      = default for anything else
- is_breaking: true only if genuinely urgent (breaking outage, major regulatory action, etc.)
- focus_keyword: 2-4 word SEO keyword derived from the story
- Prioritise stories about India or Indian companies
- "cred" is source credibility (0–100). Prefer higher-credibility sources when stories are otherwise equal in news value. Never sacrifice relevance for credibility.

Stories:
{stories_json}

Respond with JSON only — no extra text:
{{"index":<i>,"type":"news","category":"<slug>","tags":["<tag>"],"is_breaking":false,"focus_keyword":"<2-4 words>"}}"""

    r = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        raw = r.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        meta = json.loads(raw)
        idx  = meta.get("index", 0)
        if idx >= len(stories):
            idx = 0
        story = stories[idx].copy()
        story.update(meta)
        story["type"] = "news"
        tags  = [t for t in story.get("tags", []) if t in TAG_IDS]
        story["tags"] = [tags[0]] if tags else ["trending"]
        if story.get("category") not in CATEGORY_IDS:
            story["category"] = "industry-trends"
        return story
    except Exception as e:
        log.error(f"Slot {slot} story selection failed: {e}")
        s = stories[0].copy()
        s.update({"type": "news", "category": "industry-trends",
                  "tags": ["trending"], "is_breaking": False,
                  "focus_keyword": "India telecom news"})
        return s


def select_stories(stories: list[dict], trending: list[str]) -> list[dict]:
    """Select 4 best stories with dynamic category assignment — no fixed slot constraints."""
    if not stories:
        return []

    stories_json = json.dumps(
        [{"i": i, "title": s["title"], "summary": s["summary"][:200],
          "cred": s.get("credibility", 50)}
         for i, s in enumerate(stories)],
        indent=2
    )
    prompt = f"""You are the editor of The Mobile Times, India's leading telecom news publication.

Today's trending keywords: {', '.join(trending)}

Pick the 4 BEST, most newsworthy stories. Rules:

- type: always "news" for all 4
- category: assign each story to its BEST fitting category from this full list:
  {ALL_NEWS_CATEGORIES}
- Try to pick stories from DIFFERENT categories (diversity — don't pick 4 5G stories)
- Prioritise India-relevant stories
- Each story used exactly once (no duplicates across the 4 slots)
- tags: exactly ONE per story from: trending, breaking-news, new-launch
    "breaking-news" = urgent, just happened, major immediate impact
    "new-launch"    = product/service/policy launch or major announcement
    "trending"      = default for anything else notable
- is_breaking: true only if genuinely urgent breaking news (max 1 across all 4)
- focus_keyword: 2-4 word SEO keyword from the story
- "cred" is source credibility (0–100). Prefer higher-credibility sources when stories are otherwise equal. Never sacrifice relevance or diversity for credibility.

Stories:
{stories_json}

Respond with a JSON array of exactly 4 objects. Output ONLY the JSON array:
[
  {{"slot":1,"index":<i>,"type":"news","category":"<slug>","tags":["<tag>"],"is_breaking":false,"focus_keyword":"<kw>"}},
  {{"slot":2,"index":<i>,"type":"news","category":"<slug>","tags":["<tag>"],"is_breaking":false,"focus_keyword":"<kw>"}},
  {{"slot":3,"index":<i>,"type":"news","category":"<slug>","tags":["<tag>"],"is_breaking":false,"focus_keyword":"<kw>"}},
  {{"slot":4,"index":<i>,"type":"news","category":"<slug>","tags":["<tag>"],"is_breaking":false,"focus_keyword":"<kw>"}}
]"""

    r = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        raw_text = r.content[0].text.strip()
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if match:
            raw_text = match.group(0)
        selected_meta = json.loads(raw_text)
        result = []
        for meta in selected_meta:
            idx = meta.get("index", 0)
            if idx >= len(stories):
                idx = 0
            story = stories[idx].copy()
            story.update(meta)
            # Enforce type=news, exactly ONE valid tag, valid category
            story["type"] = "news"
            tags = [t for t in story.get("tags", []) if t in TAG_IDS]
            story["tags"] = [tags[0]] if tags else ["trending"]
            if story.get("category") not in CATEGORY_IDS:
                story["category"] = "industry-trends"
            result.append(story)
        return result[:4]
    except Exception as e:
        log.error(f"Story selection parse failed: {e}")
        fallback_cats = ["policy-updates", "ai-machine-learning",
                         "smartphones-tablets", "5g-networks"]
        return [{**stories[i], "type": "news", "category": fallback_cats[i],
                 "tags": ["trending"], "is_breaking": False,
                 "focus_keyword": "India telecom news"}
                for i in range(min(4, len(stories)))]


# ─── Content Generation ───────────────────────────────────────────────────────

def inject_internal_links(html: str) -> str:
    injected = set()
    for keyword, url in INTERNAL_LINKS.items():
        kw = keyword.strip()
        if kw in html and kw not in injected:
            link = f'<a href="{WP_URL}{url}" title="{kw}">{kw}</a>'
            html = html.replace(kw, link, 1)
            injected.add(kw)
    return html

CURRENT_YEAR = str(datetime.now(IST).year)
WRONG_YEARS  = ["2020", "2021", "2022", "2023", "2024", "2025"]

def validate_and_fix(content: str, title: str) -> tuple[str, str, list[str]]:
    """
    Fix common AI mistakes before publishing.
    Returns (fixed_content, list_of_warnings).
    """
    warnings = []
    original = content

    # 1. Fix wrong year — replace old years with current year
    for yr in WRONG_YEARS:
        if yr in content:
            content = content.replace(yr, CURRENT_YEAR)
            warnings.append(f"Fixed year: {yr} → {CURRENT_YEAR}")
        if yr in title:
            title = title.replace(yr, CURRENT_YEAR)
            warnings.append(f"Fixed year in title: {yr} → {CURRENT_YEAR}")

    # 2. Detect unfilled placeholders like [Stat or fact] or [Figure]
    placeholders = re.findall(r"\[(?!a |/a)[^\]]{3,60}\]", content)
    if placeholders:
        warnings.append(f"Unfilled placeholders found: {placeholders[:5]}")

    # 3. Detect lorem ipsum or generic filler
    filler_patterns = ["lorem ipsum", "placeholder text", "insert here", "add content"]
    for fp in filler_patterns:
        if fp.lower() in content.lower():
            warnings.append(f"Filler text detected: '{fp}'")

    # 4. Hard-stop if article is very short (< 400 words) — don't publish stub articles
    word_count = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", content)))
    if word_count < 500:
        raise ValueError(f"Article too short: {word_count} words (min 500). Aborting publish.")

    # 5. Hard-stop if unfilled placeholders remain — means template wasn't filled properly
    if placeholders:
        raise ValueError(f"Unfilled placeholders in content: {placeholders[:5]}. Aborting publish.")

    if warnings:
        log.warning(f"  Content QA: {len(warnings)} issue(s) — {'; '.join(warnings)}")
    else:
        log.info(f"  Content QA: passed ({word_count} words)")

    return content, title, warnings

def inject_authority_links(html: str) -> str:
    sources = random.sample(AUTHORITY_LINKS, min(3, len(AUTHORITY_LINKS)))
    parts = []
    for idx, (name, url) in enumerate(sources):
        parts.append(f'<a href="{url}" target="_blank" rel="noopener">{name} ↗</a>')
    source_html = ' | '.join(parts)
    old = '<p class="tmt-sources"><strong>Sources:</strong>'
    new = f'<p class="tmt-sources"><strong>Sources:</strong> {source_html}'
    return html.replace(old, new, 1) if old in html else html + f'\n<p class="tmt-sources"><strong>Sources:</strong> {source_html}</p>'


NEWS_STRUCTURES = [

    # ── Template A: Breaking News (no TOC, highlights first, punchy) ──
    {
        "style": "urgent breaking news desk — punchy sentences, short paragraphs, active voice, high energy. Get straight to the point.",
        "structure": """<p class="tmt-intro"><strong>[First sentence must use "{kw}" and state the biggest news.]</strong> [1-2 sentences of immediate context. Urgency tone.]</p>

<div class="tmt-highlights">
<h3>What You Need To Know</h3>
<ul>
<li>[Most critical fact with a number]</li>
<li>[Second key fact]</li>
<li>[Third key fact]</li>
<li>[Fourth key fact]</li>
</ul>
</div>

<h2 id="s1">[What Happened: heading contains "{kw}"]</h2>
<p>[80–110 words. The core facts. Who, what, where, when. Use "{kw}" here.]</p>

<h2 id="s2">[Why It Matters for India]</h2>
<p>[80–110 words. India-specific impact. Real companies affected. Use "{kw}" here.]</p>
<p>[80–110 words. Broader consequences for the industry.]</p>

<blockquote class="tmt-quote">"[Sharp, direct expert reaction to this news]" — Industry Expert, Telecom Sector</blockquote>

<h2 id="s3">[What Happens Next]</h2>
<p>[80–100 words. Immediate next steps, timelines, watch-outs. Use "{kw}" once.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Template B: Classic Analysis (TOC + highlights + data) ──
    {
        "style": "authoritative trade publication — precise, data-driven, measured tone. Every claim backed by a number or named company.",
        "structure": """<p class="tmt-intro"><strong>[First sentence must use "{kw}" as a bold claim.]</strong> [2 sentences of context and stakes. Use "{kw}" naturally.]</p>

<div class="tmt-toc">
<h3>In This Article</h3>
<ol>
<li><a href="#s1">[Section 1 title]</a></li>
<li><a href="#s2">[Section 2 title]</a></li>
<li><a href="#s3">Outlook</a></li>
</ol>
</div>

<div class="tmt-highlights">
<h3>Key Highlights</h3>
<ul>
<li>[Stat or fact with number]</li>
<li>[Fact 2]</li>
<li>[Fact 3]</li>
<li>[Fact 4]</li>
</ul>
</div>

<h2 id="s1">[Heading that contains "{kw}"]</h2>
<p>[80–110 words. Facts, India angle, real companies, real data. Use "{kw}" here.]</p>
<p>[80–110 words. Continue this section with a second paragraph.]</p>

<h2 id="s2">[Impact heading that contains "{kw}"]</h2>
<p>[80–110 words. Consequences, industry impact. Use "{kw}" here.]</p>

<blockquote class="tmt-quote">"[Expert insight about {kw}]" — Industry Analyst, Telecom Sector</blockquote>

<h2 id="s3">Outlook & What To Watch</h2>
<p>[80–100 words. Forward-looking. Use "{kw}" once. Specific milestones and dates.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Template C: Investor Brief (numbers first, market impact) ──
    {
        "style": "investor-focused financial brief — lead with market impact, revenue figures, competitive positioning, business implications. Numbers-heavy.",
        "structure": """<p class="tmt-intro"><strong>[First sentence: the market-moving significance of "{kw}".]</strong> [2 sentences on financial/business angle. Use "{kw}" naturally.]</p>

<div class="tmt-data-box">
<h3>By The Numbers</h3>
<ul>
<li><strong>[Market metric]:</strong> [Figure]</li>
<li><strong>[Revenue/share data]:</strong> [Figure]</li>
<li><strong>[Growth stat]:</strong> [Figure]</li>
<li><strong>[Competitive figure]:</strong> [Figure]</li>
</ul>
</div>

<h2 id="s1">[Market Context heading with "{kw}"]</h2>
<p>[80–110 words. Market size, growth rate, competitive landscape. Use "{kw}" here.]</p>

<h2 id="s2">[Business Impact: "{kw}" Changes the Game]</h2>
<p>[80–110 words. Revenue implications, winner/loser analysis, strategic shifts. Use "{kw}" here.]</p>
<p>[80–110 words. India-specific business angle. Named operators and figures.]</p>

<blockquote class="tmt-quote">"[Analyst comment on financial/strategic significance]" — Telecom Analyst</blockquote>

<h2 id="s3">Investment Outlook</h2>
<p>[80–100 words. What investors and operators should watch. Key milestones. Use "{kw}" once.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Template D: Deep Dive (quote leads, expert-heavy) ──
    {
        "style": "analytical deep-dive — explain the why behind the news, connect industry dots, cite context from other developments, authoritative and educational.",
        "structure": """<p class="tmt-intro"><strong>[First sentence contextualises why "{kw}" matters RIGHT NOW.]</strong> [2 sentences: what changed, what it signals. Use "{kw}" naturally.]</p>

<blockquote class="tmt-quote">"[Striking expert quote that frames the entire story about {kw}]" — Senior Industry Voice, Telecom</blockquote>

<h2 id="s1">[The Deeper Story Behind "{kw}"]</h2>
<p>[80–110 words. What most coverage misses. Use "{kw}" here. Connect dots to broader trends.]</p>
<p>[80–110 words. Historical context or parallel from India's telecom history.]</p>

<div class="tmt-highlights">
<h3>The Signal In The Noise</h3>
<ul>
<li>[Non-obvious insight #1]</li>
<li>[Non-obvious insight #2]</li>
<li>[Non-obvious insight #3]</li>
<li>[Implication most analysts are missing]</li>
</ul>
</div>

<h2 id="s2">[What This Means for "{kw}" in India]</h2>
<p>[80–110 words. India-specific deep analysis. Use "{kw}" here. Named companies, real stakes.]</p>

<h2 id="s3">The Road Ahead</h2>
<p>[80–100 words. Specific predictions with timelines. Use "{kw}" once. Bold conclusion.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Template E: Product/Launch Focus (for device/launch news) ──
    {
        "style": "product launch coverage — spec-focused, consumer-facing language, comparison to rivals, value-for-money angle for Indian market.",
        "structure": """<p class="tmt-intro"><strong>["{kw}" has arrived — open with the single most impressive spec or feature.]</strong> [2 sentences on why Indian consumers and the market should care.]</p>

<div class="tmt-highlights">
<h3>Quick Specs & Highlights</h3>
<ul>
<li>[Key spec or feature with number]</li>
<li>[Price or availability for India]</li>
<li>[Standout differentiator vs rivals]</li>
<li>[Launch timeline or offer]</li>
</ul>
</div>

<h2 id="s1">[What Makes "{kw}" Stand Out]</h2>
<p>[80–110 words. Key features, design, specs in detail. India-first angle. Use "{kw}" here.]</p>

<h2 id="s2">["{kw}" vs The Competition]</h2>
<p>[80–110 words. Compare directly to 2-3 rivals. Pricing, specs, value. Use "{kw}" here.]</p>
<p>[80–110 words. Who should buy this — target audience, use case.]</p>

<blockquote class="tmt-quote">"[Industry or analyst quote on the product's India market prospects]" — Market Analyst</blockquote>

<h2 id="s3">Availability & Verdict</h2>
<p>[80–100 words. Price, availability, TMT verdict. Use "{kw}" once. Clear buy/skip recommendation.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Template F: Head-to-Head Comparison (Jio vs Airtel, plan battles, etc.) ──
    {
        "style": "head-to-head comparison — lead with the battle, give a real comparison table with data, deliver a clear consumer verdict. Numbers-first, opinion-backed.",
        "structure": """<p class="tmt-intro"><strong>["{kw}" showdown — open with the key difference or surprising result.]</strong> [2 sentences. Why this comparison matters RIGHT NOW for Indian consumers.]</p>

<div class="tmt-highlights">
<h3>Quick Verdict</h3>
<ul>
<li>[Winner for price-conscious users]</li>
<li>[Winner for heavy data or speed users]</li>
<li>[Winner for coverage or reliability]</li>
<li>[Overall: who wins and why in one line]</li>
</ul>
</div>

<h2 id="s1">["{kw}": How Do They Really Compare in 2026?]</h2>
<p>[80–110 words. Set up the comparison — who the players are, what's at stake, why now. Use "{kw}" here.]</p>

<div class="tmt-table-wrap">
<table>
<thead><tr><th>Feature</th><th>[Option A]</th><th>[Option B]</th></tr></thead>
<tbody>
<tr><td>[Metric 1 — e.g. Price]</td><td>[A figure]</td><td>[B figure]</td></tr>
<tr><td>[Metric 2 — e.g. Data/Speed]</td><td>[A figure]</td><td>[B figure]</td></tr>
<tr><td>[Metric 3 — e.g. Coverage]</td><td>[A figure]</td><td>[B figure]</td></tr>
<tr><td>[Metric 4 — e.g. Extras/OTT]</td><td>[A figure]</td><td>[B figure]</td></tr>
<tr><td>[Metric 5 — e.g. Value score]</td><td>[A figure]</td><td>[B figure]</td></tr>
</tbody>
</table>
</div>

<h2 id="s2">[Which Is Better for India? Breaking Down "{kw}"]</h2>
<p>[80–110 words. Deep consumer analysis. Real use cases. Use "{kw}" here. Name the winner per segment.]</p>
<p>[80–110 words. Business/enterprise angle. Which operators or companies benefit. Real stakes.]</p>

<blockquote class="tmt-quote">"[Expert or analyst quote on which option wins and why]" — Telecom Industry Analyst</blockquote>

<h2 id="s3">TMT Verdict on "{kw}"</h2>
<p class="tmt-verdict">[80–100 words. Clear, actionable verdict. Who should pick which option. Use "{kw}" once. Bold memorable close.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },
]

def generate_news_post(story: dict, date_str: str) -> dict:
    kw = story["focus_keyword"]
    is_exclusive = story["type"] == "exclusive"

    # Pick structure — product stories prefer Template E, breaking prefers A
    tags = story.get("tags", [])
    cat  = story.get("category", "")
    if cat in ("smartphones-tablets", "accessories-wearables", "network-smart-devices") or "new-launch" in tags:
        template = NEWS_STRUCTURES[4]  # Product/Launch
    elif "breaking-news" in tags:
        template = NEWS_STRUCTURES[0]  # Breaking News
    elif is_exclusive:
        template = NEWS_STRUCTURES[3]  # Deep Dive for exclusives
    else:
        template = random.choice(NEWS_STRUCTURES)

    style     = template["style"]
    structure = template["structure"].replace("{kw}", kw)

    kw_slug = kw.lower().replace(" ", "-")

    prompt = f"""You are a senior journalist at The Mobile Times, India's leading telecom trade publication.
Writing style for this article: {style}

SOURCE STORY:
Original headline: {story['title']}
Summary: {story['summary']}
URL: {story['url']}
Focus keyword: "{kw}"

━━ WORD COUNT ━━
Total article body: {NEWS_WORD_TARGET} words. Every paragraph 60–90 words. No padding, no repetition.

━━ MANDATORY TITLE RULES ━━
Generate a NEW SEO-optimized title (never copy the source headline):
• Contains focus keyword "{kw}"
• Contains 1 power word: Breaking, Major, Critical, Surges, Drops, Launches, Warns, Reveals, Expands, Soars, Boosts, Unveils, Hits, Wins
• Contains 1 number (2026, a percentage, or a stat)
• 55–70 characters total
• Sounds like a real headline, NOT AI-generated

━━ VIRAL SEO RULES ━━
1. FEATURED SNIPPET: The first paragraph after each H2 must directly answer the implied question in 40–55 words. Google shows these as answer boxes.
2. QUESTION H2s: At least 1 H2 must be phrased as a question (e.g. "Why Is [topic] Critical for India in 2026?")
3. KEYWORD DENSITY: Use "{kw}" exactly 6 times — intro (1), one H2 (1), body paragraphs (3), FAQ (1). Natural, never forced.
4. LSI KEYWORDS: Naturally use 3–4 semantically related terms (not "{kw}") throughout the body.
5. FAQ BLOCK: End every article with exactly 3 FAQ items targeting "People Also Ask" questions. Each answer: 30–45 words.
6. YEAR: Every date reference must use 2026. Never use 2025 or earlier.

━━ ANTI-REPETITION RULES ━━
• Never open two consecutive paragraphs with "India", "The", or the focus keyword.
• Vary sentence length: mix short punchy sentences (8–12 words) with complex ones (20–28 words).
• Do not repeat the same fact twice in different paragraphs.

━━ HUMANIZATION RULES (CRITICAL — AI DETECTION PREVENTION) ━━
• Write like a real journalist, not an AI. Specific details, company names, and numbers over vague generalities.
• BANNED PHRASES (AI tells — never use any of these): "In today's fast-paced world", "In conclusion", "Furthermore", "It is worth noting", "delve into", "landscape", "game-changer", "game changer", "revolutionize", "paradigm shift", "unlock potential", "leverage", "cutting-edge", "state-of-the-art", "seamlessly", "robust solution", "In this article we will explore", "Additionally", "Moreover", "It is important to note", "It is crucial to", "plays a crucial role", "plays a key role", "When it comes to", "In terms of", "This ensures that", "This allows", "not only...but also", "In summary", "To summarize", "At the end of the day", "rest assured", "dive into", "navigate", "foster", "pave the way", "shed light on", "underscore", "holistic", "synergy", "ecosystem".
• BANNED PUNCTUATION — never use em dashes (—) anywhere in the article body or title. Use a comma or a new sentence instead.
• BANNED SENTENCE STARTERS — never begin 3 consecutive sentences with the same word. Never start a sentence with "This" followed by a verb ("This means", "This shows", "This highlights").
• No opinions, editorialising, or brand cheerleading. Just report the facts.
• No passive voice openers. Start sentences with the subject doing the action.
• One idea per paragraph. No transition-word bridges between paragraphs.
• Vary sentence length deliberately: mix 8–12 word punchy sentences with 22–28 word detailed ones. Never 3 sentences of the same length in a row.
• Name specific people, products, companies, prices, and dates rather than saying "industry players" or "market observers".

━━ PARAGRAPH LENGTH ━━
Every <p>: 60–90 words. Split anything longer into two paragraphs.

━━ META DESCRIPTION ━━
Must contain "{kw}" verbatim. 130–155 characters. End with a question or CTA that makes people click.

━━ OUTPUT FORMAT ━━
Use EXACTLY this HTML structure. Fill ALL bracketed placeholders with real content — zero placeholder text in output:

{structure}

<div class="tmt-highlights">
<h3>People Also Ask</h3>
<ul>
<li><strong>[Question 1 about {kw} that people search on Google]?</strong> [Direct answer in 30–45 words.]</li>
<li><strong>[Question 2 about {kw} — different angle]?</strong> [Direct answer in 30–45 words.]</li>
<li><strong>[Question 3 — future or how-to angle]?</strong> [Direct answer in 30–45 words.]</li>
</ul>
</div>

━━ AFTER THE HTML output exactly this (no extra text): ━━
META_JSON:{{"article_title":"[title]","slug":"{kw_slug}-{CURRENT_YEAR}","meta_title":"[50–60 chars | The Mobile Times]","meta_description":"[130–155 chars with '{kw}' + CTA — NO em dashes]","og_title":"[60–70 chars]","og_description":"[180–200 chars]","faq":[{{"q":"[Q1]","a":"[A1 30–45 words]"}},{{"q":"[Q2]","a":"[A2]"}},{{"q":"[Q3]","a":"[A3]"}}]}}"""

    r = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = r.content[0].text.strip()

    if "META_JSON:" in raw:
        parts = raw.split("META_JSON:", 1)
        html_content = parts[0].strip()
        try:
            meta_str = parts[1].strip()
            meta_str = re.sub(r"^```(?:json)?\s*", "", meta_str)
            meta_str = re.sub(r"\s*```$", "", meta_str)
            meta = json.loads(meta_str)
        except Exception:
            meta = {}
    else:
        html_content = raw
        meta = {}

    # Strip any markdown code fences Claude may have wrapped the HTML in
    html_content = re.sub(r"^```html?\s*\n?", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"\n?```\s*$", "", html_content)

    html_content = inject_internal_links(html_content)
    html_content = inject_authority_links(html_content)
    html_content = inject_related_links(html_content)
    html_content = inject_auto_toc(html_content)

    title    = meta.get("article_title", story["title"])
    slug     = meta.get("slug", re.sub(r"[^a-z0-9-]", "", kw.lower().replace(" ", "-")))
    meta_t   = meta.get("meta_title",   f"{title[:50]} | The Mobile Times")
    meta_d   = meta.get("meta_description", f"Latest {kw} news from India. {story['summary'][:100]}")
    og_title = meta.get("og_title",     meta_t)
    og_desc  = meta.get("og_description", meta_d)

    # QA: fix years, detect placeholders
    html_content, title, _ = validate_and_fix(html_content, title)
    slug = slug.replace("2025", CURRENT_YEAR).replace("2024", CURRENT_YEAR)

    # Guarantee kw appears in meta_description
    if kw.lower() not in meta_d.lower():
        meta_d = f"{kw}: {meta_d}"[:155]

    return {
        "title":            title,
        "content":          html_content,
        "slug":             slug,
        "focus_keyword":    kw,
        "meta_title":       meta_t,
        "meta_description": meta_d,
        "og_title":         og_title,
        "og_description":   og_desc,
        "category_slug":    story["category"],
        "tags":             story.get("tags", []),
        "is_breaking":      story.get("is_breaking", False),
        "is_launch":        story.get("is_launch",   False),
        "source_url":       story["url"],
    }

BLOG_STRUCTURES = [

    # ── Blog A: Classic Analysis (TOC + data box + verdict) ──
    {
        "style": "authoritative trade publication — precise, data-driven, measured. Every claim backed by a number or named company.",
        "structure": """<p class="tmt-intro"><strong>[Bold claim using the focus keyword].</strong> [2–3 sentences. Stakes. Why now. Use keyword again.]</p>

<div class="tmt-toc">
<h3>In This Article</h3>
<ol>
<li><a href="#s1">[Section 1 title with keyword]</a></li>
<li><a href="#s2">[Section 2 title]</a></li>
<li><a href="#s3">[Section 3 title]</a></li>
<li><a href="#s4">[Section 4 title]</a></li>
<li><a href="#s5">The Mobile Times Verdict</a></li>
</ol>
</div>

<h2 id="s1">[Context heading with focus keyword]</h2>
<p>[80–110 words. Background and stakes. Use focus keyword.]</p>
<p>[80–110 words. Continue context. Real data and companies.]</p>

<h2 id="s2">[Core Problem or Opportunity with focus keyword]</h2>
<p>[80–110 words. Define the problem or opportunity clearly. Use focus keyword.]</p>
<p>[80–110 words. Supporting data. India-specific angle.]</p>

<blockquote class="tmt-quote">"[Strong editorial quote about the topic]" — The Mobile Times Editorial</blockquote>

<h2 id="s3">[What The Industry Gets Wrong]</h2>
<p>[80–110 words. Contrarian or insightful angle. Use focus keyword.]</p>

<div class="tmt-data-box">
<h3>By The Numbers</h3>
<ul>
<li><strong>[Metric]:</strong> [Figure]</li>
<li><strong>[Metric]:</strong> [Figure]</li>
<li><strong>[Metric]:</strong> [Figure]</li>
<li><strong>[Metric]:</strong> [Figure]</li>
</ul>
</div>

<h2 id="s4">[What Must Happen Next with focus keyword]</h2>
<p>[80–110 words. Action items. Industry imperatives. Use focus keyword.]</p>

<h2 id="s5">The Mobile Times Verdict</h2>
<p class="tmt-verdict">[80–110 words. TMT's definitive position. Bold conclusion. Use focus keyword.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Blog B: Opinion / War of Words (debate format) ──
    {
        "style": "sharp editorial opinion — take a strong position, argue it with evidence, acknowledge the counterargument then dismantle it. Opinionated and confident.",
        "structure": """<blockquote class="tmt-quote">"[The sharpest possible take on this topic — a TMT editorial position]" — The Mobile Times</blockquote>

<p class="tmt-intro"><strong>[State the controversial or bold claim about focus keyword.]</strong> [2 sentences. Why this view is correct. Use focus keyword.]</p>

<div class="tmt-highlights">
<h3>The TMT Position</h3>
<ul>
<li>[Bold claim #1 with evidence]</li>
<li>[Bold claim #2 with evidence]</li>
<li>[Bold claim #3 with evidence]</li>
<li>[The one thing most people get wrong]</li>
</ul>
</div>

<h2 id="s1">[Why focus keyword Is More Important Than Anyone Admits]</h2>
<p>[80–110 words. Build the case. Real data. India context. Use focus keyword.]</p>
<p>[80–110 words. Second layer of argument. Named companies, real stakes.]</p>

<h2 id="s2">[The Counterargument — And Why It Falls Short]</h2>
<p>[80–110 words. Steel-man the opposing view. Use focus keyword. Then dismantle it.]</p>

<h2 id="s3">[What Needs to Change in India]</h2>
<p>[80–110 words. Specific, actionable critique. Use focus keyword. Name names if needed.]</p>
<p>[80–110 words. What success looks like. Milestones.]</p>

<h2 id="s4">The Mobile Times Verdict</h2>
<p class="tmt-verdict">[80–110 words. Definitive position. Bold, memorable close. Use focus keyword.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Blog C: How India Compares (India vs World format) ──
    {
        "style": "comparative analysis — benchmark India against global peers, identify gaps and opportunities, recommend specific policy or industry actions.",
        "structure": """<p class="tmt-intro"><strong>[How does India rank on focus keyword vs the world? Open with the gap or lead.]</strong> [2 sentences. Why this comparison matters now. Use focus keyword.]</p>

<div class="tmt-data-box">
<h3>India vs The World: focus keyword</h3>
<ul>
<li><strong>India:</strong> [Current figure or ranking]</li>
<li><strong>China/USA/UK:</strong> [Comparison figure]</li>
<li><strong>Gap to close:</strong> [Specific metric]</li>
<li><strong>Timeline:</strong> [When India could catch up]</li>
</ul>
</div>

<h2 id="s1">[Where India Stands on focus keyword Today]</h2>
<p>[80–110 words. Current state with data. Use focus keyword.]</p>
<p>[80–110 words. Why this is the starting point — historical context.]</p>

<h2 id="s2">[What Global Leaders Are Doing Differently]</h2>
<p>[80–110 words. 2-3 country examples. Specific policies or investments. Use focus keyword.]</p>

<blockquote class="tmt-quote">"[Expert quote on India's comparative position]" — International Telecom Analyst</blockquote>

<h2 id="s3">[India's Path Forward on focus keyword]</h2>
<p>[80–110 words. Specific recommendations. Policy, investment, timeline. Use focus keyword.]</p>
<p>[80–110 words. What's already working that India can build on.]</p>

<h2 id="s4">The Mobile Times Verdict</h2>
<p class="tmt-verdict">[80–110 words. Can India close the gap? TMT's position. Use focus keyword.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },

    # ── Blog D: Explainer / How-To ──
    {
        "style": "clear educational explainer — break down a complex topic for a smart but non-technical reader. Use analogies, numbered steps where helpful, plain English.",
        "structure": """<p class="tmt-intro"><strong>[What is focus keyword, and why should every Indian telecom professional understand it?]</strong> [2 sentences. Stakes for India. Use focus keyword again.]</p>

<div class="tmt-toc">
<h3>In This Guide</h3>
<ol>
<li><a href="#s1">What Is focus keyword?</a></li>
<li><a href="#s2">How It Works In Practice</a></li>
<li><a href="#s3">Why India Is At A Turning Point</a></li>
<li><a href="#s4">What You Should Watch For</a></li>
</ol>
</div>

<h2 id="s1">[What Is focus keyword — The Plain English Version]</h2>
<p>[80–110 words. Explain from first principles. Use an analogy. Use focus keyword.]</p>
<p>[80–110 words. Why the definition matters. Common misconceptions.]</p>

<h2 id="s2">[How focus keyword Works In The Real World]</h2>
<p>[80–110 words. Concrete example from Indian telecom. Named company. Use focus keyword.]</p>

<div class="tmt-highlights">
<h3>Key Facts</h3>
<ul>
<li>[Fact 1 — surprising or counterintuitive]</li>
<li>[Fact 2 — India-specific]</li>
<li>[Fact 3 — global context]</li>
<li>[Fact 4 — future implication]</li>
</ul>
</div>

<h2 id="s3">[Why India Is At A Turning Point With focus keyword]</h2>
<p>[80–110 words. The inflection point. What changed recently. Use focus keyword.]</p>
<p>[80–110 words. Who wins, who loses if India gets this right or wrong.]</p>

<blockquote class="tmt-quote">"[Expert quote making the stakes clear]" — Telecom Policy Expert</blockquote>

<h2 id="s4">What To Watch in 2026</h2>
<p>[80–100 words. 3-4 specific milestones or signals. Use focus keyword once.]</p>

<p class="tmt-sources"><strong>Sources:</strong></p>"""
    },
]

def generate_blog_post(topic: str, subcategory: str, date_str: str) -> dict:
    template  = random.choice(BLOG_STRUCTURES)
    style     = template["style"]
    structure = template["structure"]

    prompt = f"""You are the chief analyst at The Mobile Times, India's premier telecom publication.
Writing style: {style}

Write a long-form Insights blog post (880–960 words) on the topic below.

TOPIC: {topic}
TARGET AUDIENCE: Indian telecom professionals, investors, and industry watchers

━━ WORD COUNT ━━
Total article: {BLOG_WORD_TARGET} words. Every paragraph 60–90 words. No padding, no repetition.

━━ MANDATORY TITLE RULES ━━
• Derive the best 2–4 word focus keyword from the topic
• Title must contain that focus keyword
• Title must contain 1 power word: Breaking, Major, Critical, Surges, Reveals, Warns, Expands, Boosts, Dominates, Fails, Rises, Unveils
• Title must contain 1 number (2026, percentage, or stat)
• 55–70 characters total — sounds like a real headline, NOT AI-generated

━━ VIRAL SEO RULES ━━
1. FEATURED SNIPPETS: First paragraph after each H2 answers the implied question in 40–55 words directly.
2. QUESTION H2s: At least 2 of your H2s must be phrased as a question (e.g. "Why Is [topic] Failing India's Operators?")
3. KEYWORD: Use focus keyword EXACTLY 8 times. Replace every "focus keyword" placeholder with your chosen keyword.
4. LSI: Use 4–5 semantically related terms naturally throughout.
5. FAQ BLOCK: End with 3 FAQ items targeting Google's "People Also Ask". Each answer: 30–45 words.
6. YEAR: All date references must use 2026. Never 2025 or earlier.

━━ ANTI-REPETITION ━━
• No two consecutive paragraphs open with the same word.
• Mix short (8–12 word) and complex (20–28 word) sentences throughout.
• Never repeat the same fact, stat, or claim in multiple sections.

━━ HUMANIZATION RULES (CRITICAL) ━━
• Write like a sharp trade journalist, not an AI assistant.
• BANNED PHRASES — never write: "In today's fast-paced world", "In conclusion", "Furthermore", "It is worth noting", "delve into", "landscape", "game-changer", "revolutionize", "paradigm shift", "leverage", "cutting-edge", "seamlessly", "robust solution", "In this article we will explore".
• BANNED PUNCTUATION — never use em dashes (—) anywhere in the article or title.
• No opinions or brand cheerleading. Analytical voice only: cite data, name companies, quote analysts.
• No passive voice openers. Active voice throughout.

━━ PARAGRAPH LENGTH ━━
Every <p>: 60–90 words. Split anything longer.

━━ META DESCRIPTION ━━
Must contain focus keyword verbatim. 130–155 characters. End with a question or CTA.

━━ OUTPUT FORMAT ━━
Use EXACTLY this HTML structure. Fill ALL bracketed placeholders with real content — zero placeholder text in output:

{structure}

<div class="tmt-highlights">
<h3>People Also Ask</h3>
<ul>
<li><strong>[Question 1 people search about this topic]?</strong> [Direct answer 30–45 words.]</li>
<li><strong>[Question 2 — different angle]?</strong> [Direct answer 30–45 words.]</li>
<li><strong>[Question 3 — future/how-to angle]?</strong> [Direct answer 30–45 words.]</li>
</ul>
</div>

━━ AFTER THE HTML output exactly this: ━━
META_JSON:{{"article_title":"[title]","slug":"short-keyword-slug-max-50-chars","focus_keyword":"2–4 word keyword","meta_title":"[50–60 chars | The Mobile Times]","meta_description":"[130–155 chars with focus keyword + CTA — NO em dashes]","og_title":"[60–70 chars]","og_description":"[180–200 chars]","faq":[{{"q":"[Q1]","a":"[A1]"}},{{"q":"[Q2]","a":"[A2]"}},{{"q":"[Q3]","a":"[A3]"}}]}}"""

    r = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = r.content[0].text.strip()

    if "META_JSON:" in raw:
        parts = raw.split("META_JSON:", 1)
        html_content = parts[0].strip()
        try:
            meta_str = parts[1].strip()
            meta_str = re.sub(r"^```(?:json)?\s*", "", meta_str)
            meta_str = re.sub(r"\s*```$", "", meta_str)
            meta = json.loads(meta_str)
        except Exception:
            meta = {}
    else:
        html_content = raw
        meta = {}

    html_content = re.sub(r"^```html?\s*\n?", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"\n?```\s*$", "", html_content)

    kw       = meta.get("focus_keyword", "India telecom insights")
    title    = meta.get("article_title", topic)
    html_content = inject_internal_links(html_content)
    html_content = inject_authority_links(html_content)
    html_content = inject_related_links(html_content)
    html_content = inject_auto_toc(html_content)

    # QA: fix years, detect placeholders
    html_content, title, _ = validate_and_fix(html_content, title)

    slug     = meta.get("slug", re.sub(r"[^a-z0-9-]", "", topic.lower().replace(" ", "-"))[:60])
    slug     = slug.replace("2025", CURRENT_YEAR).replace("2024", CURRENT_YEAR)
    meta_t   = meta.get("meta_title", f"{title[:50]} | The Mobile Times")
    meta_d   = meta.get("meta_description", f"In-depth {kw} analysis: {topic[:100]}")
    og_title = meta.get("og_title", meta_t)
    og_desc  = meta.get("og_description", meta_d)

    if kw.lower() not in meta_d.lower():
        meta_d = f"{kw}: {meta_d}"[:155]

    return {
        "title":            title,
        "content":          html_content,
        "slug":             slug,
        "focus_keyword":    kw,
        "meta_title":       meta_t,
        "meta_description": meta_d,
        "og_title":         og_title,
        "og_description":   og_desc,
        "category_slug":    subcategory,
        "tags":             ["trending"],
        "is_breaking":      False,
        "is_launch":        False,
        "source_url":       "",
    }


# ─── WordPress Publishing ─────────────────────────────────────────────────────

def get_slot_publish_time(slot_idx: int, force_publish: bool = False) -> tuple[str, str | None, str | None]:
    """
    Returns (wp_status, date_local_str, date_gmt_str) for a post slot.
    slot_idx 0-4 maps to POST_TIMES_IST.  If the scheduled time is past, publishes immediately.
    """
    now_ist = datetime.now(IST)
    h, m    = map(int, POST_TIMES_IST[min(slot_idx, len(POST_TIMES_IST) - 1)].split(":"))
    sched   = now_ist.replace(hour=h, minute=m, second=0, microsecond=0)
    if force_publish or sched <= now_ist:
        return "publish", None, None
    date_local = sched.strftime("%Y-%m-%dT%H:%M:%S")
    date_gmt   = sched.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return "future", date_local, date_gmt


def get_tag_ids(tag_slugs: list[str]) -> list[int]:
    return [TAG_IDS[s] for s in tag_slugs if s in TAG_IDS]

def save_rank_math_meta(post_id: int, post_data: dict):
    """Save Rank Math SEO meta via tmt-admin-api plugin."""
    r = requests.post(
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
    if r.ok:
        log.info(f"  Rank Math meta saved for post {post_id}")
    else:
        log.warning(f"  Rank Math meta save failed ({r.status_code})")

def publish_post(post_data: dict, featured_media_id: int | None,
                 sticky: bool = False, draft: bool = False, slot_idx: int = 0) -> dict | None:
    cat_id  = CATEGORY_IDS.get(post_data["category_slug"], CATEGORY_IDS["tech-innovation"])
    tag_ids = get_tag_ids(post_data["tags"])

    if draft:
        status, date_local, date_gmt = "draft", None, None
    elif sticky:
        # Breaking/sticky posts always publish immediately
        status, date_local, date_gmt = "publish", None, None
    else:
        status, date_local, date_gmt = get_slot_publish_time(slot_idx)

    payload = {
        "title":          post_data["title"],
        "content":        post_data["content"],
        "status":         status,
        "slug":           post_data["slug"],
        "categories":     [cat_id],
        "tags":           tag_ids,
        "featured_media": featured_media_id or 0,
        "sticky":         sticky,
    }
    if date_local and status == "future":
        payload["date"]     = date_local
        payload["date_gmt"] = date_gmt

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=WP_HDR, json=payload, timeout=30)
    if r.ok:
        post = r.json()
        save_rank_math_meta(post["id"], post_data)
        return post
    log.error(f"Publish failed ({r.status_code}): {r.text[:200]}")
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


def _increment_auto_count():
    """Increment the shared daily automated post counter in WP state."""
    today = datetime.now(IST).strftime("%Y-%m-%d")
    key   = f"auto_posts_{today}"
    try:
        r = requests.post(f"{WP_URL}/wp-json/tmt/v1/state/get",
                         json={"secret": TMT_SECRET, "name": key}, timeout=10)
        n = int(r.json().get("value") or 0) if r.ok else 0
        requests.post(f"{WP_URL}/wp-json/tmt/v1/state/set",
                     json={"secret": TMT_SECRET, "name": key, "value": n + 1}, timeout=10)
        log.info(f"  Daily auto count: {n + 1}/5")
    except Exception:
        pass


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


# ─── Daily Run ────────────────────────────────────────────────────────────────

def run_daily(exclusive_tip: str = "", test_mode: bool = False, slot: int | None = None):
    global _recent_posts_cache, _seen_urls
    _seen_urls = load_seen_urls()
    now_ist   = datetime.now(IST)
    date_str  = now_ist.isoformat()
    today_idx = now_ist.weekday()  # 0=Monday

    log.info("=" * 60)
    if slot:
        log.info(f"TMT Slot {slot} Run — {now_ist.strftime('%A %d %B %Y %H:%M IST')}")
    else:
        log.info(f"TMT Daily Run (all slots) — {now_ist.strftime('%A %d %B %Y %H:%M IST')}")
    log.info("=" * 60)

    _recent_posts_cache = get_recent_posts()

    # ── Single-slot mode (GitHub Actions: one post per trigger) ──────────────
    if slot is not None:
        today_str = now_ist.strftime("%Y-%m-%d")

        if slot == 5:
            # Blog / Insights post
            blog_topic, blog_subcat = WEEKLY_BLOG_TOPICS.get(today_idx, WEEKLY_BLOG_TOPICS[0])
            log.info(f"Slot 5 — blog topic: {blog_topic}")
            blog_data = generate_blog_post(blog_topic, blog_subcat, date_str)
            blog_img = (
                fetch_fal_image(blog_topic) or
                fetch_unsplash_image(blog_data["focus_keyword"]) or
                fetch_pexels_image(blog_topic.split(":")[0]) or
                make_fallback_image(blog_topic)
            )
            blog_kw_filename = re.sub(r"[^a-z0-9-]", "", blog_data["focus_keyword"].lower().replace(" ", "-"))
            blog_media_id, blog_img_url = upload_image_to_wp(
                blog_img, f"{blog_kw_filename}-{today_str}.jpg",
                alt=f"{blog_data['title']} | The Mobile Times",
                img_title=blog_data["focus_keyword"],
            )
            # Body image for blog
            _slot5_map = {
                "industry-insights": "India business technology", "case-studies": "India business office",
                "policy-updates": "India government parliament", "market-trends": "India market economy",
                "how-to-guides": "technology guide setup",
            }
            blog_body_bytes = fetch_pexels_image(
                _slot5_map.get(blog_subcat, "India telecom technology"), watermark=True
            )
            if blog_body_bytes:
                _, blog_body_url = upload_image_to_wp(
                    blog_body_bytes, f"{blog_kw_filename}-body-{today_str}.jpg",
                    alt=f"{blog_data['focus_keyword']} | The Mobile Times",
                    img_title=blog_data["focus_keyword"],
                )
                if blog_body_url:
                    blog_data["content"] = inject_body_image_html(
                        blog_data["content"], blog_body_url,
                        f"{blog_data['focus_keyword']} | The Mobile Times"
                    )
            result = publish_post(blog_data, blog_media_id, sticky=False,
                                  draft=test_mode, slot_idx=4)
            if result:
                post_url = result.get("url", result.get("link", ""))
                log.info(f"  Slot 5 published: {post_url}")
                ping_indexing(post_url)
                seed_post_views(result.get("id"))
                _increment_auto_count()
                save_seen_urls(set())
                try:
                    from social_poster import post_to_all
                    post_to_all(blog_data["title"], post_url, blog_data["tags"],
                                category=blog_data["category_slug"])
                except Exception as e:
                    log.warning(f"Social posting failed: {e}")
            else:
                log.error("Slot 5 blog publish failed")
            return

        # Slots 1–4: news post
        log.info(f"Slot {slot} — fetching RSS stories...")
        stories = fetch_all_stories()
        if not stories:
            log.error(f"Slot {slot} — no stories fetched, aborting")
            return
        trending = get_trending_from_stories(stories)
        published_titles = get_published_titles()
        stories = [s for s in stories if not is_duplicate(s["title"], published_titles)]
        log.info(f"Slot {slot} — {len(stories)} stories after word-overlap dedup")
        stories = batch_semantic_dedup(stories, published_titles)
        log.info(f"Slot {slot} — {len(stories)} stories after semantic dedup")

        if exclusive_tip and slot == 1:
            stories.insert(0, {
                "title": exclusive_tip, "summary": exclusive_tip,
                "url": WP_URL, "source": "TMT Editorial",
            })

        story = select_story_for_slot(stories, slot, trending)
        if not story:
            log.error(f"Slot {slot} — story selection failed, aborting")
            return

        post_type = "exclusive" if story.get("type") == "exclusive" else "news"
        log.info(f"Slot {slot} — generating {post_type} post: {story['title'][:60]}...")
        post_data = generate_news_post(story, date_str)

        img_bytes = (
            extract_source_image(story.get("url", ""), story.get("_og_image", "")) or
            fetch_unsplash_image(post_data["focus_keyword"]) or
            fetch_pexels_image(post_data["focus_keyword"]) or
            make_fallback_image(story["title"])
        )
        kw_filename = re.sub(r"[^a-z0-9-]", "", post_data["focus_keyword"].lower().replace(" ", "-"))
        img_alt   = f"{post_data['title']} | The Mobile Times"
        img_title = post_data["focus_keyword"]
        media_id, feat_img_url = upload_image_to_wp(
            img_bytes, f"{kw_filename}-{today_str}.jpg",
            img_alt, img_title=img_title
        )

        body_search = _CAT_TO_SEARCH.get(post_data.get("category_slug", ""), "India telecom technology")
        body_img_bytes = (
            fetch_unsplash_image(body_search, watermark=True) or
            fetch_pexels_image(body_search, watermark=True)
        )
        if body_img_bytes:
            body_media_id, body_img_url = upload_image_to_wp(
                body_img_bytes, f"{kw_filename}-body-{today_str}.jpg",
                alt=f"{post_data['focus_keyword']} | The Mobile Times",
                img_title=post_data["focus_keyword"],
            )
            if body_img_url:
                post_data["content"] = inject_body_image_html(
                    post_data["content"], body_img_url,
                    f"{post_data['focus_keyword']} | The Mobile Times"
                )

        result = publish_post(post_data, media_id, sticky=False,
                              draft=test_mode, slot_idx=slot - 1)
        if result:
            post_url = result.get("url", result.get("link", ""))
            log.info(f"  Slot {slot} published: {post_url}")
            ping_indexing(post_url)
            seed_post_views(result.get("id"))
            _increment_auto_count()
            url_to_save = story.get("url")
            if url_to_save and url_to_save != WP_URL:
                save_seen_urls({url_to_save})
            try:
                from social_poster import post_to_all
                post_to_all(post_data["title"], post_url, post_data["tags"],
                            category=post_data["category_slug"])
            except Exception as e:
                log.warning(f"Social posting failed: {e}")
        else:
            log.error(f"Slot {slot} publish failed")
        return

    # ── Batch mode (--run-now: all 5 posts at once) ───────────────────────────
    log.info(f"  {len(_recent_posts_cache)} recent posts loaded for related-link injection")

    # Step 2: RSS stories + duplicate filter
    log.info("Fetching RSS stories...")
    stories = fetch_all_stories()
    if not stories:
        log.error("No stories fetched — aborting run")
        return
    trending = get_trending_from_stories(stories)
    log.info(f"Trending: {trending}")
    published_titles = get_published_titles()
    stories = [s for s in stories if not is_duplicate(s["title"], published_titles)]
    log.info(f"{len(stories)} stories after word-overlap dedup")
    stories = batch_semantic_dedup(stories, published_titles)
    log.info(f"{len(stories)} stories after semantic dedup")

    # If manual exclusive tip provided, add it as first story
    if exclusive_tip:
        stories.insert(0, {
            "title":   exclusive_tip,
            "summary": exclusive_tip,
            "url":     WP_URL,
            "source":  "TMT Editorial",
        })

    # Step 4: Select 4 stories with AI routing (one per slot)
    log.info("Selecting and routing stories...")
    selected = select_stories(stories, trending)
    if not selected:
        log.error("Story selection failed — aborting")
        return

    # Step 5: Blog topic for today
    blog_topic, blog_subcat = WEEKLY_BLOG_TOPICS.get(today_idx, WEEKLY_BLOG_TOPICS[0])
    log.info(f"Blog topic: {blog_topic}")

    published = []
    today_str = now_ist.strftime("%Y-%m-%d")

    # Step 6: Generate and publish 4 news posts
    for i, story in enumerate(selected):
        post_type = "exclusive" if story.get("type") == "exclusive" else "news"
        log.info(f"Generating post {i+1}/4: {story['title'][:60]}...")

        post_data = generate_news_post(story, date_str)

        img_bytes = (
            extract_source_image(story.get("url", "")) or
            fetch_unsplash_image(post_data["focus_keyword"]) or
            fetch_pexels_image(post_data["focus_keyword"]) or
            make_fallback_image(story["title"])
        )

        kw_filename = re.sub(r"[^a-z0-9-]", "", post_data["focus_keyword"].lower().replace(" ", "-"))
        filename  = f"{kw_filename}-{today_str}-{i+1}.jpg"
        alt_text  = f"{post_data['title']} | The Mobile Times"
        img_title = post_data["focus_keyword"]
        media_id, feat_img_url  = upload_image_to_wp(img_bytes, filename, alt_text, img_title=img_title)

        body_search2 = _CAT_TO_SEARCH.get(post_data.get("category_slug", ""), "India telecom technology")
        body_img_bytes = (
            fetch_unsplash_image(body_search2, watermark=True) or
            fetch_pexels_image(body_search2, watermark=True)
        )
        if body_img_bytes:
            _, body_url = upload_image_to_wp(
                body_img_bytes, f"{kw_filename}-body-{today_str}-{i+1}.jpg",
                alt=f"{post_data['focus_keyword']} | The Mobile Times",
                img_title=post_data["focus_keyword"],
            )
            if body_url:
                post_data["content"] = inject_body_image_html(
                    post_data["content"], body_url,
                    f"{post_data['focus_keyword']} | The Mobile Times"
                )

        result = publish_post(post_data, media_id, sticky=False, slot_idx=i)
        if result:
            post_url  = result.get("url", result.get("link", ""))
            scheduled = result.get("status") == "future"
            log.info(f"  {'Scheduled' if scheduled else 'Published'} [{POST_TIMES_IST[i]} IST]: {post_url}")
            ping_indexing(post_url)
            seed_post_views(result.get("id"))
            _increment_auto_count()
            published.append({
                "type":     post_type,
                "title":    post_data["title"],
                "url":      post_url,
                "category": post_data["category_slug"],
                "tags":     post_data["tags"],
            })
            try:
                from social_poster import post_to_all
                post_to_all(post_data["title"], post_url, post_data["tags"], category=post_data["category_slug"])
            except Exception as e:
                log.warning(f"Social posting failed: {e}")
        else:
            log.error(f"  Failed to publish post {i+1}")

        time.sleep(3)

    # Step 7: Generate and publish blog post (Post 5 — Insights)
    log.info(f"Generating blog post: {blog_topic[:60]}...")
    blog_data = generate_blog_post(blog_topic, blog_subcat, date_str)

    blog_img = (
        fetch_fal_image(blog_topic) or
        fetch_unsplash_image(blog_data["focus_keyword"]) or
        fetch_pexels_image(blog_topic.split(":")[0]) or
        make_fallback_image(blog_topic)
    )
    blog_kw_fn = re.sub(r"[^a-z0-9-]", "", blog_data["focus_keyword"].lower().replace(" ", "-"))
    blog_filename = f"{blog_kw_fn}-{today_str}.jpg"
    blog_alt  = f"{blog_data['title']} | The Mobile Times"
    blog_media_id, blog_img_url = upload_image_to_wp(blog_img, blog_filename, blog_alt,
                                                     img_title=blog_data["focus_keyword"])
    # Body image for batch blog
    blog_body_kw    = blog_data.get("category_slug", "industry-insights")
    _blog_body_map  = {
        "industry-insights": "India business technology", "case-studies": "India business office",
        "policy-updates": "India government parliament", "market-trends": "India market economy",
        "how-to-guides": "technology guide setup",
    }
    _blog_body_q    = _blog_body_map.get(blog_body_kw, "India telecom technology")
    blog_body_bytes = (
        fetch_unsplash_image(_blog_body_q, watermark=True) or
        fetch_pexels_image(_blog_body_q, watermark=True)
    )
    if blog_body_bytes:
        _, blog_body_url = upload_image_to_wp(
            blog_body_bytes, f"{blog_kw_fn}-body-{today_str}.jpg",
            alt=f"{blog_body_kw} | The Mobile Times", img_title=blog_body_kw,
        )
        if blog_body_url:
            blog_data["content"] = inject_body_image_html(
                blog_data["content"], blog_body_url,
                f"{blog_body_kw} | The Mobile Times"
            )

    blog_result = publish_post(blog_data, blog_media_id, sticky=False, slot_idx=4)
    if blog_result:
        blog_url  = blog_result.get("url", "")
        scheduled = blog_result.get("status") == "future"
        log.info(f"  Blog {'scheduled' if scheduled else 'published'} [{POST_TIMES_IST[4]} IST]: {blog_url}")
        ping_indexing(blog_url)
        seed_post_views(blog_result.get("id"))
        _increment_auto_count()
        published.append({
            "type":     "blog",
            "title":    blog_data["title"],
            "url":      blog_url,
            "category": blog_subcat,
            "tags":     blog_data["tags"],
        })
        try:
            from social_poster import post_to_all
            post_to_all(blog_data["title"], blog_url, blog_data["tags"], category=blog_data["category_slug"])
        except Exception as e:
            log.warning(f"Social posting failed for blog: {e}")
    else:
        log.error("Failed to publish blog post")

    # Save all processed story URLs to persistent dedup store
    new_story_urls = {s.get("url") for s in selected if s.get("url")} - {"", WP_URL}
    if new_story_urls:
        save_seen_urls(new_story_urls)
        log.info(f"Saved {len(new_story_urls)} story URLs to dedup store")

    # Final summary
    log.info("\n" + "=" * 60)
    log.info(f"Run complete — {len(published)}/5 posts published")
    for p in published:
        log.info(f"  [{p['type'].upper()}] {p['title'][:55]} -> {p['url']}")
    log.info("=" * 60)

    return published


# ─── Scheduler ────────────────────────────────────────────────────────────────

def run_scheduler():
    log.info("Scheduler started — will run daily at 08:00 IST")

    def job():
        now = datetime.now(IST)
        log.info(f"Scheduled trigger at {now.strftime('%H:%M IST')}")
        run_daily()

    schedule.every().day.at("02:30").do(job)  # 08:00 IST = 02:30 UTC

    while True:
        schedule.run_pending()
        time.sleep(60)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Mobile Times Automation Agent")
    parser.add_argument("--run-now",   action="store_true", help="Run all 5 slots at once immediately")
    parser.add_argument("--slot",      type=int, choices=[1,2,3,4,5], help="Run a single slot (1–4 = news, 5 = blog)")
    parser.add_argument("--schedule",  action="store_true", help="Run daily at 08:00 IST")
    parser.add_argument("--tip",       type=str, default="", help="Manual news tip — fed into the next slot's story selection")
    parser.add_argument("--single",    type=str, default="", help="Write and publish ONE article on a specific topic")
    parser.add_argument("--url",       type=str, default="", help="Rewrite and publish article from a source URL")
    parser.add_argument("--test-post", action="store_true", help="Publish 1 draft post for testing")
    args = parser.parse_args()

    if args.url:
        source_url = args.url
        log.info(f"URL rewrite mode — source: {source_url}")
        story = fetch_article_from_url(source_url)
        if not story:
            log.error("Could not fetch article from URL — aborting")
            sys.exit(1)
        date_str = datetime.now(IST).isoformat()
        story.update({
            "type":          "exclusive",
            "category":      "industry-insights",
            "tags":          [],
            "is_breaking":   False,
            "focus_keyword": " ".join(story["title"].split()[:4]),
        })
        log.info(f"  Source title: {story['title'][:70]}")
        post_data = generate_news_post(story, date_str)
        log.info(f"  Generated title: {post_data['title']}")
        img = (
            extract_source_image(source_url) or
            fetch_unsplash_image(post_data["focus_keyword"]) or
            fetch_pexels_image(post_data["focus_keyword"]) or
            make_fallback_image(story["title"])
        )
        url_kw_fn = re.sub(r"[^a-z0-9-]", "", post_data["focus_keyword"].lower().replace(" ", "-"))
        media_id, _ = upload_image_to_wp(img, f"{url_kw_fn}-rewrite.jpg", post_data["focus_keyword"])
        result = publish_post(post_data, media_id, sticky=False)
        if result:
            post_url = result.get("url", result.get("link", ""))
            log.info(f"  Published: {post_url}")
            ping_indexing(post_url)
            seed_post_views(result.get("id"))
            try:
                from social_poster import post_to_all
                post_to_all(post_data["title"], post_url, post_data["tags"], category=post_data["category_slug"])
            except Exception as e:
                log.warning(f"Social posting failed: {e}")
        else:
            log.error("  Publish failed")

    elif args.single:
        topic    = args.single
        date_str = datetime.now(IST).isoformat()
        log.info(f"Single post mode — topic: {topic}")
        # Treat as an exclusive blog-style post
        story = {
            "title":          topic,
            "summary":        topic,
            "url":            WP_URL,
            "source":         "TMT Editorial",
            "type":           "exclusive",
            "category":       "industry-insights",
            "tags":           [],
            "is_breaking":    False,
            "focus_keyword":  " ".join(topic.split()[:4]),
        }
        post_data = generate_news_post(story, date_str)
        log.info(f"  Generated title: {post_data['title']}")
        img = (
            fetch_unsplash_image(post_data["focus_keyword"]) or
            fetch_pexels_image(post_data["focus_keyword"]) or
            make_fallback_image(topic)
        )
        single_kw_fn = re.sub(r"[^a-z0-9-]", "", post_data["focus_keyword"].lower().replace(" ", "-"))
        media_id, _ = upload_image_to_wp(img, f"{single_kw_fn}.jpg", post_data["focus_keyword"])
        result   = publish_post(post_data, media_id, sticky=False)
        if result:
            post_url = result.get("url", result.get("link", ""))
            log.info(f"  Published: {post_url}")
            ping_indexing(post_url)
            seed_post_views(result.get("id"))
            try:
                from social_poster import post_to_all
                post_to_all(post_data["title"], post_url, post_data["tags"], category=post_data["category_slug"])
            except Exception as e:
                log.warning(f"Social posting failed: {e}")
        else:
            log.error("  Publish failed")

    elif args.test_post:
        log.info("Test mode — generating 1 full draft post (with category, tags, Rank Math meta)...")
        stories = fetch_all_stories()
        if stories:
            selected = select_stories(stories, get_trending_from_stories(stories))
            if selected:
                story    = selected[0]
                date_str = datetime.now(IST).isoformat()
                post_data = generate_news_post(story, date_str)
                log.info(f"  Title: {post_data['title'][:60]}")
                log.info(f"  Category: {post_data['category_slug']}  Tags: {post_data['tags']}")
                log.info(f"  Focus keyword: {post_data['focus_keyword']}")
                img      = extract_source_image(story.get("url", "")) or fetch_unsplash_image(post_data["focus_keyword"]) or fetch_pexels_image(post_data["focus_keyword"]) or make_fallback_image(story["title"])
                test_kw_fn = re.sub(r"[^a-z0-9-]", "", post_data["focus_keyword"].lower().replace(" ", "-"))
                media_id, _ = upload_image_to_wp(img, f"{test_kw_fn}-test.jpg", post_data["focus_keyword"])
                result   = publish_post(post_data, media_id, sticky=False, draft=True)
                if result:
                    pid = result["id"]
                    log.info(f"Test draft created — ID {pid}")
                    log.info(f"Preview: {WP_URL}/?p={pid}")
                    log.info(f"Edit:    {WP_URL}/wp-admin/post.php?post={pid}&action=edit")
                else:
                    log.error("Draft creation failed")
    elif args.slot:
        run_daily(slot=args.slot, exclusive_tip=args.tip)
    elif args.run_now or args.tip:
        run_daily(exclusive_tip=args.tip)
    elif args.schedule:
        run_scheduler()
    else:
        parser.print_help()
