# The Mobile Times — Automation System

**Site:** themobiletimes.com  
**Owner:** Sanjay Goyal, Editor-in-Chief  
**Goal:** 15,000–50,000 monthly visitors by December 2026  
**Budget:** ₹2,000/month all-in  
**Last updated:** May 2026

---

## What This Does (Plain English)

This system runs themobiletimes.com automatically — no human needs to touch it day to day.

**Every single day, without you doing anything:**

- At 5 specific times throughout the day (8am, 10am, 12pm, 3pm, 6pm IST), GitHub's free servers wake up, scan Indian telecom news from 11 sources, pick the most relevant story for that time slot, write a 400–1,000 word article using Claude AI, find a matching image, watermark it with the TMT logo, and publish it to WordPress. Once social media is activated (Phase 2), it will also simultaneously post to Twitter, LinkedIn, and Telegram.

- Every 30 minutes, a separate check scans for truly breaking news (Airtel launching 5G in a new city, TRAI issuing a new rule, etc.). If something important enough is found, it publishes immediately as a sticky breaking news post.

- On the 1st of every month, it pulls Google Search Console data to find articles that are ranking on page 2 but getting almost no clicks, then rewrites their meta descriptions to improve click-through.

**When you want to post something specific:**
- Go to GitHub → Actions → "Post Manual Story" → type a topic or paste a URL → done in 3 minutes.

**What it does NOT do yet:**
- No social media posting yet — Twitter, LinkedIn, Telegram activate in Phase 2
- Does not learn from traffic data to write more of what works (Phase 3)
- Does not send email newsletters (Phase 2)
- Does not earn money on its own — you still need to apply for AdSense (Phase 3)

---

## How It Works — The Full Flow

### Regular Posts (5 per day, spread throughout the day)

```
08:00 IST  →  GitHub triggers Slot 1
10:00 IST  →  GitHub triggers Slot 2
12:00 IST  →  GitHub triggers Slot 3
15:00 IST  →  GitHub triggers Slot 4
18:00 IST  →  GitHub triggers Slot 5 (Blog)
```

Each slot runs independently and uses fresh news at the time it fires:

```
GitHub wakes up at scheduled time
  ↓
1. Scan 11 RSS news feeds (~70 stories pulled)
2. Remove stories already published (checks URL history + title similarity)
3. Pick the best story for that slot's category:
     Slot 1 → Policy / Market / Exclusive
     Slot 2 → Technology (AI, Cybersecurity, Software)
     Slot 3 → Devices & Hardware (Smartphones, Accessories)
     Slot 4 → Industry Trends (5G, OTT, IoT, EV)
     Slot 5 → Weekly Blog Post (fixed topic roster, changes daily)
  ↓
4. Claude Sonnet writes a full article (420–1,000 words)
     - 5 article templates: Breaking / Analysis / Product / Deep Dive / Investor
     - Auto-injects internal links to related TMT categories
     - Auto-injects 2–3 authority links (TRAI, GSMA, COAI)
     - Adds "Related Reading" block from recent TMT posts
     - 3 FAQ items at the bottom for Google People Also Ask
     - NewsArticle + FAQPage JSON-LD schema embedded
5. Image pipeline:
     Source article OG image → Pexels stock photo → AI-generated fallback
     → Resize to 1200×628 → Watermark with TMT logo → Upload to WordPress
6. Publish the article live
7. Push SEO metadata via Rank Math API (focus keyword, meta description)
8. Ping IndexNow → instant Bing indexing
9. Post to Twitter (with category hashtags)
10. Post to LinkedIn (with teaser text)
11. Post to Telegram channel
12. Save story URL to deduplication history so it's never republished
```

### Breaking News (every 30 minutes, 24/7)

```
Every 30 min → GitHub wakes up
  ↓
1. Check if we've already published 3 breaking posts today → if yes, skip
2. Check WordPress: has a similar story been published in the last 24 hours? → if yes, skip
3. Scan RSS feeds, score each story on India-telecom relevance (0–100)
4. If the best story scores ≥ 65:
     Claude writes urgent 380–440 word breaking article
     → Publish immediately as sticky post
     → Post to all social channels with 🚨 BREAKING header
     → Ping IndexNow
```

### Monthly SEO (1st of every month)

```
1st of month → GitHub wakes up
  ↓
1. Pull Google Search Console data (last 90 days)
2. Find posts with: impressions > 50, CTR < 3%, position 10–25
   (these are articles almost ranking but not getting clicked)
3. Claude rewrites their meta title and description to be more clickable
4. Update via Rank Math API
```

---

## Architecture at a Glance

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
        │       ├── mobiletimes_agent.py   → core: RSS → AI → WordPress → Social
        │       ├── breaking_monitor.py    → urgency scoring + breaking posts
        │       ├── social_poster.py       → Twitter / LinkedIn / Telegram
        │       └── gsc_optimizer.py       → monthly meta rewriting from GSC data
        │
        ├── External APIs
        │       ├── Claude Sonnet 4.6      → article writing
        │       ├── Claude Haiku 4.5       → story routing, SEO metadata
        │       ├── Pexels                 → featured images
        │       ├── fal.ai                 → AI image generation (blog posts)
        │       ├── IndexNow               → instant Bing indexing
        │       └── Google Search Console  → monthly traffic data
        │
        └── WordPress (themobiletimes.com)
                ├── Rank Math SEO          → receives SEO meta from scripts
                ├── LiteSpeed Cache        → cache cleared after each publish
                └── tmt-performance.php    → custom schema + article styling
```

---

## File Inventory

### Active Scripts

| File | What it does |
|------|-------------|
| `mobiletimes_agent.py` | Core engine — runs all 5 daily slots, manual triggers, URL rewriting |
| `breaking_monitor.py` | Breaking news scanner — scores stories, publishes urgent ones |
| `social_poster.py` | Posts to Twitter, LinkedIn, Telegram with category-aware hashtags |
| `gsc_optimizer.py` | Monthly meta description optimizer using real GSC search data |
| `pillar_page_creator.py` | Creates/refreshes evergreen 1,600-word guide pages (10 live) |
| `seo_meta_updater.py` | Bulk-updates SEO on existing posts (run when needed) |
| `seo_pages_updater.py` | SEO on About/Contact/Privacy pages (run when needed) |
| `entity_schema_updater.py` | Updates About page entity schema (run when needed) |
| `fix_markdown_artifacts.py` | Cleans any backtick artifacts from posts (utility) |

**One-time setup scripts** → archived in `Automation/archive/`

### GitHub Actions Workflows

| Workflow | Cron | What it runs |
|----------|------|-------------|
| `daily-posts.yml` | 5× daily (08:00, 10:00, 12:00, 15:00, 18:00 IST) | `mobiletimes_agent.py --slot N` |
| `breaking-news.yml` | Every 30 min | `breaking_monitor.py --once` |
| `manual-story.yml` | On demand | `mobiletimes_agent.py --single "topic"` or `--url "..."` |
| `monthly-seo.yml` | 1st of month, 08:30 IST | `gsc_optimizer.py` |

### WordPress Plugin — tmt-performance.php

| Feature | Status |
|---------|--------|
| NewsMediaOrganization schema on homepage | ✅ |
| Author bio card (Sanjay Goyal, Editor-in-Chief) | ✅ |
| Article CSS: callout boxes, TOC, data tables, related reading block | ✅ |
| Reading progress bar | ✅ |
| fetchpriority=high on first image (LCP fix) | ✅ |
| Auto-unsticky breaking posts older than 24 hours | ✅ |

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
Publishes within 3–5 minutes to WordPress + all social platforms
```

**From PC:**
```bash
# Write article from a topic description
python mobiletimes_agent.py --single "Airtel hikes prepaid plans by 20%"

# Rewrite a source article in TMT voice
python mobiletimes_agent.py --url "https://telecomtalk.info/some-article"

# Run a specific slot now (useful for testing)
python mobiletimes_agent.py --slot 2

# Run all 5 slots at once
python mobiletimes_agent.py --run-now
```

---

## What Can Be Improved

These are known gaps, ranked by impact. None need immediate action — they're the next logical upgrades once Phase 1 is stable.

### High Impact (Phase 2 — do these next)

**1. Agent learns from traffic data**  
Currently the agent picks stories based on RSS + trending keywords + a fixed category system. It has no idea which TMT articles actually got traffic. If we feed it the top 10 performing articles from GA4 each week, it would start to understand that "plan comparison" articles get 10× more clicks than "IoT chipset" articles and naturally prioritize similar content.  
*What's needed: GA4 API read access + a weekly report that the agent uses as a priority hint.*

**2. Comparison content engine**  
"Jio vs Airtel" type posts are the #1 traffic driver in Indian telecom (per research). The current agent can write these if the news feed surfaces them, but it has no dedicated pipeline for generating fresh plan comparison tables automatically. A monthly "Best Prepaid Plans" post with a real comparison table would pull consistent search traffic.  
*What's needed: A script that fetches current plan data (from operators' sites or an API) and generates a comparison post.*

**3. Newsletter (Mailchimp)**  
Every subscriber is a guaranteed reader who doesn't depend on Google ranking you. A weekly digest of the top 5 posts, auto-sent every Monday, costs nothing and builds a direct audience.  
*What's needed: Mailchimp free account + subscribe form on site + one Python function to query WP for top posts and send.*

**4. Push notifications (OneSignal)**  
For breaking news, push notifications are instant reach — no algorithm, no social feed. Subscribers get a ping the moment a breaking article is published.  
*What's needed: OneSignal free account + a small code snippet in the WordPress theme + one API call from breaking_monitor.py.*

### Medium Impact (Phase 3)

**5. Smarter image sourcing**  
Current image pipeline: OG image from source article → Pexels stock photo → fallback. The Pexels photos are generic (random "technology" or "India" photos). fal.ai generates images specific to each story topic, but the key runs out of credit. Investing ₹80–150/month in fal.ai credits would make every article image unique and on-brand.  
*What's needed: Top up fal.ai, shift blog posts + breaking news to AI images instead of Pexels.*

**6. City-level coverage content**  
"5G coverage in Jaipur", "Airtel 5G in Bangalore" — nobody maintains this. High local search intent, almost zero competition. Could be a monthly auto-generated post for each major city using operator coverage map APIs.  
*What's needed: A coverage data source + a templated city-page generator.*

**7. Amazon affiliate link injection**  
Device launch and review articles can include "Buy on Amazon" links. With even 100 affiliate clicks per day at 2% conversion, this pays for API costs.  
*What's needed: Amazon Associates account + a function that finds device names in articles and appends affiliate buy links.*

**8. Internal linking is one-directional**  
Right now, every new article links TO category pages. But new articles don't get linked FROM existing pillar pages automatically. Pillar pages should be updated monthly to include links to the best recent articles in their topic.  
*What's needed: A monthly job that reads the 10 pillar pages and injects links to recent high-quality posts.*

### Lower Priority (Phase 4)

**9. Increasing post frequency beyond 5/day**  
The current 5-slot system is designed to scale. Adding a 6th slot (e.g. 21:00 IST for night readers) requires adding one cron line to `daily-posts.yml` and running `--slot 6`. The agent handles it automatically.  
*What's needed: 3 lines of YAML + define what Slot 6 covers.*

**10. Trending topic injection**  
Currently trending keywords (from Google Trends) are used to bias story selection, but the agent doesn't proactively write about what's trending if it's not in the RSS feeds. A trending detector that finds a hot topic (e.g. "Jio down" trending on Twitter) and creates an article around it would capture first-mover traffic.  
*What's needed: Twitter API trending endpoint + a check that runs every few hours.*

**11. Social media is one-way broadcast**  
The agent posts to Twitter and LinkedIn but never reads replies, mentions, or engagement. Responding to comments would build following faster. This is a manual task for now (Sanjay doing it) but could be partially automated with a reply bot in Phase 4.  
*What's needed: Manual effort now; Twitter API mentions endpoint later.*

**12. No Facebook distribution**  
`social_poster.py` has Facebook code built in but disabled. TMT Facebook page could auto-receive every article. FB has lower organic reach than it used to, but some telecom audiences (especially 35–50 age group) are still heavily on Facebook.  
*What's needed: Facebook Page access token + Meta API credentials.*

### Technical Debt

**13. LinkedIn token expiry (60 days)**  
LinkedIn access tokens expire after 60 days. When they expire, LinkedIn posting silently fails. There's no alert.  
*Fix: Add a token expiry check at startup that logs a warning if the token is within 7 days of expiry.*

**14. No email alert on workflow failure**  
If a GitHub Action fails (RSS is down, Claude API is over quota, WordPress is unreachable), it fails silently. Sanjay would only know if he checked the Actions tab.  
*Fix: Add a `on: workflow_run` failure notification that sends a Telegram message to Sanjay.*

**15. Article quality is not verified post-publish**  
The agent has a content QA function that checks for wrong years and unfilled placeholders, but it only logs warnings — it doesn't block publishing. A badly generated article could still go live.  
*Fix: Treat QA warnings as hard failures and abort publishing if critical issues are found.*

---

## Content Strategy

### What Content Types Drive the Most Traffic

| Rank | Type | Why it works | Example |
|------|------|-------------|---------|
| #1 | Plan comparisons | Huge search volume, users deciding what to buy, evergreen | "Jio Rs 299 vs Airtel Rs 349: Who Wins May 2026?" |
| #2 | Breaking news | Google News spike, social sharing, immediate traffic | "Airtel Launches 5G in 12 New Cities Across India" |
| #3 | Lists | Scannability, featured snippet bait, shareable | "10 Best 5G Phones Under ₹20,000: May 2026 Edition" |
| #4 | How-to guides | Long tail keywords, voice search, pillar material | "How to Port From Jio to Airtel Without Losing Your Plan" |
| #5 | Device launches | Launch traffic spike, then comparison intent | "OnePlus 14 India Price, Specs and Verdict" |

### Headline Formulas That Get Clicks

**Price/comparison:** `[Brand] Rs [X] vs [Brand] Rs [Y]: [Differentiator]`

**Monthly edition:** `[Topic]: [Month Year] Edition — All Plans Compared`

**Consumer implication:** `[Event]: Here's What It Means for Your [Bill / Speed / Coverage]`

**Authority + number:** `[N] [Topic] [Power word] India in [Year]`

### 3 Content Gaps vs Competitors

1. **TRAI consumer rights in plain English** — TelecomTalk and Gadgets360 don't cover this. "Know Your Rights as a Telecom Customer in India." Targets frustrated users who got overcharged or throttled. Low competition, high trust.

2. **City-level 5G coverage tracker** — "Is 5G Available in Jaipur 2026?" Nobody maintains this. Huge local search intent. Update monthly, city by city.

3. **OTT + telecom bundle master guide** — Which Jio plan includes which streaming service? Which Airtel plan includes Amazon Prime? Always-changing, always searched. Tables win featured snippets.

---

## Setup Guides

### GitHub Actions (Step by Step)

**Step 1: Push the repo to GitHub**
```bash
git init
git remote add origin https://github.com/YOUR_USERNAME/themobiletimes-automation.git
git add .
git commit -m "Phase 1: full automation setup"
git push -u origin main
```

**Step 2: Add GitHub Secrets**  
Go to: `Repo → Settings → Secrets and variables → Actions → New repository secret`

| Secret Name | Value |
|-------------|-------|
| `WP_URL` | `https://themobiletimes.com` |
| `WP_USER` | your WordPress username |
| `WP_APP_PASS` | WordPress Application Password (with spaces) |
| `ANTHROPIC_API_KEY` | your Claude API key |
| `PEXELS_API_KEY` | your Pexels API key |
| `FAL_API_KEY` | your fal.ai key |
| `TELEGRAM_BOT_TOKEN` | from @BotFather |
| `TELEGRAM_CHANNEL` | `@YourChannelName` |
| `TWITTER_API_KEY` | Twitter developer app API key |
| `TWITTER_API_SECRET` | Twitter developer app API secret |
| `TWITTER_ACCESS_TOKEN` | your Twitter account access token |
| `TWITTER_ACCESS_SECRET` | your Twitter account access token secret |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn OAuth token (expires every 60 days) |
| `LINKEDIN_ORG_ID` | LinkedIn company page numeric ID |
| `INDEXNOW_KEY` | free from bing.com/indexnow |
| `GSC_PROPERTY` | `https://themobiletimes.com/` |
| `GSC_CREDENTIALS` | full JSON contents of gsc-credentials.json |

**Step 3: Enable workflows**  
Go to `Repo → Actions`. If workflows show "disabled", click Enable on each.

**Test immediately:** Go to breaking-news workflow → Run workflow → watch the logs. Should finish in under 90 seconds.

---

### GA4 Setup (Fix Double Tag)

**Problem:** Two GA4 tracking codes are firing on every page (`GT-P3J38FVG` and `G-XYCJE9ZLL5`). This double-counts all traffic.

**Fix (10 minutes in WP Admin):**

1. **WP Admin → Rank Math → General Settings → Analytics** — if a GA4 property ID is set here, remove it (keep GA4 only in GTM, not in two places)
2. **tagmanager.google.com** → open your container → Tags → find the GA4 tag → confirm only one exists → delete any duplicate
3. Click **Submit / Publish** in GTM to deploy
4. **Link GA4 to Search Console:** In GA4 → Admin → Search Console links → Add link → select your GSC property → confirm
   - This unlocks keyword data inside GA4 (which search terms bring which visitors)

---

### Google Search Console API Setup (For Monthly Optimizer)

One-time setup (15 minutes):

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → Create project "TMT SEO"
2. APIs & Services → Library → search "Search Console API" → Enable
3. IAM & Admin → Service Accounts → Create: name `tmt-seo-reader`, role: **Viewer**
4. On the service account → Keys → Add Key → JSON → download
5. Rename the file to `gsc-credentials.json` — do NOT commit it (already in `.gitignore`)
6. In [Google Search Console](https://search.google.com/search-console) → Settings → Users and permissions → Add the service account email as **Restricted** user
7. For GitHub Actions: add a secret `GSC_CREDENTIALS` containing the full JSON, then add to `monthly-seo.yml`:
   ```yaml
   - run: echo '${{ secrets.GSC_CREDENTIALS }}' > Automation/gsc-credentials.json
   ```

---

### Social Media Setup

**Telegram (do this first — easiest):**
1. Open Telegram → message `@BotFather` → `/newbot` → follow prompts → copy the token
2. Create a channel → add your bot as Administrator
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL` in secrets

**Twitter/X:**
1. [developer.twitter.com](https://developer.twitter.com) → apply for developer account → create app
2. Keys and Tokens → copy API Key, API Secret, Access Token, Access Token Secret
3. Free tier: 1,500 posts/month (we use ~150/month — well within limits)

**LinkedIn:**
1. [linkedin.com/developers](https://www.linkedin.com/developers/apps) → Create App → attach TMT company page
2. Products tab → enable "Share on LinkedIn"
3. Auth tab → use the token generator tool to get an access token
4. Get company numeric ID from the LinkedIn page URL
5. **Important:** LinkedIn tokens expire every 60 days — set a recurring calendar reminder to refresh

**Social post formats:**
- **Twitter:** `{Title} {URL} #5GIndia #Telecom` (280 chars, category-specific hashtags)
- **LinkedIn:** `{Title}\n\n{teaser text}\n\nRead more: {URL}\n\n#TelecomIndia`
- **Telegram:** `🚨 BREAKING: {Title}\n{URL}` (breaking) or `📱 {Title}\n{URL}` (regular)

---

## All APIs & Tools

### Currently Active

| Tool | What it does | Cost |
|------|-------------|------|
| Claude Sonnet 4.6 | Writes all articles and blog posts | ~₹450/month |
| Claude Haiku 4.5 | Routes stories to categories, writes SEO metadata | ~₹50/month |
| WordPress REST API | Creates posts, uploads images, updates SEO meta | Free |
| Rank Math REST API | Saves focus keyword and meta description per post | Free |
| Pexels API | Fetches royalty-free stock photos | Free |
| feedparser (11 RSS feeds) | Pulls raw story data from news sources | Free |
| pytrends | Google Trends keyword data (has fallback if rate-limited) | Free |
| IndexNow API | Tells Bing/Yandex about new posts instantly | Free |
| GitHub Actions | Runs everything 24/7 with no server costs | Free |

### Need to Activate (Keys Exist)

| Tool | What to do | Cost |
|------|-----------|------|
| fal.ai | Top up $5 at fal.ai/dashboard/billing | ~₹40/month |
| Twitter API | Create developer app at developer.twitter.com | Free |
| LinkedIn API | Create app + OAuth token | Free |
| Telegram Bot | Create via @BotFather (5 minutes) | Free |
| Google Search Console API | Create service account (see above) | Free |

### Phase 2–3 Additions

| Tool | What it unlocks | Cost | When |
|------|----------------|------|------|
| Mailchimp | Weekly newsletter to subscribers | Free (up to 500) | Phase 2 |
| OneSignal | Push notifications for breaking news | Free (up to 10k) | Phase 2 |
| GA4 API | Agent reads traffic and writes more of what works | Free | Phase 3 |
| Amazon Associates | Affiliate links on device review articles | Revenue share | Phase 3 |
| BunnyCDN | Faster load times for India visitors | ₹80–400/month | Phase 3 |

### Scale Up When Traffic Grows

| Tool | What it unlocks | Cost | When |
|------|----------------|------|------|
| Ahrefs Starter | Keyword tracking, backlink analysis, content gaps | ₹2,500/month | 500+ daily visitors |
| Railway.app | Always-on server (sub-5 min breaking news response) | ₹420/month | After Google News approval |

---

## Roadmap to December 2026

### Phase 1 — Foundation (Target: June 15)

**Code — done:**
- [x] 5 separate GitHub Actions crons (one per slot, true 24/7 publishing)
- [x] `--slot N` argument for per-slot execution
- [x] `seen_urls.json` permanent deduplication across all runs
- [x] `--url` and `--single` manual post flags
- [x] Social posting: Twitter, LinkedIn, Telegram with category hashtags
- [x] IndexNow instant indexing on every publish
- [x] Breaking monitor: stateless WP API dedup (works without file persistence)
- [x] Folder cleaned — one-time scripts archived
- [x] `Circle_Logo.png` copied to `Automation/assets/` ✅

**You do (no coding):**
- [ ] Push repo to GitHub and enable Actions
- [ ] Add all GitHub Secrets (table above — 7 core + GSC)
- [ ] Get IndexNow key from bing.com/indexnow and verify site ownership
- [ ] Set up GSC service account (15 min — see GSC Setup section above)
- [ ] Fix double GTM tag in WP Admin + link GA4 to GSC (see GA4 Setup section above)
- [ ] Top up fal.ai ($5 at fal.ai/dashboard/billing)
- [ ] **Apply to Google News** at publishercenter.google.com ← most important
- [ ] Submit to Bing Webmaster Tools at bing.com/webmasters

**Social media deferred to Phase 2.**

**Phase 1 done when:** Site publishes 5 posts per day automatically, monthly SEO optimizer is live, Google News application is submitted.

---

### Phase 2 — Social + Distribution (June 15 – August 15)

**Build:**
- [ ] Social media live: Twitter, LinkedIn, Telegram auto-posting on every article
- [ ] Mailchimp newsletter — auto-digest of top 5 posts every Monday
- [ ] OneSignal push notifications — breaking news alerts to subscribers
- [ ] 5 new comparison pillar pages (Jio vs Airtel, Best Plans by city, 5G coverage)
- [ ] GA4 topic feedback loop — agent learns which categories get traffic
- [ ] TRAI consumer rights content series (content gap #1)

**You do:**
- [ ] Create TMT Twitter/X account + get API keys
- [ ] Create TMT LinkedIn company page + get access token
- [ ] Create TMT Telegram channel + bot via @BotFather
- [ ] Add social secrets to GitHub (TELEGRAM_BOT_TOKEN, TWITTER_*, LINKEDIN_*)
- [ ] Reply to @JioCare, @airtelindia, @TRAI_Ind on Twitter 3×/week as Sanjay
- [ ] Join 3 LinkedIn telecom groups — comment as editor
- [ ] Submit to HARO (helpareporter.com) for expert quote opportunities
- [ ] Write 1 guest post for Gadgets360 or MediaNama (best single backlink available)
- [ ] Share Telegram in relevant WhatsApp groups

**Target:** 1,000–3,000 monthly visitors. 50+ email subscribers. 200+ Telegram members.

---

### Phase 3 — Scale What Works (August 15 – October 31)

**Build:**
- [ ] Comparison content engine — auto-generates "X vs Y" plan comparison posts monthly
- [ ] OTT bundle guide generator (content gap #3)
- [ ] Amazon Associates link injection on device review posts
- [ ] Smart pillar linker — each article auto-links to its matching pillar page

**You do:**
- [ ] Apply for Google AdSense
- [ ] Reach out to 5 Indian tech bloggers for link exchanges
- [ ] Grow Telegram channel

**Target:** 5,000–12,000 monthly visitors. ₹1,000–5,000/month AdSense.

---

### Phase 4 — Traffic and Monetization (November – December 2026)

**Build:**
- [ ] Trending topic detector (Twitter + Trends → agent priorities in real time)
- [ ] Fully automated weekly newsletter
- [ ] Ahrefs integration if warranted

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
| Phase 4 | ₹1,200–2,000 | + Ahrefs ₹2,500 if traffic justifies it |

**Buffer:** ₹1,000–1,400/month stays unspent until traffic justifies new tools.  
**Break-even point:** ~3,000 monthly visitors = AdSense revenue covers API costs.

---

## The Single Biggest Variable

**Google News approval.** One article on a trending telecom story can pull 5,000 visitors in a single day. Without it, growth is steady but slower.

The site already meets all requirements:
- NewsArticle JSON-LD schema on every post ✅
- Named author with full bio page (Sanjay Goyal, Editor-in-Chief) ✅
- Consistent daily publishing schedule ✅
- Fast loading, clean URLs ✅
- About page with entity description ✅
- No ad-heavy or thin content ✅

**Apply at publishercenter.google.com — takes 10 minutes. Decision comes in 2–8 weeks.**

---

## Credentials Reference

Never commit `.env`. For GitHub Actions, every variable below becomes a GitHub Secret.

```
WP_URL                = https://themobiletimes.com
WP_USER               = sanjay
WP_APP_PASS           = xxxx xxxx xxxx xxxx xxxx xxxx
ANTHROPIC_API_KEY     = sk-ant-...
PEXELS_API_KEY        = ...
FAL_API_KEY           = ...
INDEXNOW_KEY          = ...
GSC_PROPERTY          = https://themobiletimes.com/
TELEGRAM_BOT_TOKEN    = ...
TELEGRAM_CHANNEL      = @TheMobileTimesNews
TWITTER_API_KEY       = ...
TWITTER_API_SECRET    = ...
TWITTER_ACCESS_TOKEN  = ...
TWITTER_ACCESS_SECRET = ...
LINKEDIN_ACCESS_TOKEN = ...   ← expires every 60 days
LINKEDIN_ORG_ID       = 12345678
```
