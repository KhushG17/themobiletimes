"""
tmt_engine.py — The Mobile Times Unified Publishing Engine v2.0

Architecture:
  - SQLite queue stores every story ever seen (prevents ALL duplicates)
  - Scraper thread runs every 2 hours: fetches RSS, scores, queues clean stories
  - Publisher thread runs every 30 min: posts 1 story if it's time (4-5/day max)
  - Telegram bot: receive commands from anywhere, inject custom stories

Posting schedule (IST):
  Slot 1: 08:00 | Slot 2: 10:30 | Slot 3: 13:00 | Slot 4: 16:00 | Slot 5: 19:00
  Breaking news: any time, immediately when urgency >= 7

Telegram commands:
  /status   — queue size, last post, next post time
  /queue    — list top 5 pending stories
  /post <url or headline> — inject a story to post next
  /skip     — skip the top story in queue
  /run      — force post right now (ignores time slots)
  /pause    — pause auto-posting
  /resume   — resume auto-posting

Deploy: Railway.app — push repo, set env vars, runs forever.
"""

import os, sys, re, json, base64, time, random, logging, hashlib, threading, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser
import anthropic
import pytz
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tmt_engine.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("tmt")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── Config ──────────────────────────────────────────────────────────────────
WP_URL        = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER       = os.getenv("WP_USER")
WP_PASS       = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
PEXELS_KEY    = os.getenv("PEXELS_API_KEY")
TELEGRAM_TOKEN= os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")   # Your personal chat ID
DB_PATH       = os.getenv("DB_PATH", "tmt_queue.db")
LOGO_PATH     = os.getenv("LOGO_PATH", "circle-logo.png")

IST           = pytz.timezone("Asia/Kolkata")
CURRENT_YEAR  = str(datetime.now(IST).year)
AUTHOR_NAME   = "Sanjay Goyal"
AUTHOR_URL    = "https://themobiletimes.com/author/sanjay/"

creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
WP_HDR  = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
ai      = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# Daily post slots in IST
POST_SLOTS_IST = ["08:00", "10:30", "13:00", "16:00", "19:00"]
MAX_POSTS_PER_DAY = 5
SCRAPE_INTERVAL_MINUTES = 120   # scrape every 2 hours
PUBLISH_CHECK_MINUTES   = 30    # check if time to post every 30 min
BREAKING_URGENCY_MIN    = 7     # urgency score to trigger immediate publish

# Global pause flag
_paused = False

# ─── RSS Feeds ───────────────────────────────────────────────────────────────
RSS_FEEDS = [
    "https://economictimes.indiatimes.com/tech/telecom/rssfeeds/13357270.cms",
    "https://telecomtalk.info/feed/",
    "https://www.medianama.com/feed/",
    "https://entrackr.com/feed/",
    "https://www.lightreading.com/rss.xml",
    "https://www.fiercetelecom.com/rss.xml",
    "https://www.telecompaper.com/rss/all-news.xml",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/feed/",
]

CATEGORY_IDS = {
    "5g-networks": 160, "accessories-wearables": 151, "ai-machine-learning": 156,
    "ar-vr": 163, "case-studies": 143, "cybersecurity": 155, "data-analytics": 157,
    "devices-hardware": 129, "ev-smart-grids": 164, "exclusive": 121,
    "how-to-guides": 142, "industry-insights": 141, "industry-trends": 159,
    "insights": 140, "internet-of-things": 165, "market-trends": 123,
    "network-smart-devices": 152, "ott-streaming": 162, "policy-updates": 122,
    "press-releases": 144, "smartphones-tablets": 150, "software": 154,
    "tech-innovation": 161, "technologies": 153,
}

AUTHORITY_LINKS = [
    ("TRAI", "https://www.trai.gov.in"),
    ("DOT", "https://dot.gov.in"),
    ("GSMA", "https://www.gsma.com"),
    ("COAI", "https://www.coai.in"),
]

PILLAR_LINKS = {
    "5g":           f"{WP_URL}/5g-india-guide-2026/",
    "jio":          f"{WP_URL}/jio-vs-airtel-2026-comparison/",
    "airtel":       f"{WP_URL}/jio-vs-airtel-2026-comparison/",
    "trai":         f"{WP_URL}/trai-regulations-india-2026/",
    "cybersecurity":f"{WP_URL}/cybersecurity-india-guide-2026/",
    "ott":          f"{WP_URL}/ott-streaming-india-2026/",
    "bsnl":         f"{WP_URL}/bsnl-revival-plan-2026/",
    "smartphone":   f"{WP_URL}/best-smartphones-india-2026/",
    "iot":          f"{WP_URL}/iot-india-market-2026/",
    "telecom market":f"{WP_URL}/india-telecom-market-2026/",
}

STOPWORDS = {
    "the","and","for","with","from","that","this","are","was","has","its",
    "have","will","india","2026","2025","2024","new","how","what","why","top"
}


# ─── Database ─────────────────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash      TEXT UNIQUE,
            title         TEXT,
            source_url    TEXT,
            source_name   TEXT,
            summary       TEXT,
            fetched_at    TEXT,
            urgency       INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'pending',
            manual        INTEGER DEFAULT 0,
            published_at  TEXT,
            wp_url        TEXT,
            wp_id         INTEGER
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_status ON stories(status)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_fetched ON stories(fetched_at)")
    con.commit()
    con.close()
    log.info(f"DB initialised: {DB_PATH}")


def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def story_hash(title: str, url: str = "") -> str:
    """Stable hash for deduplication."""
    key = (title + url).lower().strip()
    return hashlib.md5(key.encode()).hexdigest()


def is_known(title: str, url: str = "") -> bool:
    """Check if this story (or a similar one) is already in the DB."""
    h = story_hash(title, url)
    con = db()

    # Exact hash match
    row = con.execute("SELECT 1 FROM stories WHERE url_hash=?", (h,)).fetchone()
    if row:
        con.close()
        return True

    # Semantic overlap check against last 200 stories
    rows = con.execute(
        "SELECT title FROM stories ORDER BY id DESC LIMIT 200"
    ).fetchall()
    con.close()

    title_lower = title.lower()
    words = set(re.findall(r"\b\w{3,}\b", title_lower)) - STOPWORDS
    if not words:
        return False

    for (pub_title,) in rows:
        pub_words = set(re.findall(r"\b\w{3,}\b", pub_title.lower())) - STOPWORDS
        if not pub_words:
            continue
        overlap = len(words & pub_words) / max(len(words), 1)
        if overlap >= 0.45:
            return True

        # Brand/entity match: shared capitalised terms + 2+ other words
        brands_new = {w.lower() for w in re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", title)}
        brands_pub = {w.lower() for w in re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", pub_title)}
        if len(brands_new & brands_pub) >= 1 and len(words & pub_words) >= 2:
            return True

    return False


def add_story(title: str, url: str, source: str, summary: str,
              urgency: int = 0, manual: bool = False):
    """Add a new story to the queue."""
    h = story_hash(title, url)
    now = datetime.now(IST).isoformat()
    try:
        con = db()
        con.execute("""
            INSERT INTO stories (url_hash, title, source_url, source_name, summary,
                                 fetched_at, urgency, status, manual)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (h, title[:300], url, source, summary[:500], now, urgency, 1 if manual else 0))
        con.commit()
        con.close()
        return True
    except sqlite3.IntegrityError:
        return False  # already in DB


def get_next_story(breaking_only: bool = False) -> dict | None:
    """Pop the best pending story from the queue."""
    con = db()
    if breaking_only:
        row = con.execute("""
            SELECT id, title, source_url, source_name, summary, urgency, manual
            FROM stories WHERE status='pending' AND urgency >= ?
            ORDER BY manual DESC, urgency DESC, id ASC LIMIT 1
        """, (BREAKING_URGENCY_MIN,)).fetchone()
    else:
        row = con.execute("""
            SELECT id, title, source_url, source_name, summary, urgency, manual
            FROM stories WHERE status='pending'
            ORDER BY manual DESC, urgency DESC, id ASC LIMIT 1
        """).fetchone()
    con.close()
    if not row:
        return None
    keys = ["id", "title", "source_url", "source_name", "summary", "urgency", "manual"]
    return dict(zip(keys, row))


def mark_published(story_id: int, wp_url: str, wp_id: int):
    now = datetime.now(IST).isoformat()
    con = db()
    con.execute("""
        UPDATE stories SET status='published', published_at=?, wp_url=?, wp_id=?
        WHERE id=?
    """, (now, wp_url, wp_id, story_id))
    con.commit()
    con.close()


def mark_skipped(story_id: int):
    con = db()
    con.execute("UPDATE stories SET status='skipped' WHERE id=?", (story_id,))
    con.commit()
    con.close()


def queue_stats() -> dict:
    con = db()
    pending  = con.execute("SELECT COUNT(*) FROM stories WHERE status='pending'").fetchone()[0]
    breaking = con.execute("SELECT COUNT(*) FROM stories WHERE status='pending' AND urgency>=?",
                           (BREAKING_URGENCY_MIN,)).fetchone()[0]
    published_today = con.execute("""
        SELECT COUNT(*) FROM stories
        WHERE status='published' AND published_at >= ?
    """, (datetime.now(IST).strftime("%Y-%m-%d"),)).fetchone()[0]
    last_pub = con.execute("""
        SELECT title, wp_url FROM stories
        WHERE status='published' ORDER BY published_at DESC LIMIT 1
    """).fetchone()
    top5 = con.execute("""
        SELECT title, urgency, manual FROM stories
        WHERE status='pending'
        ORDER BY manual DESC, urgency DESC LIMIT 5
    """).fetchall()
    con.close()
    return {
        "pending": pending, "breaking": breaking,
        "published_today": published_today,
        "last_published": last_pub,
        "top5": top5,
    }


# ─── Scraper ─────────────────────────────────────────────────────────────────

def score_urgency(title: str, summary: str) -> int:
    """Quick heuristic urgency score 0-10 (no AI call, saves cost)."""
    text = (title + " " + summary).lower()
    score = 3  # baseline

    # Breaking signals
    for kw in ["breaking", "just in", "urgent", "alert", "shutdown", "ban", "crash",
               "hack", "breach", "down", "outage", "arrested", "raided", "fined"]:
        if kw in text: score += 2; break

    # India + telecom relevance boost
    india_kws = ["india", "jio", "airtel", "bsnl", "trai", "dot ", "indian"]
    if any(k in text for k in india_kws): score += 1

    # Recency signal (if title has today/yesterday)
    if any(k in text for k in ["today", "yesterday", "hours ago", "just"]): score += 1

    return min(score, 10)


def scrape_all_feeds() -> int:
    """Scrape all RSS feeds, score stories, add new ones to queue."""
    added = 0
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            source = feed.feed.get("title", feed_url)
            for entry in feed.entries[:10]:
                title   = entry.get("title", "").strip()
                url     = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                summary = re.sub(r"<[^>]+>", " ", summary).strip()[:500]

                if not title or len(title) < 15:
                    continue
                if is_known(title, url):
                    continue

                urgency = score_urgency(title, summary)
                if add_story(title, url, source, summary, urgency):
                    added += 1
                    log.debug(f"  Queued [{urgency}]: {title[:60]}")
        except Exception as e:
            log.warning(f"Feed error ({feed_url[:40]}): {e}")

    log.info(f"Scrape complete — {added} new stories queued")
    return added


# ─── Article Generation ───────────────────────────────────────────────────────

def generate_article(story: dict) -> dict | None:
    """Generate full article HTML + metadata using Claude Sonnet."""
    is_breaking = story["urgency"] >= BREAKING_URGENCY_MIN
    word_target = "380-440" if is_breaking else "550-700"

    prompt = f"""You are a senior journalist at The Mobile Times — India's leading telecom and technology news publication.

Write a {'BREAKING NEWS' if is_breaking else 'news'} article based on this story.

Title: {story['title']}
Source: {story['source_name']}
Summary: {story['summary']}
URL: {story['source_url']}

Requirements:
- Word count: {word_target} words
- Structure: strong news hook in first sentence, H2 subheadings every 100-130 words
- Include India-specific context and impact even if the story is global
- Named companies, people, and data points where available
- {'Bold first paragraph, concise urgent tone' if is_breaking else 'Professional trade-focused tone for mobile retailers and telecom professionals'}
- End with "What This Means" or "Industry Outlook" section
- Current year is {CURRENT_YEAR} — never reference past years as current

Format: clean HTML only (h2, p, ul/li, strong). No divs. No inline styles.
Do NOT wrap in ```html fences.

After the HTML, write exactly:

META_JSON:
{{
  "article_title": "SEO title under 65 chars with keyword and year",
  "slug": "url-slug",
  "focus_keyword": "2-4 word keyword phrase",
  "meta_description": "compelling 140-155 char description with keyword",
  "category_slug": "one of: {', '.join(list(CATEGORY_IDS.keys())[:15])}",
  "tags": ["tag1", "tag2"],
  "is_breaking": {'true' if is_breaking else 'false'}
}}"""

    try:
        r = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2800,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = r.content[0].text.strip()
    except Exception as e:
        log.error(f"Claude error: {e}")
        return None

    # Parse HTML + META_JSON
    if "META_JSON:" in raw:
        parts        = raw.split("META_JSON:", 1)
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

    # Strip any accidental markdown fences
    html_content = re.sub(r"^```html?\s*\n?", "", html_content, flags=re.IGNORECASE)
    html_content = re.sub(r"\n?```\s*$", "", html_content)

    # Fix years
    for yr in ["2020", "2021", "2022", "2023", "2024", "2025"]:
        html_content = html_content.replace(yr, CURRENT_YEAR)

    # Inject pillar page links
    for keyword, url in PILLAR_LINKS.items():
        if keyword.lower() in html_content.lower():
            html_content = re.sub(
                rf"\b({re.escape(keyword)})\b",
                f'<a href="{url}">\g<1></a>',
                html_content, count=1, flags=re.IGNORECASE
            )

    # Inject authority links
    auth_links = random.sample(AUTHORITY_LINKS, min(2, len(AUTHORITY_LINKS)))
    auth_html  = " | ".join(f'<a href="{u}" target="_blank" rel="noopener">{n}</a>' for n, u in auth_links)
    html_content += f'\n<p class="tmt-sources"><strong>Sources:</strong> {auth_html}</p>'

    # Build schema
    date_str = datetime.now(IST).isoformat()
    schema = {
        "@context": "https://schema.org",
        "@type":    "NewsArticle",
        "headline": meta.get("article_title", story["title"])[:110],
        "datePublished": date_str,
        "dateModified":  date_str,
        "author":    {"@type": "Person", "name": AUTHOR_NAME, "url": AUTHOR_URL},
        "publisher": {
            "@type": "NewsMediaOrganization", "name": "The Mobile Times",
            "url": WP_URL,
            "logo": {"@type": "ImageObject", "url": f"{WP_URL}/wp-content/uploads/circle-logo.png"},
        },
        "inLanguage":    "en-IN",
        "keywords":      meta.get("focus_keyword", ""),
        "isAccessibleForFree": True,
    }
    html_content += f'\n<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    if is_breaking:
        html_content = '<span class="tmt-breaking-badge">BREAKING</span>\n' + html_content

    return {
        "title":        meta.get("article_title", story["title"]),
        "slug":         meta.get("slug", ""),
        "content":      html_content,
        "focus_kw":     meta.get("focus_keyword", "India telecom"),
        "meta_desc":    meta.get("meta_description", ""),
        "category_slug":meta.get("category_slug", "industry-trends"),
        "tags":         meta.get("tags", []),
        "is_breaking":  meta.get("is_breaking", is_breaking),
        "source_url":   story["source_url"],
    }


# ─── Image ────────────────────────────────────────────────────────────────────

def fetch_pexels_image(query: str) -> bytes | None:
    if not PEXELS_KEY:
        return None
    try:
        r = requests.get("https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=10)
        if r.ok:
            photos = r.json().get("photos", [])
            if photos:
                img_url = random.choice(photos)["src"]["large"]
                return requests.get(img_url, timeout=15).content
    except Exception as e:
        log.warning(f"Pexels error: {e}")
    return None


def upload_image(img_bytes: bytes, filename: str) -> int | None:
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            headers={"Authorization": f"Basic {creds}",
                     "Content-Disposition": f'attachment; filename="{filename}"',
                     "Content-Type": "image/jpeg"},
            data=img_bytes, timeout=30
        )
        if r.ok:
            return r.json().get("id")
    except Exception as e:
        log.warning(f"Image upload error: {e}")
    return None


def get_featured_image(title: str) -> int | None:
    query  = re.sub(r"[^a-zA-Z0-9 ]", "", title)[:40]
    img    = fetch_pexels_image(query) or fetch_pexels_image("India technology telecom")
    if img:
        fname = re.sub(r"\s+", "-", query.lower()[:30]) + ".jpg"
        return upload_image(img, fname)
    return None


# ─── Publisher ────────────────────────────────────────────────────────────────

def get_or_create_tags(names: list) -> list:
    ids = []
    for name in names[:4]:
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower().strip())[:50]
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags", headers=WP_HDR,
                params={"slug": slug}, timeout=10)
        if r.ok and r.json():
            ids.append(r.json()[0]["id"])
        else:
            r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", headers=WP_HDR,
                    json={"name": name, "slug": slug}, timeout=10)
            if r2.ok:
                ids.append(r2.json()["id"])
    return ids


def publish_article(article: dict, sticky: bool = False) -> tuple[int, str] | None:
    cat_id  = CATEGORY_IDS.get(article["category_slug"], CATEGORY_IDS["industry-trends"])
    tag_ids = get_or_create_tags(article.get("tags", []))
    media_id = get_featured_image(article["title"])

    payload = {
        "title":           article["title"],
        "content":         article["content"],
        "status":          "publish",
        "slug":            article["slug"],
        "categories":      [cat_id],
        "tags":            tag_ids,
        "sticky":          sticky,
        "author":          1,
    }
    if media_id:
        payload["featured_media"] = media_id

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=WP_HDR,
            json=payload, timeout=30)
    if not r.ok:
        log.error(f"WP publish failed: {r.status_code} {r.text[:200]}")
        return None

    wp_id  = r.json()["id"]
    wp_url = r.json().get("link", "")

    # Push Rank Math SEO
    requests.post(f"{WP_URL}/wp-json/rankmath/v1/updateMeta", headers=WP_HDR,
        json={"objectID": wp_id, "objectType": "post",
              "meta": {"rank_math_focus_keyword": article["focus_kw"],
                       "rank_math_description":   article["meta_desc"]}},
        timeout=15)

    return wp_id, wp_url


# ─── Scheduling Logic ─────────────────────────────────────────────────────────

def get_posts_today() -> int:
    con = db()
    count = con.execute("""
        SELECT COUNT(*) FROM stories
        WHERE status='published' AND published_at >= ?
    """, (datetime.now(IST).strftime("%Y-%m-%d"),)).fetchone()[0]
    con.close()
    return count


def is_posting_time() -> bool:
    """Returns True if we're within 20 min of a scheduled slot and haven't posted too many today."""
    if _paused:
        return False
    if get_posts_today() >= MAX_POSTS_PER_DAY:
        return False

    now_ist = datetime.now(IST)
    for slot in POST_SLOTS_IST:
        h, m = map(int, slot.split(":"))
        slot_time = now_ist.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = abs((now_ist - slot_time).total_seconds())
        if diff <= 20 * 60:  # within 20 min window
            return True
    return False


def notify_telegram(message: str):
    """Send a message to the owner via Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception:
        pass


# ─── Threads ──────────────────────────────────────────────────────────────────

def scraper_thread():
    """Runs every SCRAPE_INTERVAL_MINUTES. Fetches feeds, queues new stories."""
    log.info("Scraper thread started")
    while True:
        try:
            added = scrape_all_feeds()
            stats = queue_stats()

            # Check for breaking news — notify immediately
            if stats["breaking"] > 0:
                log.info(f"  {stats['breaking']} breaking story/stories in queue")
                notify_telegram(
                    f"🚨 <b>Breaking story queued</b>\n"
                    f"Queue: {stats['pending']} pending | {stats['breaking']} breaking\n"
                    f"Will publish immediately."
                )
        except Exception as e:
            log.error(f"Scraper error: {e}")

        time.sleep(SCRAPE_INTERVAL_MINUTES * 60)


def publisher_thread():
    """Runs every PUBLISH_CHECK_MINUTES. Posts when it's time."""
    log.info("Publisher thread started")
    time.sleep(30)  # brief startup delay

    while True:
        try:
            # Always check for breaking news first
            breaking = get_next_story(breaking_only=True)
            if breaking and not _paused:
                log.info(f"Publishing breaking story: {breaking['title'][:60]}")
                _publish_story(breaking, is_breaking=True)

            # Regular scheduled posts
            elif is_posting_time():
                story = get_next_story()
                if story:
                    log.info(f"Publishing scheduled story: {story['title'][:60]}")
                    _publish_story(story, is_breaking=False)
                else:
                    log.warning("It's posting time but queue is empty — scraping now")
                    scrape_all_feeds()

        except Exception as e:
            log.error(f"Publisher error: {e}")

        time.sleep(PUBLISH_CHECK_MINUTES * 60)


def _publish_story(story: dict, is_breaking: bool):
    """Generate and publish a single story."""
    article = generate_article(story)
    if not article:
        log.error(f"Failed to generate article for: {story['title'][:60]}")
        mark_skipped(story["id"])
        return

    result = publish_article(article, sticky=is_breaking)
    if result:
        wp_id, wp_url = result
        mark_published(story["id"], wp_url, wp_id)
        label = "BREAKING" if is_breaking else "POST"
        log.info(f"[{label}] Published: {wp_url}")
        notify_telegram(
            f"{'🚨' if is_breaking else '📰'} <b>{'Breaking: ' if is_breaking else ''}{article['title']}</b>\n"
            f"<a href='{wp_url}'>{wp_url}</a>"
        )
    else:
        log.error(f"Failed to publish: {story['title'][:60]}")


# ─── Telegram Bot ─────────────────────────────────────────────────────────────

def telegram_bot_thread():
    """Simple Telegram bot using long-polling."""
    if not TELEGRAM_TOKEN:
        log.info("No TELEGRAM_BOT_TOKEN set — bot disabled")
        return

    log.info("Telegram bot started")
    offset = 0

    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=40
            )
            if not r.ok:
                time.sleep(5)
                continue

            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                msg    = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text    = msg.get("text", "").strip()

                # Only respond to authorised chat
                if TELEGRAM_CHAT and chat_id != TELEGRAM_CHAT:
                    continue

                handle_telegram_command(chat_id, text)

        except Exception as e:
            log.warning(f"Telegram poll error: {e}")
            time.sleep(10)


def tg_send(chat_id: str, text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception:
        pass


def handle_telegram_command(chat_id: str, text: str):
    global _paused

    if text.startswith("/status"):
        s = queue_stats()
        last = f"{s['last_published'][0][:50]}\n{s['last_published'][1]}" if s["last_published"] else "none"
        tg_send(chat_id,
            f"<b>TMT Engine Status</b>\n"
            f"Pending stories: {s['pending']}\n"
            f"Breaking in queue: {s['breaking']}\n"
            f"Posted today: {s['published_today']}/{MAX_POSTS_PER_DAY}\n"
            f"Paused: {'Yes' if _paused else 'No'}\n"
            f"Last post: {last}"
        )

    elif text.startswith("/queue"):
        s = queue_stats()
        if not s["top5"]:
            tg_send(chat_id, "Queue is empty.")
            return
        lines = ["<b>Next in queue:</b>"]
        for i, (title, urgency, manual) in enumerate(s["top5"], 1):
            tag = "🚨" if urgency >= BREAKING_URGENCY_MIN else ("📌" if manual else "📰")
            lines.append(f"{i}. {tag} {title[:60]}")
        tg_send(chat_id, "\n".join(lines))

    elif text.startswith("/skip"):
        story = get_next_story()
        if story:
            mark_skipped(story["id"])
            tg_send(chat_id, f"Skipped: {story['title'][:60]}\nNext story is now at the top.")
        else:
            tg_send(chat_id, "Queue is empty.")

    elif text.startswith("/run"):
        story = get_next_story()
        if story:
            tg_send(chat_id, f"Publishing now: {story['title'][:60]}")
            threading.Thread(target=_publish_story, args=(story, False), daemon=True).start()
        else:
            tg_send(chat_id, "Queue is empty. Scraping feeds now...")
            threading.Thread(target=scrape_all_feeds, daemon=True).start()

    elif text.startswith("/pause"):
        _paused = True
        tg_send(chat_id, "Auto-posting paused. Send /resume to restart.")

    elif text.startswith("/resume"):
        _paused = False
        tg_send(chat_id, "Auto-posting resumed.")

    elif text.startswith("/post "):
        # User sent: /post <url or headline>
        content = text[6:].strip()
        if content.startswith("http"):
            # It's a URL — fetch title from page
            try:
                r = requests.get(content, timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"})
                title_match = re.search(r"<title>(.*?)</title>", r.text, re.S)
                title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else content
                summary = ""
            except Exception:
                title = content
                summary = ""
            url = content
        else:
            title   = content
            url     = ""
            summary = ""

        if add_story(title, url, "Manual", summary, urgency=8, manual=True):
            tg_send(chat_id,
                f"Added to queue (priority): {title[:60]}\n"
                f"Send /run to publish immediately, or it will post at the next slot."
            )
        else:
            tg_send(chat_id, f"This story is already in the queue or published.")

    elif text.startswith("/help") or text.startswith("/start"):
        tg_send(chat_id,
            "<b>TMT Engine Commands:</b>\n\n"
            "/status — engine status and today's post count\n"
            "/queue — see next 5 stories in queue\n"
            "/post &lt;url or headline&gt; — add a story to post next\n"
            "/run — post right now\n"
            "/skip — skip top story\n"
            "/pause — pause auto-posting\n"
            "/resume — resume auto-posting\n"
            "/help — this message"
        )


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("TMT ENGINE v2.0 STARTING")
    log.info(f"DB: {DB_PATH}")
    log.info(f"Site: {WP_URL}")
    log.info(f"Post slots (IST): {', '.join(POST_SLOTS_IST)}")
    log.info(f"Telegram bot: {'enabled' if TELEGRAM_TOKEN else 'disabled'}")
    log.info("=" * 60)

    init_db()

    # Initial scrape on startup
    log.info("Initial scrape...")
    scrape_all_feeds()

    # Start threads
    threads = [
        threading.Thread(target=scraper_thread,      name="Scraper",    daemon=True),
        threading.Thread(target=publisher_thread,    name="Publisher",  daemon=True),
        threading.Thread(target=telegram_bot_thread, name="TelegramBot",daemon=True),
    ]
    for t in threads:
        t.start()
        log.info(f"Started: {t.name}")

    notify_telegram(
        "✅ <b>TMT Engine started</b>\n"
        f"Slots: {', '.join(POST_SLOTS_IST)} IST\n"
        "Send /status to check queue."
    )

    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Engine stopped.")


if __name__ == "__main__":
    main()
