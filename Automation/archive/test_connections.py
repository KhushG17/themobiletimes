"""
test_connections.py — Verify every API connection before running the agent.
Run this first. Everything must show ✅ before going live.
"""

import os, sys, base64, json, requests, time
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL", "https://themobiletimes.com")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
PEXELS_KEY    = os.getenv("PEXELS_API_KEY")
FAL_KEY       = os.getenv("FAL_API_KEY")

creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
WP_HDR  = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

results = []

def check(name, fn):
    try:
        msg = fn()
        print(f"  ✅ {name}: {msg}")
        results.append((name, True, msg))
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        results.append((name, False, str(e)))


# ─── WordPress ────────────────────────────────────────────────────────────────

def test_wp():
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/users/me", headers=WP_HDR, timeout=15)
    r.raise_for_status()
    return f"Logged in as '{r.json()['name']}'"

def test_wp_post():
    payload = {
        "title":   "TMT Connection Test — DELETE ME",
        "content": "<p>Test post from automation agent. Safe to delete.</p>",
        "status":  "draft",
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=WP_HDR, json=payload, timeout=15)
    r.raise_for_status()
    post_id = r.json()["id"]
    # Clean up
    requests.delete(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}?force=true", headers=WP_HDR)
    return f"Draft created & deleted (ID {post_id})"

def test_wp_media():
    # Upload a tiny 1x1 white JPEG
    pixel = bytes([
        0xff,0xd8,0xff,0xe0,0x00,0x10,0x4a,0x46,0x49,0x46,0x00,0x01,
        0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xff,0xdb,0x00,0x43,
        0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
        0x09,0x08,0x0a,0x0c,0x14,0x0d,0x0c,0x0b,0x0b,0x0c,0x19,0x12,
        0x13,0x0f,0x14,0x1d,0x1a,0x1f,0x1e,0x1d,0x1a,0x1c,0x1c,0x20,
        0x24,0x2e,0x27,0x20,0x22,0x2c,0x23,0x1c,0x1c,0x28,0x37,0x29,
        0x2c,0x30,0x31,0x34,0x34,0x34,0x1f,0x27,0x39,0x3d,0x38,0x32,
        0x3c,0x2e,0x33,0x34,0x32,0xff,0xc0,0x00,0x0b,0x08,0x00,0x01,
        0x00,0x01,0x01,0x01,0x11,0x00,0xff,0xc4,0x00,0x1f,0x00,0x00,
        0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
        0x09,0x0a,0x0b,0xff,0xc4,0x00,0xb5,0x10,0x00,0x02,0x01,0x03,
        0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7d,
        0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,
        0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,0x81,0x91,0xa1,0x08,
        0x23,0x42,0xb1,0xc1,0x15,0x52,0xd1,0xf0,0x24,0x33,0x62,0x72,
        0x82,0x09,0x0a,0x16,0x17,0x18,0x19,0x1a,0x25,0x26,0x27,0x28,
        0x29,0x2a,0x34,0x35,0x36,0x37,0x38,0x39,0x3a,0x43,0x44,0x45,
        0x46,0x47,0x48,0x49,0x4a,0x53,0x54,0x55,0x56,0x57,0x58,0x59,
        0x5a,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6a,0x73,0x74,0x75,
        0x76,0x77,0x78,0x79,0x7a,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8a,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9a,0xa2,0xa3,
        0xa4,0xa5,0xa6,0xa7,0xa8,0xa9,0xaa,0xb2,0xb3,0xb4,0xb5,0xb6,
        0xb7,0xb8,0xb9,0xba,0xc2,0xc3,0xc4,0xc5,0xc6,0xc7,0xc8,0xc9,
        0xca,0xd2,0xd3,0xd4,0xd5,0xd6,0xd7,0xd8,0xd9,0xda,0xe1,0xe2,
        0xe3,0xe4,0xe5,0xe6,0xe7,0xe8,0xe9,0xea,0xf1,0xf2,0xf3,0xf4,
        0xf5,0xf6,0xf7,0xf8,0xf9,0xfa,0xff,0xda,0x00,0x08,0x01,0x01,
        0x00,0x00,0x3f,0x00,0xfb,0xd2,0x8a,0x28,0x03,0xff,0xd9
    ])
    upload_headers = {
        "Authorization": f"Basic {creds}",
        "Content-Disposition": "attachment; filename=tmt-test.jpg",
        "Content-Type": "image/jpeg",
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=upload_headers, data=pixel, timeout=15)
    r.raise_for_status()
    media_id = r.json()["id"]
    requests.delete(f"{WP_URL}/wp-json/wp/v2/media/{media_id}?force=true", headers=WP_HDR)
    return f"Image uploaded & deleted (ID {media_id})"

def test_rank_math():
    r = requests.get(f"{WP_URL}/wp-json/rankmath/v1/", headers=WP_HDR, timeout=10)
    if r.ok:
        return "REST API is ON"
    else:
        raise Exception(f"HTTP {r.status_code} — Enable: WP Admin → Rank Math → General Settings → REST API → ON")

def test_sitemap():
    r = requests.get(f"{WP_URL}/sitemap.xml", timeout=10)
    if r.status_code == 200:
        return f"OK ({len(r.content):,} bytes)"
    raise Exception(f"HTTP {r.status_code} — Run wp_setup.py first")


# ─── Anthropic ────────────────────────────────────────────────────────────────

def test_anthropic():
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say OK"}]
    )
    return f"claude-haiku responded: '{msg.content[0].text.strip()}'"


# ─── Pexels ───────────────────────────────────────────────────────────────────

def test_pexels():
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": "5G India technology", "per_page": 1},
        timeout=10
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise Exception("No photos returned")
    return f"Photo found: {photos[0]['url'][:60]}..."


# ─── fal.ai ───────────────────────────────────────────────────────────────────

def test_fal():
    import fal_client
    os.environ["FAL_KEY"] = FAL_KEY
    try:
        result = fal_client.run(
            "fal-ai/flux/schnell",
            arguments={"prompt": "A modern telecom tower", "image_size": "landscape_16_9", "num_images": 1, "num_inference_steps": 1}
        )
        images = result.get("images", [])
        if not images:
            raise Exception("No images in response")
        return f"Image generated OK"
    except Exception as e:
        err_str = str(e)
        if "balance" in err_str.lower() or "locked" in err_str.lower():
            raise Exception("No credits — top up at fal.ai/dashboard/billing (fallback to Pexels is active)")
        raise


# ─── RSS Feeds ────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    "https://economictimes.indiatimes.com/tech/telecom/rssfeeds/13357270.cms",
    "https://telecomtalk.info/feed/",
    "https://www.medianama.com/feed/",
    "https://entrackr.com/feed/",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/feed/",
]

def test_rss():
    import feedparser
    ok_count = 0
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                ok_count += 1
        except Exception:
            pass
    if ok_count == 0:
        raise Exception("All RSS feeds failed")
    return f"{ok_count}/{len(RSS_FEEDS)} feeds reachable"


# ─── Site Speed ───────────────────────────────────────────────────────────────

def test_speed():
    start = time.time()
    r = requests.get(WP_URL, timeout=30)
    elapsed = time.time() - start
    r.raise_for_status()
    return f"{elapsed:.2f}s response time ({'⚡ fast' if elapsed < 2.5 else '🐌 slow — optimise LiteSpeed'})"


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  The Mobile Times — Connection Test Suite")
    print("=" * 60)

    print("\n── WordPress ──────────────────────────────────────────")
    check("WP Auth",         test_wp)
    check("WP Create Post",  test_wp_post)
    check("WP Upload Media", test_wp_media)
    check("Rank Math API",   test_rank_math)
    check("Sitemap",         test_sitemap)

    print("\n── AI & Images ────────────────────────────────────────")
    check("Anthropic Claude", test_anthropic)
    check("Pexels API",       test_pexels)
    check("fal.ai",           test_fal)

    print("\n── Content Sources ────────────────────────────────────")
    check("RSS Feeds", test_rss)

    print("\n── Performance ────────────────────────────────────────")
    check("Site Speed", test_speed)

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total  = len(results)
    print(f"\n{'=' * 60}")
    print(f"  Result: {passed}/{total} checks passed")

    if passed == total:
        print("  ✅ All systems GO — safe to run mobiletimes_agent.py")
    else:
        print("  ⚠️  Fix the ❌ items above before running the agent")
        failed = [name for name, ok, _ in results if not ok]
        for f in failed:
            print(f"     - {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
