# TMT System Analysis — Full Audit
**Date:** May 28, 2026 (updated May 28, 2026)  
**Scope:** Automation system + WordPress installation  
**Status:** Production live. Phase 1 complete. Weekly Insights live. Google News application pending.

---

## 1. Architecture Overview

```
GitHub Repository
├── Automation/                     ← Python automation scripts
│   ├── mobiletimes_agent.py        ← Core: ALL publishing logic (news + blogs + manual)
│   ├── breaking_monitor.py         ← Breaking news only (separate scoring + format)
│   ├── social_poster.py            ← Social media (code ready, Phase 2)
│   ├── gsc_optimizer.py            ← Monthly SEO meta rewrites (inactive)
│   ├── tmt-admin-api/              ← Custom WP plugin (must stay deployed)
│   ├── assets/Circle_Logo.png      ← Watermark logo
│   ├── llms.txt                    ← AI citation context file
│   └── requirements.txt
│
└── .github/workflows/
    ├── daily-posts.yml             ← 4 crons/day: 08/12/16/20 IST (--slot 1-4)
    ├── weekly-insights.yml         ← Mon/Wed/Fri 08:30 IST (--blog <subcategory>)
    ├── breaking-news.yml           ← 16×/day (every 1.5h, separate script)
    ├── manual-story.yml            ← On-demand via GitHub UI (--single or --url)
    └── monthly-seo.yml             ← 1st of month (currently skipped — no GSC creds)

WordPress (Hostinger LiteSpeed, local copy at public_html/ — NOT in git)
├── Theme: Foxiz v?.?.? (premium news/magazine)
├── Active Plugins:
│   ├── seo-by-rank-math            ← SEO meta, schema, sitemap
│   ├── wp-super-cache              ← Page caching (NOT LiteSpeed Cache)
│   ├── autoptimize                 ← CSS/JS minification
│   ├── light-views-counter         ← View counts seeded by automation
│   ├── tmt-admin-api               ← Custom plugin: REST API for automation
│   ├── elementor                   ← Page builder (static pages only)
│   ├── foxiz-core                  ← Theme functionality plugin
│   ├── contact-form-7              ← Contact form
│   ├── mailchimp-for-wp            ← Newsletter signup (Phase 2)
│   ├── breadcrumb-navxt            ← Breadcrumbs
│   ├── custom-post-type-ui         ← Custom post type management
│   ├── easy-post-submission        ← Public post submissions ⚠️
│   ├── themeruby-multi-authors     ← Multi-author (unused, one author)
│   ├── local-fonts-uploader        ← Local font hosting (good)
│   └── 3d-flipbook-dflip-lite      ← Unknown purpose ⚠️
└── mu-plugins/ (Hostinger-managed):
    ├── hostinger-auto-updates.php  ← Disables WP auto-updates (Hostinger manages)
    └── hostinger-preview-domain.php
```

---

## 2. Data Flow — Full Publish Cycle

```
GitHub Actions trigger (cron or manual)
  ↓
Python script boots on fresh Ubuntu runner (~30s install)
  ↓
1. Load WP state (seen_urls, pexels_ids, daily counter) via tmt/v1/state/get
2. Fetch stories: News API → RSS feeds (35+), merge + dedup by title hash
3. Semantic dedup: Claude Haiku compares candidates vs last 100 WP post titles
4. Story selection: Claude Haiku routes best story to category + template
5. Content generation: Claude Sonnet writes article using one of 10 templates
   (6 news + 4 blog)
6. QA: reject placeholder-unfilled articles, reject <500 words, fix years
7. Post-processing: inject internal links, authority links, related links, TOC
8. Image pipeline: OG scrape → Unsplash → Pexels → fal.ai → text fallback
   → resize 1200×628 → add watermark → upload to WP media
9. Publish: WP REST API /wp/v2/posts
10. SEO meta: tmt/v1/update-meta → Rank Math (title, desc, focus_keyword, OG)
11. Views seed: tmt/v1/views/seed → Light Views Counter (300–2000 random)
12. Daily counter: tmt/v1/state/set auto_posts_{YYYY-MM-DD} (automated only)
13. Cache flush: tmt/v1/cache/flush → WP Super Cache + Autoptimize + Rank Math
14. IndexNow ping → Bing/Yandex instant indexing
15. Google sitemap ping
16. Social posting: Telegram + Twitter + LinkedIn + Facebook (if credentials set)
17. State save: update seen_urls, pexels_ids in WP options
```

---

## 3. External Service Map

| Service | Purpose | Status | Cost |
|---------|---------|--------|------|
| Claude Sonnet 4.6 | Article writing | ✅ Active | ~₹400/month |
| Claude Haiku 4.5 | Story routing, dedup, meta | ✅ Active | ~₹100/month |
| News API (newsapi.org) | Primary story source, 150k+ sources | ✅ Active | Free (100/day) |
| 35+ RSS feeds | Secondary story source | ✅ Active | Free |
| Unsplash API | Primary stock images | ✅ Active | Free |
| Pexels API | Fallback stock images | ✅ Active | Free |
| fal.ai (flux/schnell) | AI image generation (blog posts) | ⚠️ Needs $5 top-up | ~₹40/month |
| IndexNow | Instant Bing/Yandex indexing | ⚠️ Key may be empty | Free |
| Google Search Console | Monthly meta optimization | ❌ Not configured | Free |
| Telegram Bot | Social channel | Phase 2 | Free |
| Twitter/X API | Social posts | Phase 2 | Free (1500/month) |
| LinkedIn Posts API | Social posts | Phase 2 | Free (token expires 60 days) |
| Facebook Graph API | Social posts | Phase 2 | Free |
| GitHub Actions | Cron + compute | ✅ Active | Free |
| Hostinger LiteSpeed | WordPress hosting | ✅ Active | ~₹500/month |

---

## 4. WordPress State Keys (WP Options)

All stored as `tmt_state_{name}` in `wp_options` (autoload=false):

| Key | Content | TTL |
|-----|---------|-----|
| `tmt_state_seen_urls` | `{"urls": [...2000 max]}` — story URLs published | Forever |
| `tmt_state_pexels_used_ids` | `{"ids": [...1000 max]}` — used Pexels photo IDs | Forever |
| `tmt_state_breaking_seen` | `{"published": [...500 hashes], "daily": {"YYYY-MM-DD": N}}` | Forever |
| `tmt_state_auto_posts_{YYYY-MM-DD}` | Integer — combined daily post count | Self-expires (keyed by date) |

---

## 5. Issues Found

### SECURITY (Action Required)

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| S1 | **CRITICAL: Live tmt-admin-api.php on server still has old hardcoded fallback secret (`TMT2026xK9mSEO`)** — the updated version with empty fallback is only in the local Automation/ folder, NOT yet deployed to WordPress | CRITICAL | Upload `Automation/tmt-admin-api/tmt-admin-api.php` to `wp-content/plugins/tmt-admin-api/` on the live server NOW. Then add `define('TMT_API_SECRET', 'your-key');` to wp-config.php on server. |
| S2 | `TMT_API_SECRET` not defined in wp-config.php (local copy confirmed — live server unknown) | HIGH | Add `define('TMT_API_SECRET', 'TMT_...your_strong_key...');` to live server wp-config.php |
| S3 | `easy-post-submission` plugin active — allows public post submissions with no visible moderation | HIGH | Review moderation settings or deactivate if unused |
| S4 | `xmlrpc.php` accessible at site root | MEDIUM | Block in .htaccess: `<Files "xmlrpc.php"> deny from all </Files>` |
| S5 | `readme.html` at site root exposes WordPress version | LOW | Delete from server |
| S6 | `tmt-admin-api` routes registered with `permission_callback: __return_true` — auth done in handler | LOW | Fine as-is; auth in handler is correct PHP pattern for REST |

### AUTOMATION (Functional Issues)

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| A1 | ~~Weekly blog topics 7–14 never used~~ | **FIXED** | `WEEKLY_BLOG_TOPICS` removed entirely. All 5 daily slots are now news posts. Weekly blogs are a separate dynamic system (Mon/Wed/Fri, AI-picked topics). |
| A2 | **gsc_optimizer.py disabled** | MEDIUM | GSC credentials not configured. Monthly SEO workflow silently skips. Opportunity cost: no meta rewriting happening. |
| A3 | **fal.ai quota likely depleted** | MEDIUM | Blog posts (Slot 5) fall back to Pexels if fal.ai fails. No error visible to user. |
| A4 | **IndexNow key may be empty** | MEDIUM | `INDEXNOW_KEY = ""` if secret not set. Only Google ping fires. Bing/Yandex miss instant indexing. |
| A5 | **Source OG image copyright risk** | HIGH | `extract_source_image()` downloads images from source articles and republishes them with TMT watermark. This is copyright infringement. Should only use Unsplash/Pexels/AI-generated images. |
| A6 | **`schedule` package imported but never used** | LOW | Both scripts import `schedule` but run `--once` via GitHub Actions. Remove import + dependency. |
| A7 | **No retry logic on API calls** | LOW | Single `requests.post()` with timeout. If WP is briefly unavailable, publish fails silently. |
| A8 | **Breaking news runs 16×/day not 30min** | LOW (docs only) | README says "every 30 minutes" but GitHub Actions cron runs 16 times/day. Update docs. |
| A9 | **`fix_existing_posts.py` and `seo_updater.py` deleted but .pyc files in pycache** | LOW | .gitignore excludes pycache, so they're local-only. No action needed. |
| A10 | **Post author hardcoded to default WP user** | LOW | WP REST API uses the authenticated user's ID automatically. Sanjay must be the WP_USER in secrets. |

### WORDPRESS PERFORMANCE

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| W1 | ~~WP Super Cache instead of LiteSpeed Cache~~ | RESOLVED | Foxiz theme recommends WP Super Cache. Keep as-is. |
| W2 | **Elementor loading on all pages** | MEDIUM | Elementor adds ~380KB JS/CSS. Only needed for static pages (About, Contact). Should be disabled on post/category pages if possible. |
| W3 | **autoptimize + WP Super Cache** | LOW | Two overlapping optimization layers. LiteSpeed Cache would handle both. |
| W4 | **No WebP image generation** | MEDIUM | All images saved as JPEG quality=90. WebP is 25–34% smaller. LiteSpeed Cache auto-converts; WP Super Cache does not. |
| W5 | **Images missing width/height attributes** | LOW | Automation publishes `<img>` without explicit dimensions — causes CLS (layout shift). |
| W6 | **3d-flipbook-dflip-lite plugin** | LOW | Unknown purpose for a news site. Loads JS on page. Audit if needed. |

### CONTENT/SEO RISKS

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| C1 | **24 categories for a new site** | MEDIUM | Many categories will have thin content for months. Google's helpful content system is site-wide — many thin category pages can suppress ranking of strong pages. |
| C2 | **Expert quotes are AI-generated** | MEDIUM | Templates include `"[Expert quote]" — Industry Analyst`. These quotes are fabricated. Risk of E-E-A-T penalty when site is reviewed. |
| C3 | **FAQ answers in content are AI-generated** | LOW | FAQPage schema from real AI-generated answers is fine, but the content must be accurate. |
| C4 | **No internal linking to specific posts** | LOW | `inject_internal_links()` links to categories, not specific posts. `inject_related_links()` uses recent posts but has no topical relevance filter. |
| C5 | **Stat claims are hallucinated** | HIGH | Articles include specific numbers and market data that Claude generates from context. These are NOT verified. Risk: factual errors, potential legal issues. |

---

## 6. What Is Working Well

- ✅ **WP state API** — clean persistent storage, no file commits needed
- ✅ **Dual dedup** (word overlap + semantic) — prevents obvious content repetition  
- ✅ **Source authority scoring** — routes to higher-quality stories
- ✅ **10 article templates** — 6 news + 4 blog, good content variety
- ✅ **Dynamic blog topics** — AI picks blog topic fresh from current news each run (Mon/Wed/Fri), not from a static hardcoded list
- ✅ **Weekly blogs outside daily limit** — 3 extra posts/week don't interfere with daily news cap
- ✅ **Robust image fallback chain** — never fails to produce an image
- ✅ **Post-publish pipeline complete** — views seed, cache flush, IndexNow, social, state save all in sequence
- ✅ **Combined daily limit (5/day)** — prevents overpublishing, manual posts exempt
- ✅ **Email failure alerts** — on all 3 scheduled workflows
- ✅ **tmt-api-logs** — detailed server-side logs for debugging
- ✅ **llms.txt deployed** — AI citation optimization in place
- ✅ **TMT article CSS in plugin** — consistent visual style regardless of theme updates
- ✅ **Content QA hard stops** — placeholder detection, minimum word count

---

## 7. Priority Fix List

### Tier 1 — Do Soon (high impact, low risk)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| 1 | **Deploy updated tmt-admin-api.php to live server** (security fix + views fix) | Eliminates hardcoded secret fallback, makes views errors visible | 5min upload |
| 2 | **Fix WEEKLY_BLOG_TOPICS to use all 15 topics** (rotate by post count, not weekday) | Content diversity | 10min code |
| 3 | **Block source OG image use as featured image** — use only Unsplash/Pexels/fal.ai | Legal risk elimination | 15min code |
| 4 | **Set up GSC credentials** so monthly SEO optimizer activates | SEO improvements monthly | 30min setup |
| 5 | **Top up fal.ai** ($5) | AI-generated images for blog posts | 5min |

### Tier 2 — Phase 2 (growth features)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| 6 | **Social media credentials** (Telegram first, then Twitter) | Distribution, audience growth | Phase 2 |
| 7 | **Audit and reduce active plugins** (remove 3d-flipbook, easy-post-submission, themeruby-multi-authors if unused) | Performance, security | 30min |
| 8 | **Block xmlrpc.php in .htaccess** | Security | 5min |
| 9 | **Remove readme.html** from server root | Security (minor) | 1min |
| 10 | **Disable Elementor on post/category pages** or replace with Foxiz built-in page builder | Performance | 1hr |

### Tier 3 — Long-term (scale improvements)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| 11 | **Plan comparison content** — auto-generate "Jio vs Airtel plan" posts | Traffic (highest-volume queries) | Phase 3 |
| 12 | **City-level 5G tracker** — "Is 5G available in [City]?" pages | Local search traffic | Phase 3 |
| 13 | **Google News approval follow-up** | 10–50× traffic potential | Already applied |
| 14 | **Add width/height to images** in automation-generated HTML | CLS improvement | Medium |
| 15 | **Expert quote attribution** improvement — source real quotes from public statements | E-E-A-T | Complex |

---

## 8. Scaling Projection

| Phase | Posts | Monthly Content | DB Size | Expected Impact |
|-------|-------|----------------|---------|-----------------|
| Now | 4 news/day + 3 blogs/week | ~135 posts/month | Small | 1–3k visitors/month |
| Phase 2 (social live) | 4 news/day + 3 blogs/week | ~135 posts/month | Medium | 3–8k visitors/month |
| Phase 3 (comparison engine) | same + 50 comparison pages | ~185/month | Medium | 8–20k/month |
| After Google News | 4 news/day + 3 blogs/week | ~135 posts/month | Medium | 15–50k/month (trending story = 5k in a day) |

**Bottleneck:** Google News approval. Everything else is secondary.

---

## 9. Key Files Reference

| File | Location | Purpose |
|------|----------|---------|
| `mobiletimes_agent.py` | Automation/ | Core: 5 daily posts |
| `breaking_monitor.py` | Automation/ | Breaking news, runs 16×/day |
| `social_poster.py` | Automation/ | Social (Phase 2, code ready) |
| `gsc_optimizer.py` | Automation/ | Monthly SEO meta rewrites |
| `tmt-admin-api.php` | Automation/tmt-admin-api/ | Custom WP plugin — MUST stay active |
| `assets/Circle_Logo.png` | Automation/assets/ | Watermark applied to all images |
| `llms.txt` | Automation/ + WP root | AI citation file |
| `.env` | Automation/ | Local dev credentials (not in git) |
| `requirements.txt` | Automation/ | Python packages |
| `wp-config.php` | public_html/ | WP config — local only, NOT in git |
| `tmt-api-logs/` | wp-content/ | Server-side API logs (daily) |

---

## 10. Environment Variables — Complete Reference

| Variable | Required By | Status |
|----------|------------|--------|
| `WP_URL` | All scripts | ✅ Set |
| `WP_USER` | All scripts | ✅ Set |
| `WP_APP_PASS` | All scripts | ✅ Set |
| `ANTHROPIC_API_KEY` | All scripts | ✅ Set |
| `TMT_SECRET` | All scripts | ✅ Set |
| `PEXELS_API_KEY` | Image pipeline | ✅ Set |
| `UNSPLASH_ACCESS_KEY` | Image pipeline (primary) | ✅ Set |
| `FAL_API_KEY` | Blog post images | ⚠️ Set but quota depleted |
| `NEWS_API_KEY` | Story fetching | ✅ Set |
| `INDEXNOW_KEY` | IndexNow ping | ⚠️ May be empty |
| `ALERT_EMAIL_PASS` | Failure emails | ✅ Set |
| `GSC_PROPERTY` | gsc_optimizer.py | ❌ Not set |
| `GSC_CREDENTIALS` | gsc_optimizer.py | ❌ Not set |
| `TELEGRAM_BOT_TOKEN` | social_poster.py | Phase 2 |
| `TELEGRAM_CHANNEL` | social_poster.py | Phase 2 |
| `TWITTER_API_KEY` | social_poster.py | Phase 2 |
| `TWITTER_API_SECRET` | social_poster.py | Phase 2 |
| `TWITTER_ACCESS_TOKEN` | social_poster.py | Phase 2 |
| `TWITTER_ACCESS_SECRET` | social_poster.py | Phase 2 |
| `LINKEDIN_ACCESS_TOKEN` | social_poster.py | Phase 2 (expires 60 days) |
| `LINKEDIN_ORG_ID` | social_poster.py | Phase 2 |
| `META_ACCESS_TOKEN` | social_poster.py | Phase 2 |
| `META_PAGE_ID` | social_poster.py | Phase 2 |
| `TMT_API_SECRET` | wp-config.php on server | ✅ Must be set on live server |
