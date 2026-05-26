# The Mobile Times — Automation System

**Site:** themobiletimes.com  
**Owner:** Sanjay Goyal, Editor-in-Chief  
**Goal:** 15,000–50,000 monthly visitors by December 2026  
**Budget:** ₹2,000/month all-in  
**Last updated:** May 26, 2026 — Phase 1 live ✅ Applied to Google News

---

## What This Does (Plain English)

This system runs themobiletimes.com automatically — no human needs to touch it day to day.

**Every single day, without you doing anything:**

- At 5 specific times (8am, 10am, 12pm, 3pm, 6pm IST), GitHub's free servers wake up, scan Indian telecom news from **35+ RSS feeds + News API** (150,000 sources), Claude AI picks the most relevant story from all available categories, writes a 430–1,000 word article, finds a matching image (source article image first → Pexels → fallback), watermarks it with the TMT logo, and publishes it to WordPress.

- Every 30 minutes, a separate check scans for truly breaking news (Airtel launching 5G in a new city, TRAI issuing a new rule, etc.). If something important enough is found, it publishes immediately as a breaking news post.

- On the 1st of every month, it pulls Google Search Console data to find articles ranking on page 2 but getting almost no clicks, then rewrites their meta descriptions to improve click-through rate.

**When you want to post something specific:**
Go to GitHub → Actions → "Post Manual Story" → type a topic or paste a URL → done in 3 minutes.

**What it does NOT do yet:**
- No social media posting yet — Twitter, LinkedIn, Telegram activate in Phase 2
- Does not send email newsletters (Phase 2)
- Does not earn money on its own — you still need to apply for AdSense (Phase 3)

---

## How It Works — The Full Flow

### Regular Posts (5 per day)

```
08:00 IST  →  Slot 1
10:00 IST  →  Slot 2
12:00 IST  →  Slot 3
15:00 IST  →  Slot 4
18:00 IST  →  Slot 5 (Blog / Insights — fixed weekly topic)
```

Each slot runs independently and uses fresh news at the time it fires:

```
GitHub wakes up at scheduled time
  ↓
1. Fetch stories: News API first (keyword queries) → 35+ RSS feeds as supplement
2. Remove stories already published (URL history + title similarity check)
3. Claude Haiku picks the best story from ALL telecom/tech categories dynamically
   (no fixed category per slot — picks the best story available at that moment,
    covering diverse categories across the 4 daily news slots)
   Slot 5 → Weekly Blog Post (fixed topic roster, rotates by day of week)
  ↓
4. Claude Sonnet writes a full article (430–1,000 words)
     - 6 article templates: Breaking / Analysis / Product / Deep Dive / Investor / Comparison
     - Comparison template includes a full HTML comparison table (tmt-table-wrap class)
     - Auto-injects internal links to related TMT categories
     - Auto-injects 2–3 authority links (TRAI, GSMA, COAI)
     - Adds "Related Reading" block from recent TMT posts
     - 3 FAQ items at the bottom for Google People Also Ask
     - Auto-TOC injected for articles 800+ words with 3+ sections
     - Body image (Pexels, no watermark) injected between sections
     - NewsArticle schema handled by Rank Math; FAQPage schema from FAQ blocks
5. Content QA — hard stop on:
     - Unfilled template placeholders (e.g. [Stat or fact])
     - Articles under 400 words
     - Wrong years auto-corrected (2020–2025 → 2026)
6. Image pipeline:
     News API urlToImage → Source article OG image → Pexels stock photo → fallback
     → Resize to 1200×628 → Watermark (9% width, 80% opacity) → Upload to WordPress
     Alt text: "{Article Title} | The Mobile Times"
     Title attribute: focus keyword
7. Publish the article live (never sticky)
8. Push SEO metadata via Rank Math API (focus keyword, meta title, meta description)
9. Flush WP Super Cache via tmt-admin-api plugin
10. Ping IndexNow → instant Bing/Yandex indexing
11. Save story URL to deduplication history so it is never republished
```

### Breaking News (every 30 minutes, 24/7)

```
Every 30 min → GitHub wakes up
  ↓
1. Check if 3 breaking posts already published today → if yes, skip
2. Check WordPress: similar story published in last 24 hours? → if yes, skip
3. Fetch stories: News API (3 queries) → 35+ RSS feeds, deduplicated
4. Score each story on India-telecom relevance (0–100)
5. If best story scores ≥ 65:
     Claude writes urgent 600–750 word breaking article
     → Publish immediately (no sticky)
     → Ping IndexNow
     → Flush WP Super Cache
```

### Monthly SEO (1st of every month)

```
1st of month → GitHub wakes up
  ↓
1. Pull Google Search Console data (last 90 days)
2. Find posts with: impressions > 50, CTR < 3%, position 10–25
   (articles almost ranking but not getting clicked)
3. Claude rewrites their meta title and description to be more clickable
4. Update via Rank Math API
```

---

## Architecture

```
themobiletimes.com
        │
        ├── GitHub Actions (free, cloud, no PC needed)
        │       ├── daily-posts.yml     → 5 cron triggers per day (one per slot)
        │       ├── breaking-news.yml   → every 30 min
        │       ├── manual-story.yml    → on-demand via GitHub UI
        │       └── monthly-seo.yml     → 1st of month
        │
        ├── Python Scripts (Automation/)
        │       ├── mobiletimes_agent.py   → core: News API + RSS → AI → WordPress
        │       ├── breaking_monitor.py    → urgency scoring + breaking posts
        │       ├── social_poster.py       → Twitter / LinkedIn / Telegram (Phase 2)
        │       └── gsc_optimizer.py       → monthly meta rewriting from GSC data
        │
        ├── External APIs (Active)
        │       ├── Claude Sonnet 4.6      → article writing
        │       ├── Claude Haiku 4.5       → story routing, SEO metadata
        │       ├── News API (newsapi.org) → 150,000+ sources, keyword queries
        │       ├── 35+ RSS feeds          → India + global telecom/tech news
        │       ├── Pexels                 → featured images (royalty-free)
        │       ├── fal.ai                 → AI image generation (blog posts)
        │       ├── IndexNow               → instant Bing/Yandex indexing
        │       └── Google Search Console  → monthly traffic data
        │
        └── WordPress (themobiletimes.com)
                ├── Foxiz v2.7.5 theme     → premium news/magazine layout
                ├── Rank Math SEO          → receives SEO meta from scripts
                ├── WP Super Cache         → flushed after each publish via plugin API
                ├── Autooptimize           → CSS/JS minification
                └── tmt-admin-api plugin   → cache flush, post update, meta update endpoints
```

---

## Complete File Map

Every file in this repository and what it does.

```
TMT/
│
├── Automation/
│   │
│   ├── ── CORE SCRIPTS (run automatically via GitHub Actions) ──
│   │
│   ├── mobiletimes_agent.py
│   │     The main publishing engine. Runs 5× daily (one per slot) and on demand.
│   │     Fetches news from News API + 35+ RSS feeds, routes to Claude Haiku for
│   │     story selection, writes article with Claude Sonnet using one of 6 templates,
│   │     handles the full image pipeline, publishes to WordPress, sets Rank Math SEO
│   │     meta, flushes WP Super Cache, pings IndexNow, and saves the URL to
│   │     seen_urls.json so it is never republished.
│   │     CLI: --slot N | --run-now | --single "topic" | --url "..." | --tip "..." | --test-post
│   │
│   ├── breaking_monitor.py
│   │     Runs every 30 minutes, 24/7. Scores all incoming stories 0–100 on
│   │     India-telecom relevance. If best story scores ≥ 65 and fewer than 3
│   │     breaking posts were published today, writes and publishes a 600–750 word
│   │     breaking news article immediately. Stateless dedup via WordPress API check.
│   │     CLI: --once (single check, exits — how GitHub Actions calls it)
│   │
│   ├── social_poster.py
│   │     Posts every published article to Twitter/X, LinkedIn, Telegram, and Facebook.
│   │     Called by mobiletimes_agent.py and breaking_monitor.py after each publish.
│   │     Each platform is independent — silently skips if its credentials are not set.
│   │     STATUS: Phase 2 — credentials not yet added, not yet active.
│   │
│   ├── gsc_optimizer.py
│   │     Runs on the 1st of every month. Pulls last 90 days of Google Search Console
│   │     data, finds posts with >50 impressions, <3% CTR, position 10–25 (almost
│   │     page 1 but nobody clicks). Uses Claude Haiku to rewrite meta descriptions
│   │     using the exact queries people searched, then pushes updates via Rank Math API.
│   │     Requires GSC_CREDENTIALS and GSC_PROPERTY secrets — currently skipped.
│   │
│   ├── ── ASSETS ──
│   │
│   ├── assets/
│   │   └── Circle_Logo.png
│   │         TMT circular logo. Watermarked onto every featured image at
│   │         9% of image width, 80% opacity, 18px padding from corner.
│   │
│   ├── ── CONFIG ──
│   │
│   ├── requirements.txt
│   │     Python package list. Installed fresh on every GitHub Actions run.
│   │     Key packages: anthropic, requests, feedparser, Pillow, tweepy, python-dotenv.
│   │
│   ├── llms.txt
│   │     Context file for AI citation engines (ChatGPT, Perplexity, Claude, Gemini).
│   │     Describes TMT's coverage areas, editorial team, and key pages.
│   │     Also deployed live at: https://themobiletimes.com/llms.txt
│   │
│   ├── .env  (not committed — local dev only)
│   │     Local copy of all credentials. GitHub Actions uses GitHub Secrets instead.
│   │
│   ├── seen_urls.json  (auto-generated, committed by workflow)
│   │     Running list of every story URL ever published. Used to prevent
│   │     republishing the same news. Committed back to repo after each run
│   │     by the daily-posts workflow so it persists across GitHub Actions runs.
│   │
│   ├── pexels_used_ids.json  (auto-generated)
│   │     List of Pexels photo IDs already used. Prevents the same stock photo
│   │     appearing on multiple articles.
│   │
│   ├── ── WORDPRESS PLUGIN ──
│   │
│   ├── tmt-admin-api/
│   │   └── tmt-admin-api.php
│   │         Custom WordPress plugin. MUST be active at all times.
│   │         Exposes 4 REST endpoints called by the scripts:
│   │           POST /wp-json/tmt/v1/health       → plugin health check
│   │           POST /wp-json/tmt/v1/post/update  → update post content
│   │           POST /wp-json/tmt/v1/update-meta  → set Rank Math SEO fields
│   │           POST /wp-json/tmt/v1/cache/flush  → flush WP Super Cache
│   │         All endpoints require TMT_SECRET header for authentication.
│   │
│   ├── ── DOCS ──
│   │
│   ├── README.md
│   │     This file. Full system documentation.
│   │
│   │
│
└── .github/
    └── workflows/
        │
        ├── daily-posts.yml
        │     5 cron triggers: 02:30, 04:30, 06:30, 09:30, 12:30 UTC
        │     (= 08:00, 10:00, 12:00, 15:00, 18:00 IST)
        │     Runs: python mobiletimes_agent.py --slot N
        │     Also: commits seen_urls.json back to repo after each run.
        │     Failure alert: email to goyalkhush1214@gmail.com
        │
        ├── breaking-news.yml
        │     Cron every 30 minutes, 24/7.
        │     Runs: python breaking_monitor.py --once
        │     Failure alert: email to goyalkhush1214@gmail.com
        │
        ├── manual-story.yml
        │     Triggered manually from GitHub Actions UI.
        │     Inputs: topic (text) or url (text).
        │     Runs: python mobiletimes_agent.py --single "..." or --url "..."
        │
        └── monthly-seo.yml
              Cron: 03:00 UTC on the 1st of every month (= 08:30 IST).
              Runs: python gsc_optimizer.py
              Skips gracefully if GSC credentials not configured.
              Failure alert: email to goyalkhush1214@gmail.com
```

### WordPress Plugin — tmt-admin-api

`tmt-admin-api/tmt-admin-api.php` must be **active on WordPress at all times.**

| Endpoint | Used for |
|----------|---------|
| `POST /wp-json/tmt/v1/health` | Plugin health check before each run |
| `POST /wp-json/tmt/v1/post/update` | Update post content |
| `POST /wp-json/tmt/v1/update-meta` | Save Rank Math SEO meta |
| `POST /wp-json/tmt/v1/cache/flush` | Flush WP Super Cache after publishing |

Secret key stored in GitHub Secrets as `TMT_SECRET`. Never commit to repo.

---

## Manual Story Trigger

**From phone or any browser (GitHub UI):**
```
GitHub repo → Actions tab → "Post Manual Story" → Run workflow
  ↓
Fill in either:
  Topic  →  "Airtel hikes prepaid plans by 20% from June 1"
  OR
  URL    →  "https://telecomtalk.info/airtel-hike-article"
  ↓
Publishes within 3–5 minutes to WordPress
```

**From PC (Automation/ folder):**
```bash
# Write article from a topic (publishes immediately)
python mobiletimes_agent.py --single "Airtel hikes prepaid plans by 20%"

# Rewrite a source article in TMT voice
python mobiletimes_agent.py --url "https://telecomtalk.info/some-article"

# Feed a manual news tip into the next slot's story selection
python mobiletimes_agent.py --tip "Jio announces free 5G trial in Tier 2 cities"

# Run a specific slot now
python mobiletimes_agent.py --slot 2

# Run all 5 slots at once
python mobiletimes_agent.py --run-now

# Generate 1 draft post without publishing (for previewing)
python mobiletimes_agent.py --test-post
```

---

## GitHub Secrets

Go to: `Repo → Settings → Secrets and variables → Actions → New repository secret`

| Secret | Value | Status |
|--------|-------|--------|
| `WP_URL` | `https://themobiletimes.com` | ✅ |
| `WP_USER` | WordPress username | ✅ |
| `WP_APP_PASS` | WordPress Application Password (with spaces) | ✅ |
| `ANTHROPIC_API_KEY` | Claude API key | ✅ |
| `PEXELS_API_KEY` | Pexels API key | ✅ |
| `FAL_API_KEY` | fal.ai key | ✅ |
| `NEWS_API_KEY` | newsapi.org key | ✅ |
| `TMT_SECRET` | tmt-admin-api plugin secret | ✅ |
| `ALERT_EMAIL_PASS` | Gmail app password for failure alerts | ✅ |
| `INDEXNOW_KEY` | Handled by Rank Math | ✅ Skipped |
| `GSC_PROPERTY` | `https://themobiletimes.com/` | ⏭ Skipped |
| `GSC_CREDENTIALS` | Google service account JSON | ⏭ Skipped |
| `TELEGRAM_BOT_TOKEN` | From @BotFather | Phase 2 |
| `TELEGRAM_CHANNEL` | `@TheMobileTimesNews` | Phase 2 |
| `TWITTER_API_KEY` | Twitter developer app key | Phase 2 |
| `TWITTER_API_SECRET` | Twitter developer app secret | Phase 2 |
| `TWITTER_ACCESS_TOKEN` | Twitter account access token | Phase 2 |
| `TWITTER_ACCESS_SECRET` | Twitter account access token secret | Phase 2 |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn OAuth token (expires every 60 days) | Phase 2 |
| `LINKEDIN_ORG_ID` | LinkedIn company page numeric ID | Phase 2 |
| `META_ACCESS_TOKEN` | Facebook page access token | Phase 2 |
| `META_PAGE_ID` | Facebook page numeric ID | Phase 2 |

---

## Article Templates

| Template | Best for | Key feature |
|----------|---------|------------|
| A — Breaking | Urgent news, launches, policy | No TOC, highlights first, punchy |
| B — Analysis | Policy, market, regulatory | Data blocks, expert quotes |
| C — Product | Device launches, app releases | Specs box, verdict callout |
| D — Deep Dive | 5G, OTT, IoT trends | TOC, numbered sections |
| E — Investor | Funding, M&A, market data | Stat callouts, forward-looking |
| F — Comparison | Plan vs plan, device vs device | Full HTML comparison table |

---

## Content Strategy

### What Drives the Most Traffic

| Rank | Type | Why it works | Example |
|------|------|-------------|---------|
| #1 | Plan comparisons | Huge search volume, users deciding what to buy, evergreen | "Jio Rs 299 vs Airtel Rs 349: Who Wins June 2026?" |
| #2 | Breaking news | Google News spike, social sharing, immediate traffic | "Airtel Launches 5G in 12 New Cities Across India" |
| #3 | Lists | Scannability, featured snippet bait, shareable | "10 Best 5G Phones Under ₹20,000: June 2026" |
| #4 | How-to guides | Long tail keywords, voice search | "How to Port From Jio to Airtel Without Losing Your Plan" |
| #5 | Device launches | Launch traffic spike + comparison intent | "OnePlus 14 India Price, Specs and Verdict" |

### 3 Best Content Gaps vs Competitors

1. **TRAI consumer rights in plain English** — nobody covers this clearly. Low competition, high trust signal.
2. **City-level 5G coverage tracker** — "Is 5G Available in Jaipur 2026?" — high local intent, nobody maintains it.
3. **OTT + telecom bundle master guide** — which Jio plan includes which streaming service? Always changing, always searched.

---

## Roadmap to December 2026

### Phase 1 — Foundation ✅ COMPLETE (May 25, 2026)

- [x] 5 GitHub Actions crons (one per slot, true 24/7 publishing)
- [x] `--slot N`, `--run-now`, `--single`, `--url`, `--tip`, `--test-post` CLI flags
- [x] `seen_urls.json` permanent deduplication across all runs
- [x] Dynamic category selection — AI picks best story from ALL categories per slot
- [x] News API integration (primary source, RSS as supplement, 35+ feeds)
- [x] 6 article templates including Template F (comparison table)
- [x] QA hard-stop — unfilled placeholders or sub-400-word articles abort publishing
- [x] Humanization rules — 30+ AI tell-tale phrases banned, em dashes banned, sentence variety enforced
- [x] Image SEO — alt text `"{title} | The Mobile Times"`, title = focus keyword
- [x] Watermark — 9% width, 80% opacity
- [x] No sticky posts anywhere in the system
- [x] Cache flush via tmt-admin-api after every publish
- [x] Breaking monitor — max 3/day, score threshold 65
- [x] IndexNow instant indexing on every publish
- [x] Auto-TOC injection for 800+ word articles with 3+ H2 sections
- [x] Body image (second Pexels photo, no watermark) injected between sections
- [x] `pexels_used_ids.json` deduplication — same Pexels photo never reused
- [x] tmt-admin-api plugin — health, post/update, update-meta, cache/flush endpoints
- [x] llms.txt live at themobiletimes.com/llms.txt for AI citation
- [x] All SEO meta (titles, descriptions) set on all pages and 24 category pages
- [x] AI crawlers allowed: GPTBot, ClaudeBot, PerplexityBot, Google-Extended in robots.txt
- [x] GA4 orphaned tag removed, GA4 linked to Search Console
- [x] Applied to Google News (decision in 2–8 weeks)

**One remaining item:**
- [ ] Top up fal.ai $5 at fal.ai/dashboard/billing — needed for AI-generated images on blog posts. Pexels covers news posts in the meantime.

---

### Phase 2 — Social + Distribution (June – August 2026)

- [ ] Social media live: Twitter, LinkedIn, Telegram, Facebook auto-posting on every article
- [ ] Mailchimp newsletter — auto-digest of top 5 posts every Monday
- [ ] OneSignal push notifications — breaking news alerts to subscribers
- [ ] GA4 topic feedback loop — agent learns which categories get traffic
- [ ] TRAI consumer rights content series

**You do:**
- [ ] Create TMT Twitter/X account + get API keys at developer.twitter.com
- [ ] Create TMT LinkedIn company page + OAuth access token
- [ ] Create TMT Telegram channel + bot via @BotFather
- [ ] Add social secrets to GitHub Secrets
- [ ] Reply to @JioCare, @airtelindia, @TRAI_Ind on Twitter 3×/week as Sanjay
- [ ] Write 1 guest post for Gadgets360 or MediaNama
- [ ] Share Telegram channel in relevant WhatsApp groups

**Target:** 1,000–3,000 monthly visitors. 50+ email subscribers. 200+ Telegram members.

---

### Phase 3 — Scale What Works (August – October 2026)

- [ ] Monthly plan comparison engine (auto-generates "X vs Y" posts)
- [ ] OTT bundle guide generator
- [ ] Amazon Associates link injection on device review posts
- [ ] Smart pillar linker — new articles auto-link to matching pillar pages
- [ ] City-level 5G tracker content series

**You do:**
- [ ] Apply for Google AdSense
- [ ] Reach out to 5 Indian tech bloggers for link exchanges

**Target:** 5,000–12,000 monthly visitors. ₹1,000–5,000/month AdSense.

---

### Phase 4 — Traffic and Monetization (November – December 2026)

- [ ] Trending topic detector (Twitter Trends → agent priorities in real time)
- [ ] Fully automated weekly newsletter
- [ ] Ahrefs/Semrush API — keyword difficulty + volume fed into article selection

**Target:**
- 15,000–50,000 monthly visitors (upper end requires Google News approval)
- ₹5,000–20,000/month AdSense revenue
- Site is 95% self-running

---

## Budget

| Phase | Monthly Spend | What It Covers |
|-------|-------------|----------------|
| Phase 1 (now) | ₹540–640 | Claude API ₹500 + fal.ai ₹40 |
| Phase 2 | ₹640–740 | Same + minor tools |
| Phase 3 | ₹800–1,000 | + BunnyCDN ₹200 |
| Phase 4 | ₹1,200–2,000 | + Ahrefs if traffic justifies it |

**Break-even:** ~3,000 monthly visitors = AdSense covers all API costs.

---

## Setup Guides

### Google Search Console API (Monthly Optimizer)

**Status: Skipped for now.** The monthly meta optimizer (`gsc_optimizer.py`) is the only script that needs this. All 5 daily slots, breaking news, and manual triggers work without it. The workflow handles missing credentials gracefully — logs a warning and skips.

To set up later:
1. console.cloud.google.com → Create project → Enable **Search Console API**
2. IAM & Admin → Service Accounts → Create → download JSON key
3. Add JSON contents as GitHub Secret `GSC_CREDENTIALS`
4. Add `GSC_PROPERTY` = `https://themobiletimes.com/`

### Social Media Setup (Phase 2)

**Telegram (easiest — do first):**
1. Message @BotFather → `/newbot` → copy the token
2. Create a channel → add your bot as Administrator
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL` in GitHub Secrets

**Twitter/X:**
1. developer.twitter.com → apply → create app → copy all 4 keys
2. Free tier: 1,500 posts/month (we use ~150/month)

**LinkedIn:**
1. linkedin.com/developers → Create App → attach TMT company page → enable "Share on LinkedIn"
2. Copy access token — **expires every 60 days, set a calendar reminder**

---

## The Single Biggest Variable

**Google News approval.** One article on a trending telecom story can pull 5,000 visitors in a single day.

**Status: Applied ✅ (May 25, 2026) — waiting for decision (2–8 weeks)**

The site meets all requirements:
- NewsArticle schema on every post (Rank Math) ✅
- Named author with full bio page (Sanjay Goyal, Editor-in-Chief) ✅
- Consistent daily publishing schedule ✅
- Fast loading, clean URLs ✅
- About page with entity description ✅
- AI crawlers allowed: GPTBot, ClaudeBot, PerplexityBot, Google-Extended ✅
- llms.txt live for AI citation ✅

---

## Credentials Reference

Never commit `.env`. All variables below are GitHub Secrets for Actions.

```
WP_URL                = https://themobiletimes.com
WP_USER               = sanjay
WP_APP_PASS           = xxxx xxxx xxxx xxxx xxxx xxxx
ANTHROPIC_API_KEY     = sk-ant-...
PEXELS_API_KEY        = ...
FAL_API_KEY           = ...
NEWS_API_KEY          = ...
TMT_SECRET            = ...
ALERT_EMAIL_PASS      = ...   (Gmail app password for failure alerts)
INDEXNOW_KEY          = ...   (optional — Rank Math handles this)
GSC_PROPERTY          = https://themobiletimes.com/   (skipped)
GSC_CREDENTIALS       = { ... full JSON ... }          (skipped)
TELEGRAM_BOT_TOKEN    = ...   (Phase 2)
TELEGRAM_CHANNEL      = @TheMobileTimesNews            (Phase 2)
TWITTER_API_KEY       = ...   (Phase 2)
TWITTER_API_SECRET    = ...   (Phase 2)
TWITTER_ACCESS_TOKEN  = ...   (Phase 2)
TWITTER_ACCESS_SECRET = ...   (Phase 2)
LINKEDIN_ACCESS_TOKEN = ...   ← expires every 60 days  (Phase 2)
LINKEDIN_ORG_ID       = ...   (Phase 2)
META_ACCESS_TOKEN     = ...   (Phase 2)
META_PAGE_ID          = ...   (Phase 2)
```
