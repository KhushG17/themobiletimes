# TMT System Analysis — Full Audit
**Date:** May 28, 2026 (updated May 29, 2026)  
**Scope:** Automation system + WordPress installation  
**Status:** Production live. Phase 1 complete. Weekly Insights live. Google News application pending. Repo public. All major reliability issues resolved.

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
| `tmt_state_unsplash_used_ids` | `{"ids": [...1000 max]}` — used Unsplash photo IDs | Forever |
| `tmt_state_auto_posts_{YYYY-MM-DD}` | Integer — combined daily post count | Self-expires (keyed by date) |

---

## 5. Issues Found

### SECURITY

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| S1 | ~~tmt-admin-api.php old version on server~~ | CRITICAL | **FIXED** — deployed, TMT_API_SECRET set in wp-config.php as `TMT@2026#SecureKey_MobileTimes` |
| S2 | ~~TMT_API_SECRET not defined~~ | HIGH | **FIXED** — set in wp-config.php + GitHub Secret |
| S3 | `easy-post-submission` plugin active | HIGH | Review moderation settings or deactivate if unused |
| S4 | `xmlrpc.php` accessible at site root | MEDIUM | Block in .htaccess: `<Files "xmlrpc.php"> deny from all </Files>` |
| S5 | `readme.html` at root exposes WP version | LOW | Delete from server |

### AUTOMATION

| # | Issue | Status |
|---|-------|--------|
| A1 | ~~Static blog topics~~ | **FIXED** — dynamic AI-picked topics (Mon/Wed/Fri weekly blogs) |
| A2 | ~~No retry on API calls~~ | **FIXED** — 3 retries with backoff on all state, meta, views, counter calls |
| A3 | ~~Daily limit not enforced on API failure~~ | **FIXED** — fail-safe defaults (returns limit on error, not 0) |
| A4 | ~~Same story published multiple times~~ | **FIXED** — full cross-script dedup (word-overlap against all recent WP posts) |
| A5 | ~~No pre-flight checks before Claude~~ | **FIXED** — WP health + App Password auth checked before every Sonnet call |
| A6 | ~~Inconsistent post-publish pipeline~~ | **FIXED** — all 6 modes have identical pipeline |
| A7 | ~~Data loss in save_seen_urls / save_pexels_id~~ | **FIXED** — returns None on failure, saves only if load succeeded |
| A8 | ~~Unsplash dedup only in-memory~~ | **FIXED** — persisted to WP state (unsplash_used_ids) across runs |
| A9 | ~~Source images low resolution~~ | **FIXED** — min 800×450px check, quality 92, better headers |
| A10 | ~~Category diversity (only Jio/Airtel)~~ | **FIXED** — COVERAGE_AREAS + already_covered tracking, smart AI diversity |
| A11 | ~~10 posts in one day~~ | **FIXED** — MAX_BREAKING_PER_DAY=1, threshold=65, fail-safe limits |
| A12 | ~~Views not seeding~~ | **FIXED** — 3 retries, PHP error checking, all 47 posts seeded |
| A13 | ~~Only 6 templates~~ | **FIXED** — 10 templates (+ Explainer, Policy Brief, Market Numbers, Industry Reaction) |
| A14 | **gsc_optimizer.py disabled** | OPEN — needs GSC_CREDENTIALS + GSC_PROPERTY secrets |
| A15 | **fal.ai quota depleted** | OPEN — needs $5 top-up at fal.ai/dashboard/billing |
| A16 | **DALL-E 3 inactive** | OPEN (by design) — activate when OpenAI key funded |
| A17 | GitHub Actions minute limit | **RESOLVED** — repo made public, unlimited minutes |

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

### Remaining Action Items (code is done — server/setup needed)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| 1 | **Top up fal.ai** ($5 at fal.ai/dashboard/billing) | Blog post AI images | 5min |
| 2 | **Set up GSC credentials** — enables monthly SEO meta optimizer | Monthly CTR improvements | 30min |
| 3 | **OpenAI API key** — fund account, add key to GitHub Secrets `OPENAI_API_KEY`, say "activate" | Better editorial images | Setup + tell me |
| 4 | **Block xmlrpc.php in .htaccess** | Security | 5min |
| 5 | **Social media credentials** (Telegram first) | Distribution, audience growth | Phase 2 |

### Phase 2 — Growth Features

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| 6 | Twitter, LinkedIn, Facebook social posting | Distribution | Phase 2 |
| 7 | Mailchimp newsletter — Monday digest | Audience retention | Phase 2 |
| 8 | Plan comparison content engine — "Jio vs Airtel" auto-generation | Highest-traffic queries | Phase 3 |
| 9 | City-level 5G tracker — "Is 5G available in [City]?" | Local search traffic | Phase 3 |
| 10 | Google News approval — already applied, waiting | 10–50× traffic potential | Waiting |

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
