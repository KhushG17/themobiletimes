"""
seo_meta_updater.py — Auto-generate and push focus keywords + meta descriptions
to all WordPress posts via Rank Math REST API fields.
Uses Claude Haiku to generate SEO copy per post.
"""
import os, sys, base64, json, requests
from dotenv import load_dotenv
import anthropic

# Force UTF-8 output on Windows to handle ₹, ✓ and other Unicode chars
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

WP_URL   = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER  = os.getenv("WP_USER")
WP_PASS  = os.getenv("WP_APP_PASS")
AI_KEY   = os.getenv("ANTHROPIC_API_KEY")

creds = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR   = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

ai = anthropic.Anthropic(api_key=AI_KEY)


def get_all_posts():
    posts = []
    page  = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HDR,
            params={"per_page": 100, "page": page,
                    "_fields": "id,title,content,slug,excerpt"}
        )
        if r.status_code != 200 or not r.json():
            break
        posts.extend(r.json())
        if len(r.json()) < 100:
            break
        page += 1
    return posts


def strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", text).strip()


def generate_seo(title: str, content_snippet: str) -> dict:
    prompt = f"""You are an SEO expert for The Mobile Times — India's leading telecom and technology news site.

Post title: {title}
Content snippet: {content_snippet[:600]}

Generate:
1. focus_keyword — The single best keyword phrase (2-5 words) this article should rank for in Google.
   Rules: specific, searchable, matches what someone in India would type, NO brand names.
2. meta_description — A compelling meta description (140-155 characters EXACTLY, count carefully).
   Rules: includes the focus keyword naturally, describes the article value, ends with a hook or insight.
   Do NOT start with "The Mobile Times" or "Discover" or "Learn".

Respond ONLY with valid JSON, no extra text:
{{"focus_keyword": "...", "meta_description": "..."}}"""

    msg = ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    # strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def update_post_seo(post_id: int, focus_keyword: str, meta_description: str) -> bool:
    # Try Rank Math's own REST endpoint first
    rm_payload = {
        "objectID":   post_id,
        "objectType": "post",
        "meta": {
            "rank_math_focus_keyword": focus_keyword,
            "rank_math_description":   meta_description,
        }
    }
    r = requests.post(
        f"{WP_URL}/wp-json/rankmath/v1/updateMeta",
        headers=HDR,
        json=rm_payload,
        timeout=15
    )
    if r.status_code == 200:
        return True
    # Fallback: standard WP meta endpoint
    r2 = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        headers=HDR,
        json={"meta": rm_payload["meta"]},
        timeout=15
    )
    return r2.status_code == 200


def main():
    print("Fetching posts...")
    posts = get_all_posts()
    print(f"Found {len(posts)} posts\n")

    results = []
    for post in posts:
        title   = strip_html(post["title"]["rendered"])
        content = strip_html(post["content"]["rendered"])
        pid     = post["id"]

        print(f"  [{pid}] Generating SEO for: {title[:60]}...")
        try:
            seo = generate_seo(title, content)
            kw  = seo["focus_keyword"]
            md  = seo["meta_description"]

            # Truncate if AI went over
            if len(md) > 160:
                md = md[:157] + "..."

            ok = update_post_seo(pid, kw, md)
            status = "✓ Updated" if ok else "✗ API error"
            results.append({"id": pid, "title": title, "keyword": kw,
                            "description": md, "status": status})
            print(f"    Keyword: {kw}")
            print(f"    Description ({len(md)} chars): {md}")
            print(f"    {status}\n")

        except Exception as e:
            print(f"    ERROR: {e}\n")
            results.append({"id": pid, "title": title, "error": str(e), "status": "✗ Failed"})

    print("=" * 60)
    print(f"Done. {sum(1 for r in results if '✓' in r['status'])}/{len(results)} posts updated.")

    # Save report
    report_path = "seo_meta_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
