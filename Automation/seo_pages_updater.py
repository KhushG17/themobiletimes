"""
seo_pages_updater.py — Sets Rank Math SEO meta on all WordPress Pages.

Behaviour per page type:
  - Content pages (about, contact, media-kit, etc.) → Claude Haiku generates
    focused keyword + meta description, then pushes via Rank Math updateMeta
  - Legal pages (privacy-policy, terms-conditions) → sets noindex
  - Home/catch-all pages → skipped
"""

import os, sys, re, base64, json, requests
from dotenv import load_dotenv
import anthropic
import pytz
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

WP_URL        = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER       = os.getenv("WP_USER")
WP_PASS       = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

creds = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR   = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

IST          = pytz.timezone("Asia/Kolkata")
CURRENT_YEAR = str(datetime.now(IST).year)

# ─── Page config ─────────────────────────────────────────────────────────────
# noindex=True  → mark as noindex, no meta description needed
# skip=True     → ignore entirely
# hint          → extra context passed to Claude for better generation

PAGE_CONFIG = {
    "about": {
        "hint": "About page for The Mobile Times — India's leading telecom and technology news publication. Editor: Sanjay Goyal.",
    },
    "contact": {
        "hint": "Contact page for The Mobile Times. Readers can submit news tips, press releases, or advertising inquiries.",
    },
    "media-kit": {
        "hint": "Media kit / advertise page for The Mobile Times. Brands and agencies can advertise to India's telecom and tech audience.",
    },
    "post-a-press-release": {
        "hint": "Page where companies can submit press releases to be published on The Mobile Times and reach India's telecom industry.",
    },
    "newsletter-subscription": {
        "hint": "Newsletter signup page. Readers subscribe to get daily telecom, 5G and smartphone news from India.",
    },
    "may-2026": {
        "hint": "The Mobile Times May 2026 issue / archive page — monthly roundup of India telecom and technology news.",
    },
    "privacy-policy":   {"noindex": True},
    "terms-conditions": {"noindex": True},
    "home":             {"skip": True},
}


def strip_html(t: str) -> str:
    return re.sub(r"<[^>]+>", " ", t).strip()


def get_page_content(page_id: int) -> str:
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/pages/{page_id}",
        headers=HDR,
        params={"_fields": "content"},
        timeout=15
    )
    if r.ok:
        return strip_html(r.json().get("content", {}).get("rendered", ""))[:800]
    return ""


def generate_page_seo(title: str, content_snippet: str, hint: str) -> dict:
    prompt = f"""You are an SEO expert for The Mobile Times — India's leading telecom and technology news publication.

Page title: {title}
Page hint: {hint}
Content snippet: {content_snippet[:500]}

Generate:
1. focus_keyword — The single best 2–4 word keyword this page should rank for.
   Rules: specific, searchable, what someone would type in Google, relevant to India.
2. meta_description — Compelling meta description, EXACTLY 130–155 characters.
   Rules: includes focus keyword naturally, describes the page value clearly, ends with a subtle CTA.
   Do NOT start with "The Mobile Times", "Discover", or "Learn".

Respond ONLY with valid JSON, no extra text:
{{"focus_keyword": "...", "meta_description": "..."}}"""

    msg = ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def set_rank_math_meta(page_id: int, focus_keyword: str = "", meta_description: str = "",
                       noindex: bool = False) -> bool:
    meta = {}
    if noindex:
        meta["rank_math_robots"] = ["noindex"]
    else:
        meta["rank_math_focus_keyword"] = focus_keyword
        meta["rank_math_description"]   = meta_description

    payload = {
        "objectID":   page_id,
        "objectType": "post",   # Rank Math uses "post" for all post types including pages
        "meta":       meta,
    }
    r = requests.post(
        f"{WP_URL}/wp-json/rankmath/v1/updateMeta",
        headers=HDR,
        json=payload,
        timeout=15
    )
    return r.status_code == 200 and r.json().get("slug") is True


def get_all_pages() -> list[dict]:
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/pages",
        headers=HDR,
        params={"per_page": 100, "status": "publish",
                "_fields": "id,slug,title,link"},
        timeout=15
    )
    return r.json() if r.ok else []


def main():
    print("Fetching WordPress pages...")
    pages = get_all_pages()
    print(f"Found {len(pages)} pages\n{'='*60}")

    results = []
    for page in pages:
        pid   = page["id"]
        slug  = page["slug"]
        title = strip_html(page["title"]["rendered"])
        url   = page.get("link", "")
        cfg   = PAGE_CONFIG.get(slug, {})

        if cfg.get("skip"):
            print(f"  [SKIP]    [{pid}] /{slug}/")
            continue

        if cfg.get("noindex"):
            print(f"  [NOINDEX] [{pid}] /{slug}/ — {title[:50]}")
            ok = set_rank_math_meta(pid, noindex=True)
            results.append({"id": pid, "slug": slug, "title": title,
                            "action": "noindex", "status": "OK" if ok else "FAILED"})
            if ok:
                print(f"    noindex set")
            else:
                print(f"    FAILED to set noindex")
            continue

        # Generate SEO for content pages
        print(f"  [SEO]     [{pid}] /{slug}/ — {title[:50]}")
        hint = cfg.get("hint", f"{title} — page on The Mobile Times, India telecom news site.")

        try:
            content = get_page_content(pid)
            seo     = generate_page_seo(title, content, hint)
            kw      = seo["focus_keyword"]
            desc    = seo["meta_description"]

            if len(desc) > 160:
                desc = desc[:157] + "..."

            ok = set_rank_math_meta(pid, focus_keyword=kw, meta_description=desc)
            status = "OK" if ok else "API error"
            results.append({"id": pid, "slug": slug, "title": title,
                            "keyword": kw, "description": desc, "status": status})
            print(f"    Keyword: {kw}")
            print(f"    Desc ({len(desc)} chars): {desc}")
            print(f"    {status}")

        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"id": pid, "slug": slug, "title": title,
                            "error": str(e), "status": "FAILED"})
        print()

    print("=" * 60)
    ok_count = sum(1 for r in results if r["status"] in ("OK",))
    print(f"Done. {ok_count}/{len(results)} pages updated.")

    with open("seo_pages_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Report saved to seo_pages_report.json")


if __name__ == "__main__":
    main()
