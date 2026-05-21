"""
social_poster.py — Auto-post every published article to all TMT social channels.
Called automatically by mobiletimes_agent.py and breaking_monitor.py after each publish.

Platforms:
  - Telegram  (easiest — just create bot + channel, no approval needed)
  - Twitter/X (requires API v2 developer app)
  - LinkedIn  (requires company page + developer app)
  - Facebook  (requires page access token via Meta)

Set credentials in .env — each platform is independent and skips gracefully if not set.
"""

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("tmt.social")

# ─── Credentials ──────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL    = os.getenv("TELEGRAM_CHANNEL", "")        # @TheMobileTimes or -100xxxxxxxx

TWITTER_API_KEY     = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET  = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN= os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET=os.getenv("TWITTER_ACCESS_SECRET", "")

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_ORG_ID       = os.getenv("LINKEDIN_ORG_ID", "")       # numeric ID from company page URL

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PAGE_ID      = os.getenv("META_PAGE_ID", "")

# ─── Hashtag Strategy ─────────────────────────────────────────────────────────
# Category-specific + tag-specific hashtags. Max 4 per post to avoid spam filters.

CATEGORY_HASHTAGS = {
    "5g-networks":          ["#5GIndia", "#5G", "#TelecomIndia"],
    "smartphones-tablets":  ["#Smartphones", "#MobileIndia", "#TechIndia"],
    "cybersecurity":        ["#Cybersecurity", "#InfoSec", "#TechSecurity"],
    "ai-machine-learning":  ["#AI", "#ArtificialIntelligence", "#TechIndia"],
    "policy-updates":       ["#TRAI", "#TelecomPolicy", "#IndiaPolicy"],
    "market-trends":        ["#TelecomIndia", "#IndiaMarkets", "#BusinessIndia"],
    "ott-streaming":        ["#OTT", "#JioHotstar", "#StreamingIndia"],
    "industry-trends":      ["#TelecomIndia", "#IndiaInfra", "#5G"],
    "industry-insights":    ["#TelecomInsights", "#IndiaInfra", "#TechIndia"],
    "exclusive":            ["#Exclusive", "#TelecomIndia", "#BreakingNews"],
    "how-to-guides":        ["#HowTo", "#TelecomTips", "#IndiaDigital"],
}

TAG_HASHTAGS = {
    "trending":      ["#Trending", "#IndiaNews"],
    "breaking-news": ["#BreakingNews", "#Breaking"],
    "new-launch":    ["#NewLaunch", "#TechLaunch"],
}

BASE_HASHTAGS = ["#TheMobileTimes", "#TelecomIndia"]


def build_hashtags(tags: list, category: str = "", max_tags: int = 4) -> str:
    chosen = []
    if category and category in CATEGORY_HASHTAGS:
        chosen.extend(CATEGORY_HASHTAGS[category][:2])
    for tag in (tags or []):
        if tag in TAG_HASHTAGS:
            chosen.extend(TAG_HASHTAGS[tag][:1])
    chosen.extend(BASE_HASHTAGS)
    seen, unique = set(), []
    for h in chosen:
        if h not in seen:
            seen.add(h)
            unique.append(h)
    return " ".join(unique[:max_tags])


# ─── Telegram ─────────────────────────────────────────────────────────────────

def post_to_telegram(title: str, url: str, tags: list, category: str = "") -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL:
        log.warning("Telegram credentials not set — skipping")
        return False
    try:
        is_breaking = "breaking-news" in (tags or [])
        header = "🚨 <b>BREAKING — The Mobile Times</b>" if is_breaking else "📡 <b>The Mobile Times</b>"
        text   = f"{header}\n\n{title}\n\n<a href=\"{url}\">Read full story →</a>"
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHANNEL, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10,
        )
        if r.ok:
            log.info("  Telegram ✓")
            return True
        log.warning(f"  Telegram failed ({r.status_code}): {r.text[:100]}")
        return False
    except Exception as e:
        log.warning(f"  Telegram error: {e}")
        return False


# ─── Twitter / X ──────────────────────────────────────────────────────────────

def post_to_twitter(title: str, url: str, tags: list, category: str = "") -> bool:
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        log.warning("Twitter credentials not set — skipping")
        return False
    try:
        import tweepy
        client   = tweepy.Client(
            consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET,
        )
        hashtags  = build_hashtags(tags, category, max_tags=4)
        title_part = title if len(title) <= 200 else title[:197] + "..."
        tweet     = f"{title_part}\n\n{url}\n\n{hashtags}"
        client.create_tweet(text=tweet[:280])
        log.info("  Twitter ✓")
        return True
    except Exception as e:
        log.warning(f"  Twitter error: {e}")
        return False


# ─── LinkedIn ─────────────────────────────────────────────────────────────────

def post_to_linkedin(title: str, url: str, tags: list, category: str = "") -> bool:
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_ORG_ID:
        log.warning("LinkedIn credentials not set — skipping")
        return False
    try:
        hashtags = build_hashtags(tags, category, max_tags=5)
        text     = f"{title}\n\n{hashtags}\n\n{url}"
        payload  = {
            "author": f"urn:li:organization:{LINKEDIN_ORG_ID}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary":    {"text": text},
                    "shareMediaCategory": "ARTICLE",
                    "media": [{"status": "READY", "originalUrl": url,
                               "title": {"text": title[:200]}}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        r = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={"Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
                     "Content-Type": "application/json",
                     "X-Restli-Protocol-Version": "2.0.0"},
            json=payload, timeout=15,
        )
        if r.ok:
            log.info("  LinkedIn ✓")
            return True
        log.warning(f"  LinkedIn failed ({r.status_code}): {r.text[:100]}")
        return False
    except Exception as e:
        log.warning(f"  LinkedIn error: {e}")
        return False


# ─── Facebook ─────────────────────────────────────────────────────────────────

def post_to_facebook(title: str, url: str, tags: list, category: str = "") -> bool:
    if not META_ACCESS_TOKEN or not META_PAGE_ID:
        log.warning("Facebook credentials not set — skipping")
        return False
    try:
        hashtags = build_hashtags(tags, category, max_tags=4)
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{META_PAGE_ID}/feed",
            params={"access_token": META_ACCESS_TOKEN},
            json={"message": f"{title}\n\n{hashtags}", "link": url},
            timeout=15,
        )
        if r.ok:
            log.info("  Facebook ✓")
            return True
        log.warning(f"  Facebook failed ({r.status_code}): {r.text[:100]}")
        return False
    except Exception as e:
        log.warning(f"  Facebook error: {e}")
        return False


# ─── Post to All ──────────────────────────────────────────────────────────────

def post_to_all(title: str, url: str, tags: list = None, category: str = "") -> int:
    """Post to all configured platforms. Returns count of successful posts."""
    log.info(f"Social posting: {title[:60]}...")
    t = tags or []
    results = [
        post_to_telegram(title, url, t, category),
        post_to_twitter(title, url, t, category),
        post_to_linkedin(title, url, t, category),
        post_to_facebook(title, url, t, category),
    ]
    count = sum(results)
    log.info(f"Social: {count}/4 platforms posted")
    return count


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing social poster with a sample post...")
    results_count = post_to_all(
        title    = "Test: India 5G Networks Reach 100 Million Subscribers",
        url      = "https://themobiletimes.com",
        tags     = ["trending"],
        category = "5g-networks",
    )
    print(f"Posted to {results_count} platforms")
