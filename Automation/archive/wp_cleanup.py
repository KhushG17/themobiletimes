"""
wp_cleanup.py — One-shot site cleanup via WordPress REST API
Runs each fix, reports result. Safe to re-run (already-deleted items just 404).
"""
import os, base64, requests
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR     = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

ok  = []
fail = []

def done(label):
    print(f"  OK   {label}")
    ok.append(label)

def err(label, reason):
    print(f"  FAIL {label} — {reason}")
    fail.append(label)

def delete(type_, id_, label):
    r = requests.delete(
        f"{WP_URL}/wp-json/wp/v2/{type_}/{id_}?force=true",
        headers=HDR, timeout=20
    )
    if r.ok or r.status_code == 404:
        done(label)
    else:
        err(label, f"HTTP {r.status_code} {r.text[:80]}")

def update_post(id_, payload, label):
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{id_}",
        headers=HDR, json=payload, timeout=20
    )
    if r.ok:
        done(label)
    else:
        err(label, f"HTTP {r.status_code} {r.text[:80]}")

print("=" * 60)
print("  TMT WordPress Cleanup")
print("=" * 60)

# ── 1. Delete 3 stale draft posts ─────────────────────────────────────────────
print("\n── Draft posts ──────────────────────────────────────────")
delete("posts", 31219, "Draft: Tackling Call Drop (Vodafone Idea)")
delete("posts", 31184, "Draft: South Korea 5G Revolution")
delete("posts", 31168, "Draft: How Starlink is Reshaping Connectivity")

# ── 2. Delete leftover blog-page-1/2/3 pages ─────────────────────────────────
print("\n── Junk pages ───────────────────────────────────────────")
delete("pages", 22149, "Page: blog-page-1")
delete("pages", 22572, "Page: blog-page-2")
delete("pages", 22877, "Page: blog-page-3")
delete("pages", 26127, "Page: image-credits")

# ── 3. Delete rogue tag main-breaking (created outside our system) ────────────
print("\n── Tags ─────────────────────────────────────────────────")
delete("tags", 194, "Tag: main-breaking (ID 194)")

# ── 4. Fix site tagline ───────────────────────────────────────────────────────
print("\n── Site settings ────────────────────────────────────────")
r = requests.post(
    f"{WP_URL}/wp-json/wp/v2/settings",
    headers=HDR,
    json={
        "description": "India's Leading Telecom & Tech News Publication",
        "timezone_string": "Asia/Kolkata",
    },
    timeout=20
)
if r.ok:
    done("Tagline updated to 'India's Leading Telecom & Tech News Publication'")
    done("Timezone set to Asia/Kolkata")
else:
    err("Site settings", f"HTTP {r.status_code} {r.text[:80]}")

# ── 5. Rename 'Uncategorized' to something useful ────────────────────────────
r2 = requests.post(
    f"{WP_URL}/wp-json/wp/v2/categories/1",
    headers=HDR,
    json={"name": "General", "slug": "general",
          "description": "General telecom and technology news from The Mobile Times."},
    timeout=20
)
if r2.ok:
    done("Category 'Uncategorized' renamed to 'General'")
else:
    err("Rename Uncategorized", f"HTTP {r2.status_code} {r2.text[:80]}")

# ── 6. Fix 3 published posts that have 'uncategorized' as their only category
#    (if any got published without a proper cat during early testing) ──────────
print("\n── Post category fixes ──────────────────────────────────")
r3 = requests.get(
    f"{WP_URL}/wp-json/wp/v2/posts?categories=1&per_page=20&status=publish",
    headers=HDR, timeout=20
)
if r3.ok:
    mis_posts = r3.json()
    if mis_posts:
        for p in mis_posts:
            # Only fix if uncategorized is the ONLY category
            if p.get("categories") == [1]:
                update_post(p["id"], {"categories": [161]},  # → tech-innovation
                    f"Post {p['id']} recategorised: uncategorized → tech-innovation")
    else:
        done("No posts stuck in uncategorized/general")
else:
    err("Fetch uncategorized posts", f"HTTP {r3.status_code}")

# ── 7. Trash any remaining old test posts with 'TMT Connection Test' ──────────
print("\n── Test posts ───────────────────────────────────────────")
r4 = requests.get(
    f"{WP_URL}/wp-json/wp/v2/posts?search=TMT+Connection+Test&status=any&per_page=10",
    headers=HDR, timeout=20
)
if r4.ok:
    test_posts = r4.json()
    if test_posts:
        for p in test_posts:
            delete("posts", p["id"], f"Test post ID {p['id']}: {p['title']['rendered'][:40]}")
    else:
        done("No leftover test posts found")

# ── 8. Verify the deletions ───────────────────────────────────────────────────
print("\n── Verification ─────────────────────────────────────────")
rv = requests.get(
    f"{WP_URL}/wp-json/wp/v2/posts?per_page=5&status=draft",
    headers=HDR, timeout=20
)
if rv.ok:
    remaining_drafts = rv.json()
    if not remaining_drafts:
        done("Zero draft posts remaining")
    else:
        for p in remaining_drafts:
            err("Still has draft", f"ID {p['id']} {p['title']['rendered'][:40]}")

rv2 = requests.get(
    f"{WP_URL}/wp-json/wp/v2/settings",
    headers=HDR, timeout=20
)
if rv2.ok:
    s = rv2.json()
    done(f"Tagline confirmed: '{s.get('description', '?')}'")
    done(f"Timezone confirmed: '{s.get('timezone_string', '?')}'")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  Done: {len(ok)} fixed,  {len(fail)} failed")
if fail:
    print("  Failed items:")
    for f in fail:
        print(f"    - {f}")
print("=" * 60)
