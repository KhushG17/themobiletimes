# The Mobile Times — Automation System

**Site:** themobiletimes.com  
**Owner:** Sanjay Goyal, Editor-in-Chief  
**Goal:** 15,000–50,000 monthly visitors by December 2026  
**Budget:** ₹2,000/month all-in  
**Last updated:** May 29, 2026 — Phase 1 live ✅ Applied to Google News ✅ Weekly Insights live ✅ Repo public ✅

---

## What This Does (Plain English)

This system runs themobiletimes.com automatically — no human needs to touch it day to day.

**Every single day, without you doing anything:**

- At 4 specific times (8am, 12pm, 4pm, 8pm IST), GitHub's free servers wake up, scan Indian telecom news from **35+ RSS feeds + News API** (150,000 sources), Claude AI picks the most relevant story intelligently — spreading across telecom, devices, cybersecurity, AI, OTT, policy, and more — writes a 500–750 word article using one of 10 article templates, finds a matching image (source article → Unsplash → Pexels → fallback), watermarks it with the TMT logo, and publishes it to WordPress.

- 3 times a week (Mon, Wed, Fri), a separate workflow publishes a long-form Insights blog post (900–1,000 words) with 2 body images. Claude AI reads the current week's news and picks the most timely topic. Monday = Industry Insights full week recap, Wednesday = Case Study on what people are researching, Friday = How-to Guide (e.g. "How to Port Your Number"). These are completely separate from the daily news posts and not counted in the daily limit.

- 16 times a day (roughly every 1.5 hours), a separate check scans for truly breaking news. If a high-scoring story is found and fewer than 5 total posts were already published today, it publishes immediately as a breaking news article.

- On the 1st of every month, it pulls Google Search Console data to find articles almost on page 1 but not getting clicks, then rewrites their meta descriptions to improve CTR. *(Currently disabled — needs GSC setup.)*

**When you want to post something specific:**  
Go to GitHub → Actions → "Post Manual Story" → type a topic or paste a URL → done in 3–5 minutes.

---

## How It Works — The Full Flow

### Daily News Posts (4 per day)

```
08:00 IST  →  Slot 1
12:00 IST  →  Slot 2
16:00 IST  →  Slot 3
20:00 IST  →  Slot 4
```

Each slot runs independently:

```
GitHub wakes up at scheduled time
  ↓
1.  Load state from WordPress (seen URLs, Pexels IDs, daily counter)
2.  Fetch stories: News API first → 35+ RSS feeds as supplement
3.  Remove stories already published (URL history + word overlap + semantic dedup)
4.  Claude Haiku: pick best story from ALL categories dynamically
  ↓
5.  Claude Sonnet: write news article (500–750 words)
      - 6 templates: Breaking / Analysis / Investor / Deep Dive / Product / Comparison
      - Auto-injects internal links to TMT category pages
      - Auto-injects 2 authority links (TRAI, GSMA, COAI, DOT)
      - Adds "Related Reading" block from recent TMT posts
      - 3 FAQ items at the bottom for Google "People Also Ask"
      - Auto-TOC for articles 800+ words with 3+ H2 sections
6.  Content QA — hard stops on:
      - Unfilled template placeholders
      - Articles under 500 words
      - Wrong years auto-corrected (2020–2025 → 2026)
7.  Image pipeline:
      Unsplash (primary) → Pexels (fallback) → fal.ai → text fallback
      → Resize to 1200×628 → Watermark (9% width, 80% opacity) → Upload to WP
      Featured image: clean hero, no watermark
      Body image:     watermarked, injected between sections
8.  Publish via WP REST API
9.  Save Rank Math SEO meta (title, description, focus keyword, OG tags)
10. Seed random view count (300–2000) via Light Views Counter
11. Increment combined daily counter in WP state
12. Flush WP Super Cache, Autoptimize, Rank Math sitemap
13. Ping IndexNow → instant Bing/Yandex indexing
14. Ping Google sitemap
15. Post to Telegram, Twitter, LinkedIn, Facebook (if credentials set — Phase 2)
16. Save story URL to dedup history
```

### Weekly Insights Blogs (3 per week — separate from daily limit)

```
Monday    08:30 IST  →  Industry Insights  (full week recap)
Wednesday 08:30 IST  →  Case Studies       (what users research)
Friday    08:30 IST  →  How-to Guides      (e.g. "How to Port Your Number")
```

```
GitHub wakes up on scheduled day
  ↓
1.  Fetch current news headlines from RSS + News API
2.  Claude Haiku reads the week's news and picks the most relevant topic
    for the subcategory — topic is always timely, never from a fixed list
3.  Claude Sonnet writes long-form blog post (900–1,000 words)
      - 4 blog templates: Opinion / India-vs-World / Editorial / Explainer
      - FAQs, expert quotes, deeper analysis than news posts
4.  2 body images (different visual themes) uploaded and injected
    giving a magazine-style layout throughout the article
5.  Publish, seed views, flush cache, IndexNow, social post
    ← does NOT increment the daily counter (separate system)
```

### Breaking News (16 checks/day, every ~90 min)

```
GitHub wakes up (16× per day)
  ↓
1. Check combined daily limit: if 5 or more posts published today → skip
2. Check breaking-specific cap: if 3 breaking posts already today → skip
3. Fetch stories: News API + 35 RSS feeds
4. Score each story 0–100 on India-telecom relevance
5. If best story scores ≥ 45:
     Claude Sonnet writes 600–750 word breaking article
     → Publish immediately (not sticky)
     → Seed views, increment daily counter
     → Cache flush, IndexNow ping
     → Social post
```

### Manual Posting

```
GitHub Actions → "Post Manual Story" → fill in topic or URL → runs in 3–5 min
```

Manual posts do NOT count toward the daily 5-post limit.

### Monthly SEO (1st of month)

```
1st of month → GitHub wakes up
  ↓
1. Pull last 28 days of Google Search Console data
2. Find posts with: impressions > 50, CTR < 4%, position 4–15
3. Fetch top search queries for each post
4. Claude Haiku rewrites meta descriptions using those exact queries
5. Push to Rank Math via tmt-admin-api
```

**Status: Currently disabled** — needs `GSC_CREDENTIALS` + `GSC_PROPERTY` secrets.

---

## Architecture

All publishing logic lives in `mobiletimes_agent.py`. The workflows are thin triggers that call the same script with different flags. Fix something once — it applies everywhere.

```
themobiletimes.com
        │
        ├── GitHub Actions (free, cloud, no PC needed)
        │       ├── daily-posts.yml      → 4 cron triggers/day (--slot 1/2/3/4)
        │       ├── weekly-insights.yml  → 3×/week Mon/Wed/Fri (--blog <subcategory>)
        │       ├── breaking-news.yml    → 16 triggers/day (separate script)
        │       ├── manual-story.yml     → on-demand (--single or --url)
        │       └── monthly-seo.yml      → 1st of month (separate script)
        │
        ├── Python Scripts (Automation/)
        │       ├── mobiletimes_agent.py   → ALL publishing logic lives here
        │       │                            --slot N  = daily news posts
        │       │                            --blog X  = weekly insights blogs
        │       │                            --single  = manual topic post
        │       │                            --url     = rewrite from source
        │       │                            --run-now = all 4 slots at once
        │       ├── breaking_monitor.py    → separate: urgency scoring + breaking posts
        │       ├── social_poster.py       → called by both scripts after each publish
        │       └── gsc_optimizer.py       → separate: monthly GSC meta rewrites
        │
        ├── External APIs (Active)
        │       ├── Claude Sonnet 4.6      → article writing (~₹290/month)
        │       ├── Claude Haiku 4.5       → story routing, dedup, topics, prompts (~₹45/month)
        │       ├── News API (newsapi.org) → 150,000+ sources, keyword queries (free)
        │       ├── 35+ RSS feeds          → balanced: telecom/devices/cyber/AI/OTT (free)
        │       ├── Unsplash               → primary stock images (commercial use, free)
        │       ├── Pexels                 → fallback stock images (royalty-free, free)
        │       ├── fal.ai (flux/schnell)  → blog post featured images (⚠️ needs $5 top-up)
        │       ├── DALL-E 3 (OpenAI)      → custom editorial images — INACTIVE (key slot ready)
        │       ├── IndexNow               → instant Bing/Yandex indexing
        │       └── Google Search Console  → monthly meta optimization (disabled)
        │
        └── WordPress (themobiletimes.com — Hostinger LiteSpeed)
                ├── Foxiz v2.7.6 theme        → premium news/magazine layout
                ├── Rank Math SEO             → receives SEO meta from scripts
                ├── WP Super Cache            → page caching (flushed after each publish)
                ├── Autoptimize               → CSS/JS minification
                ├── Light Views Counter       → view counts seeded by automation
                └── tmt-admin-api plugin      → the bridge between scripts and WordPress
```

---

## File Map

```
TMT/
│
├── Automation/
│   │
│   ├── ── CORE SCRIPTS ──────────────────────────────────────────────────────
│   │
│   ├── mobiletimes_agent.py
│   │     Main publishing engine. 4× daily news + 3× weekly blogs + on-demand.
│   │     35 balanced RSS feeds + News API → smart diversity selection → AI article → WP publish
│   │     10 news templates + 4 blog templates. Consistent post-publish pipeline in all modes.
│   │     Pre-flight: WP health + App Password auth checked before every Claude call.
│   │     CLI: --slot N | --run-now | --blog X | --single "topic" | --url "..." | --tip "..." | --test-post
│   │
│   ├── breaking_monitor.py
│   │     16× daily (every ~90 min). Scores stories 0–100.
│   │     Threshold ≥ 65. Max 1 breaking/day. Combined daily cap = 5.
│   │     Full dedup against ALL recent WP posts (not just breaking-specific hashes).
│   │     CLI: --once (single check — how GitHub Actions calls it)
│   │
│   ├── social_poster.py
│   │     Posts every published article to Telegram, Twitter, LinkedIn, Facebook.
│   │     Called after each publish. Silently skips if credentials not set.
│   │     STATUS: Code ready. Credentials not yet added. Phase 2.
│   │
│   ├── gsc_optimizer.py
│   │     Runs 1st of month. GSC data → Claude rewrites meta descriptions.
│   │     STATUS: Disabled (needs GSC_CREDENTIALS + GSC_PROPERTY secrets).
│   │
│   ├── ── ASSETS ───────────────────────────────────────────────────────────
│   │
│   ├── assets/Circle_Logo.png
│   │     TMT circular logo. Watermarked on all featured + body images.
│   │     9% of image width, 80% opacity, 18px padding from bottom-right corner.
│   │
│   ├── ── CONFIG ───────────────────────────────────────────────────────────
│   │
│   ├── requirements.txt
│   │     Python packages. Installed fresh on every GitHub Actions run.
│   │
│   ├── llms.txt
│   │     AI citation context file for ChatGPT, Perplexity, Claude, Gemini.
│   │     Also deployed live at: https://themobiletimes.com/llms.txt
│   │
│   ├── .env  (NOT in git — local dev only)
│   │     Local copy of all credentials for running scripts on your PC.
│   │
│   ├── ── WORDPRESS PLUGIN ─────────────────────────────────────────────────
│   │
│   └── tmt-admin-api/
│       └── tmt-admin-api.php
│             Custom WordPress plugin. MUST stay active at all times.
│             24 REST endpoints for the automation scripts.
│             ⚠️ Deploy to WP server after any changes to this file.
│
└── .github/
    └── workflows/
        ├── daily-posts.yml      → 4 crons: 02:30, 06:30, 10:30, 14:30 UTC (= 08/12/16/20 IST)
        ├── weekly-insights.yml  → Mon/Wed/Fri 03:00 UTC (= 08:30 IST)
        ├── breaking-news.yml    → 16 crons/day (00:00, 01:30, 03:00 ... every 90min)
        ├── manual-story.yml     → manual trigger (topic or URL input)
        └── monthly-seo.yml      → 03:00 UTC on 1st of month
```

---

## tmt-admin-api Plugin — Endpoint Reference

`tmt-admin-api/tmt-admin-api.php` must be **active on WordPress at all times.**

All endpoints are `POST /wp-json/tmt/v1/{path}` and require `"secret": TMT_SECRET` in the JSON body.

| Endpoint | What It Does |
|----------|-------------|
| `health` | System health check |
| `site/info` | WP version, PHP, active plugins, post counts |
| `post/create` | Create post/page with categories, tags, media, Rank Math meta |
| `post/update` | Update any post field |
| `post/get` | Fetch post with all meta |
| `post/list` | Query posts with pagination |
| `post/delete` | Delete to trash or permanently |
| `meta/update` | Set Rank Math SEO fields for any post or term |
| `meta/get` | Read meta fields |
| `media/upload` | Upload image (base64) to WP media library |
| `media/update` | Update media alt text / caption |
| `media/list` | List media attachments |
| `term/create` | Create category or tag |
| `term/update` | Rename / describe term |
| `term/delete` | Delete category or tag |
| `term/list` | List all terms for a taxonomy |
| `option/get` | Read a WordPress option |
| `option/set` | Write a WordPress option (protected: siteurl, home, blogname, admin_email) |
| `user/update` | Update user bio, name, social links |
| `user/list` | List all users with roles |
| `plugin/list` | List all installed plugins |
| `plugin/activate` | Activate a plugin |
| `plugin/deactivate` | Deactivate a plugin |
| `cache/flush` | Purge WP Super Cache + LiteSpeed + Autoptimize + Rank Math sitemap |
| `views/seed` | Set view count for a single post, or bulk-seed all posts |
| `state/get` | Read persistent state (stored as WP option) |
| `state/set` | Write persistent state (stored as WP option) |

**Logs:** Every API call is logged to `/wp-content/tmt-api-logs/tmt-api-YYYY-MM-DD.log`

---

## Daily Post Limit

The system enforces a combined limit of **5 automated posts per day** covering daily news + breaking news.

- `mobiletimes_agent.py` increments `auto_posts_YYYY-MM-DD` after each scheduled news publish (3 retries)
- `breaking_monitor.py` reads this counter before publishing; skips if ≥ 5
- Counter read is fail-safe: if WP state API is unreachable, assumes limit reached (prevents runaway publishing)
- With 4 daily slots, breaking news can fire at most 1 time per day
- **Weekly blogs (`--blog`) do NOT count — completely separate**
- **Manual modes (`--single`, `--url`) do NOT count**
- Breaking monitor hard cap: max 1 breaking post per day regardless of counter

## Image Pipeline

Every post goes through this chain (first success wins):

```
DALL-E 3 (INACTIVE — ready when OpenAI key is funded)
   ↓
Source article OG image (minimum 800×450px — rejects small/blurry)
   ↓
Unsplash (persistent dedup across runs via WP state)
   ↓
Pexels (persistent dedup across runs via WP state)
   ↓
fal.ai AI image (blog posts only — needs $5 top-up)
   ↓
Text fallback (always works)
```

To activate DALL-E 3: add OpenAI API key to GitHub Secret `OPENAI_API_KEY`, then say "activate DALL-E 3". Monthly cost with DALL-E 3: ~₹786 (within ₹2,000 budget).

---

## Manual Story Trigger

**From phone or any browser (GitHub UI):**
```
GitHub repo → Actions tab → "Post Manual Story" → Run workflow
  ↓
Fill in either:
  Topic  →  "Airtel hikes prepaid plans by 20% from June 1"
  OR
  URL    →  "https://telecomtalk.info/some-article"
  ↓
Publishes within 3–5 minutes to WordPress
```

**From PC (Automation/ folder):**
```bash
# Write and publish one article on a specific topic
python mobiletimes_agent.py --single "Airtel hikes prepaid plans by 20%"

# Rewrite a source article in TMT voice
python mobiletimes_agent.py --url "https://telecomtalk.info/some-article"

# Run a specific daily news slot now
python mobiletimes_agent.py --slot 2

# Run all 4 daily slots at once
python mobiletimes_agent.py --run-now

# Publish a weekly insights blog manually (AI picks the topic from current news)
python mobiletimes_agent.py --blog industry-insights
python mobiletimes_agent.py --blog case-studies
python mobiletimes_agent.py --blog how-to-guides

# Feed a manual tip into the next slot's story selection
python mobiletimes_agent.py --tip "Jio announces free 5G trial in Tier 2 cities"

# Generate 1 draft post without publishing (for previewing)
python mobiletimes_agent.py --test-post

# Single breaking-news scan
python breaking_monitor.py --once
```

---

## GitHub Secrets

Go to: `Repo → Settings → Secrets and variables → Actions → New repository secret`

| Secret | Value | Status |
|--------|-------|--------|
| `WP_URL` | `https://themobiletimes.com` | ✅ |
| `WP_USER` | WordPress username (must be admin) | ✅ |
| `WP_APP_PASS` | WordPress Application Password (with spaces) | ✅ |
| `ANTHROPIC_API_KEY` | Claude API key | ✅ |
| `PEXELS_API_KEY` | Pexels API key | ✅ |
| `FAL_API_KEY` | fal.ai key | ⚠️ Quota depleted — top up $5 at fal.ai/dashboard/billing |
| `NEWS_API_KEY` | newsapi.org key | ✅ |
| `TMT_SECRET` | `TMT@2026#SecureKey_MobileTimes` — must match `TMT_API_SECRET` in wp-config.php | ✅ |
| `UNSPLASH_ACCESS_KEY` | Unsplash API key | ✅ |
| `OPENAI_API_KEY` | OpenAI key for DALL-E 3 image generation — slot ready, activate when funded | ⏭ Ready |
| `INDEXNOW_KEY` | IndexNow submission key | ⚠️ Verify it's set (Rank Math can provide this) |
| `ALERT_EMAIL_PASS` | Gmail app password for failure alerts | ✅ |
| `GSC_PROPERTY` | `https://themobiletimes.com/` | ❌ Not set (disables monthly SEO) |
| `GSC_CREDENTIALS` | Google service account JSON (full contents) | ❌ Not set |
| `TELEGRAM_BOT_TOKEN` | From @BotFather | Phase 2 |
| `TELEGRAM_CHANNEL` | `@TheMobileTimesNews` | Phase 2 |
| `TWITTER_API_KEY` | Twitter developer app key | Phase 2 |
| `TWITTER_API_SECRET` | Twitter developer app secret | Phase 2 |
| `TWITTER_ACCESS_TOKEN` | Twitter account access token | Phase 2 |
| `TWITTER_ACCESS_SECRET` | Twitter account access token secret | Phase 2 |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn OAuth token (⚠️ expires every 60 days) | Phase 2 |
| `LINKEDIN_ORG_ID` | LinkedIn company page numeric ID | Phase 2 |
| `META_ACCESS_TOKEN` | Facebook page access token | Phase 2 |
| `META_PAGE_ID` | Facebook page numeric ID | Phase 2 |

---

## WordPress Setup Requirements

For the automation to work, the live WordPress server must have:

**1. tmt-admin-api plugin active**  
Upload `Automation/tmt-admin-api/tmt-admin-api.php` to `/wp-content/plugins/tmt-admin-api/` and activate.

**2. TMT_API_SECRET in wp-config.php**  
```php
define('TMT_API_SECRET', 'your-strong-secret-here');
```
This must match the `TMT_SECRET` GitHub Secret exactly.

**3. Application Passwords enabled**  
The tmt-admin-api plugin force-enables this on WordPress. Hostinger Tools plugin, if active, would block it — keep it deactivated.

**4. Light Views Counter plugin active**  
Required for `views/seed` endpoint to work.

---

## Article Templates

**News Posts (6 templates — one chosen per story):**

| Template | Best For | Key Feature |
|----------|---------|-------------|
| A — Breaking | Urgent news, launches, policy announcements | Highlights box first, fast-paced |
| B — Analysis | Market data, regulatory, trends | Data box, expert quote, deep context |
| C — Investor | Funding, M&A, market share | Numbers-heavy, financial framing |
| D — Deep Dive | Long-form trends, tech explainers | TOC, numbered sections |
| E — Product | Device launches, app releases | Specs box, verdict callout |
| F — Comparison | Plan vs plan, carrier vs carrier | Full HTML comparison table |

**Blog Posts / Insights (4 templates — one chosen per topic):**

| Template | Style |
|----------|-------|
| A — Opinion | TMT takes a position, builds argument, dismantles counterargument |
| B — India vs World | Benchmarks India against global peers with data |
| C — Editorial | Sharp opinion, The Mobile Times verdict |
| D — Explainer | Plain English guide for complex topics |

---

## Content Strategy

### What Drives Traffic

| Type | Why It Works |
|------|-------------|
| Plan comparisons | Huge search volume — people deciding what to buy, evergreen |
| Breaking news | Google News spike, social sharing, immediate traffic |
| Lists & how-to | Long-tail keywords, voice search, featured snippets |
| Device launches | Launch traffic spike + comparison intent |
| Policy explainers | Low competition, high trust signal from TRAI/DOT coverage |

### 3 Best Untapped Content Gaps

1. **TRAI consumer rights in plain English** — nobody covers this clearly. Low competition, high trust signal.
2. **City-level 5G coverage tracker** — "Is 5G available in Jaipur 2026?" — high local intent, nobody maintains it.
3. **OTT + telecom bundle master guide** — which Jio plan includes which streaming service? Always changing, always searched.

---

## Roadmap

### Phase 1 — Foundation ✅ COMPLETE (May 2026)

- [x] 5 GitHub Actions crons (one per slot)
- [x] Breaking news monitor (16×/day, combined daily limit)
- [x] Dynamic AI-powered category selection per story
- [x] 6 news templates + 4 blog templates
- [x] Dual dedup: word overlap + Claude Haiku semantic
- [x] Content QA hard stops (placeholders, word count, year fixes)
- [x] Humanization rules (30+ banned AI phrases, em dash ban, sentence variety)
- [x] Full image pipeline (Unsplash → Pexels → fal.ai → fallback)
- [x] Image SEO (alt text, title, 1200×628 crop, watermark)
- [x] Rank Math SEO meta on every post (title, description, focus keyword, OG)
- [x] Light Views Counter seeded on every post (300–2000 random views)
- [x] WP state API (persistent state across ephemeral GitHub Actions runners)
- [x] Cache flush after every publish
- [x] IndexNow instant indexing
- [x] Auto-TOC injection for long articles
- [x] Body image injection between article sections
- [x] Related Reading block from recent posts
- [x] Authority links (TRAI, GSMA, COAI) auto-injected
- [x] Internal category links auto-injected
- [x] Social poster code complete (awaiting credentials — Phase 2)
- [x] tmt-admin-api plugin with 24 endpoints
- [x] tmt-api-logs for server-side debugging
- [x] llms.txt live for AI citation
- [x] Applied to Google News (awaiting decision)
- [x] 5-post combined daily limit (daily + breaking)

### Phase 2 — Social + Distribution (June–August 2026)

- [ ] Telegram channel live (easiest — do first)
- [ ] Twitter/X auto-posting
- [ ] LinkedIn company page auto-posting
- [ ] Mailchimp newsletter — Monday digest of top 5 posts
- [ ] OneSignal push notifications for breaking news
- [ ] Top up fal.ai ($5)
- [ ] GSC credentials setup for monthly optimizer
- [ ] Block xmlrpc.php in .htaccess

**You do manually:**
- [ ] Create TMT Twitter/X account + developer API keys
- [ ] Create TMT LinkedIn company page + OAuth token
- [ ] Create TMT Telegram channel + bot via @BotFather
- [ ] Reply to @JioCare, @airtelindia, @TRAI_Ind on Twitter 3×/week
- [ ] Write 1 guest post for Gadgets360 or MediaNama

**Target:** 1,000–3,000 monthly visitors. 50+ email subscribers.

### Phase 3 — Scale (August–October 2026)

- [ ] Plan comparison engine (auto-generates "Jio vs Airtel" posts)
- [ ] OTT bundle guide generator
- [ ] City-level 5G tracker content series
- [ ] Amazon Associates link injection on device posts
- [ ] Apply for Google AdSense

**Target:** 5,000–12,000 monthly visitors. ₹1,000–5,000/month AdSense.

### Phase 4 — Traffic + Monetization (November–December 2026)

- [ ] Twitter Trends → real-time story priority
- [ ] Fully automated weekly newsletter
- [ ] Keyword intelligence (volume + difficulty) fed into story selection

**Target:** 15,000–50,000 monthly visitors. ₹5,000–20,000/month.

**The single biggest variable: Google News approval.** One trending story = 5,000 visitors in a day.

---

## Budget

| Phase | Monthly Spend | What It Covers |
|-------|-------------|----------------|
| Phase 1 (now) | ₹540–640 | Claude API ₹500 + fal.ai ₹40 |
| Phase 2 | ₹640–740 | Same + minor tools |
| Phase 3 | ₹800–1,000 | + CDN if needed |
| Phase 4 | ₹1,200–2,000 | + keyword tools if traffic justifies |

**Break-even:** ~3,000 monthly visitors = AdSense covers all API costs.

---

## Setup Guides

### Google Search Console API (Monthly Optimizer)

1. console.cloud.google.com → Create project → Enable **Search Console API**
2. IAM & Admin → Service Accounts → Create → download JSON key
3. In Google Search Console → Settings → Users → add the service account email with "Full" permission
4. Add entire JSON file contents as GitHub Secret `GSC_CREDENTIALS`
5. Add `GSC_PROPERTY` = `https://themobiletimes.com/`

### Social Media Setup (Phase 2)

**Telegram (easiest — do first):**
1. Message @BotFather → `/newbot` → copy the token
2. Create a channel → add your bot as Administrator
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL` (e.g. `@TheMobileTimesNews`) in GitHub Secrets

**Twitter/X:**
1. developer.twitter.com → apply → create app → copy all 4 keys
2. Free tier: 1,500 posts/month (we post ~150/month)

**LinkedIn:**
1. linkedin.com/developers → Create App → attach TMT company page → enable "Share on LinkedIn"
2. Copy access token — **expires every 60 days, set a calendar reminder to renew**

---

## Credentials Reference

Never commit `.env`. All variables below are GitHub Secrets for Actions.

```
WP_URL                = https://themobiletimes.com
WP_USER               = sanjay
WP_APP_PASS           = xxxx xxxx xxxx xxxx xxxx xxxx
ANTHROPIC_API_KEY     = sk-ant-...
PEXELS_API_KEY        = ...
FAL_API_KEY           = ...   ← top up $5 at fal.ai/dashboard/billing
NEWS_API_KEY          = ...
TMT_SECRET            = ...   ← must match TMT_API_SECRET in wp-config.php
ALERT_EMAIL_PASS      = ...   ← Gmail app password for failure alerts
UNSPLASH_ACCESS_KEY   = ...
INDEXNOW_KEY          = ...   ← from Rank Math settings
GSC_PROPERTY          = https://themobiletimes.com/   ← not yet configured
GSC_CREDENTIALS       = { ... full JSON ... }          ← not yet configured
TELEGRAM_BOT_TOKEN    = ...   ← Phase 2
TELEGRAM_CHANNEL      = @TheMobileTimesNews            ← Phase 2
TWITTER_API_KEY       = ...   ← Phase 2
TWITTER_API_SECRET    = ...   ← Phase 2
TWITTER_ACCESS_TOKEN  = ...   ← Phase 2
TWITTER_ACCESS_SECRET = ...   ← Phase 2
LINKEDIN_ACCESS_TOKEN = ...   ← expires every 60 days (Phase 2)
LINKEDIN_ORG_ID       = ...   ← Phase 2
META_ACCESS_TOKEN     = ...   ← Phase 2
META_PAGE_ID          = ...   ← Phase 2
```
