# ═══════════════════════════════════════════════════════════════
#   THE MOBILE TIMES — CLAUDE CODE MASTER BRIEF (FINAL)
#   Hand this file to Claude Code. It has everything.
# ═══════════════════════════════════════════════════════════════

## OWNER
Khush Goyal | themobiletimes.com | Jaipur, India

## SITE
URL:          https://themobiletimes.com
CMS:          WordPress (self-hosted on Hostinger, LiteSpeed server)
Page Builder: Elementor
SEO Plugin:   Rank Math (already installed, REST API must be ON)
Cache Plugin: LiteSpeed Cache (install if not present)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ALL CREDENTIALS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WP_URL            = https://themobiletimes.com
WP_USER           = themobiletimes@gmail.com
WP_APP_PASS       = R6Bg ZLr2 gMd6 4RxX 7zjB gGQT
ANTHROPIC_API_KEY = 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
PEXELS_API_KEY    = hfFooWUMK8he74MiSi9sNOzEoRAkCBc0IxxAtPi63lGPOeOd8m7DSUYA
FAL_API_KEY       = 62111a11-d5a8-4ee7-a03d-616301bfd0e5:ca705983cf626a1cccaa10c2b667fe6c
LOGO_PATH         = Circle_Logo.png

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## WHAT TO BUILD — FULL SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Build, test, and launch a complete daily content automation 
system for The Mobile Times. The system must:

1. CONTENT AGENT    — publishes 6 posts daily at 8:00 AM IST
2. SEO              — Rank Math score 85+ on every post
3. SPEED            — optimise WordPress for fast loading
4. INDEXING         — ping Google after every publish
5. TESTING          — verify everything works before going live
6. WORDPRESS FIXES  — fix broken meta, category pages, CSS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## DAILY OUTPUT — 6 POSTS EVERY DAY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POSTS 1-5: NEWS (including 1 exclusive)
  - 400-500 words each
  - Pexels stock photo + TMT logo watermark
  - Category: AI decides based on content (see category map)
  - Tags: AI assigns from ONLY these 3 tags based on content:
      "trending"      → story is trending/popular topic
      "breaking-news" → urgent, major, time-sensitive news
      "new-launch"    → product, device, service launch
    A post can have 1, 2, or all 3 tags if relevant.
    Tags and categories are COMPLETELY SEPARATE things.
    Category = where it lives in the site structure.
    Tag = content label for filtering/display.

  BREAKING NEWS RULE:
    - The highest-scoring breaking story → tagged "breaking-news" + STICKY
    - Only 1 sticky breaking-news post per day
    - All other breaking stories → tagged "breaking-news" but NOT sticky
    - They go to /tag/breaking-news/ archive
    - At start of each day → auto-remove sticky from yesterday's breaking post

  NEW LAUNCH RULE:
    - The top product/launch story → tagged "new-launch" + STICKY
    - Only 1 sticky new-launch post per day
    - Others with launch content → tagged "new-launch" but NOT sticky
    - At start of each day → auto-remove sticky from yesterday's launch post

  EXCLUSIVE (1 of the 5 news posts):
    - Category: exclusive
    - Goes to /category/exclusive/
    - NOT a tag — it is a category
    - Source A (automatic daily): AI picks most interesting story,
      writes as deep TMT analysis with "TMT Exclusive:" prefix
    - Source B (on-demand): Khush provides tip → AI writes it up

POST 6: BLOG
  - 800-950 words
  - Goes under Insights section (subcategory decided by AI)
  - Subcategories available:
      industry-insights | how-to-guides | case-studies | press-releases
  - AI-generated image via fal.ai + TMT logo watermark
  - Full structure: ToC, pull quote, data box, verdict
  - Tags: same 3 tag system — AI assigns what's relevant
  - Rotates through weekly topics (see below)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## WORDPRESS CATEGORY STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTOMATED (agent posts here):

HOME:
  exclusive          → /category/exclusive/
  policy-updates     → /category/policy-updates/
  market-trends      → /category/market-trends/

INDUSTRY TRENDS:
  5g-networks        → /category/industry-trends/5g-networks/
  ott-streaming      → /category/industry-trends/ott-streaming/
  ev-smart-grids     → /category/industry-trends/ev-smart-grids/
  tech-innovation    → /category/industry-trends/tech-innovation/
  ar-vr              → /category/industry-trends/ar-vr/
  internet-of-things → /category/industry-trends/internet-of-things/

DEVICES & HARDWARE:
  smartphones-tablets    → /category/devices-hardware/smartphones-tablets/
  accessories-wearables  → /category/devices-hardware/accessories-wearables/
  network-smart-devices  → /category/devices-hardware/network-smart-devices/

TECHNOLOGIES:
  softwares          → /category/technologies/softwares/
  cybersecurity      → /category/technologies/cybersecurity/
  ai-machine-learning → /category/technologies/ai-machine-learning/
  data-analytics     → /category/technologies/data-analytics/

INSIGHTS (blog goes here):
  industry-insights  → /category/insights/industry-insights/
  how-to-guides      → /category/insights/how-to-guides/
  case-studies       → /category/insights/case-studies/
  press-releases     → /category/insights/press-releases/

NOT AUTOMATED:
  E-Magazine, Advertise With Us, About, Contact

Category IDs are unknown — fetch via:
  GET {WP_URL}/wp-json/wp/v2/categories?per_page=100
  Authorization: Basic base64(WP_USER:WP_APP_PASS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CATEGORY ROUTING — AI DECISION LOGIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For every news post, Claude reads title + summary and picks
the best slug. Fallback = tech-innovation.

exclusive          → TMT original analysis, insider scoops
policy-updates     → TRAI, DOT, government, spectrum, regulations
market-trends      → Revenue, M&A, market share, funding, business
5g-networks        → 5G rollout, spectrum, fiber, towers, NR
ott-streaming      → Netflix, JioCinema, Zee5, streaming deals
ev-smart-grids     → EV charging, smart grids, energy tech
tech-innovation    → Startups, R&D, emerging tech
ar-vr              → AR, VR, metaverse, spatial computing
internet-of-things → Smart home, M2M, IIoT, connected devices
smartphones-tablets    → Phone/tablet launches, reviews, specs
accessories-wearables  → Earbuds, smartwatches, chargers, bands
network-smart-devices  → Routers, modems, mesh networks
softwares              → Apps, SaaS, enterprise software, OS
cybersecurity          → Hacking, breaches, privacy, VPNs, malware
ai-machine-learning    → LLMs, GenAI, ML models, ChatGPT, automation
data-analytics         → Big data, cloud, analytics, data science

For blog: pick from industry-insights / how-to-guides /
          case-studies / press-releases based on topic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TAG LOGIC — ONLY 3 TAGS EXIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tags are SEPARATE from categories. Every post gets 1-3 tags.

"trending"      → story matches trending keyword OR is high-relevance
"breaking-news" → urgent, major, time-sensitive, exclusive breaking news
"new-launch"    → product launch, device announced, service released,
                  app launched, feature unveiled

Tagging rules:
  - AI reads title + summary and assigns relevant tags
  - Can assign 1, 2, or all 3 if all apply
  - Example: "Jio launches new 5G phone" → new-launch + trending
  - Example: "Major data breach at Airtel" → breaking-news + trending
  - Example: "Samsung Galaxy S25 Ultra India price" → new-launch
  - Tags are created in WP if they don't exist

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## RSS FEED SOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

https://economictimes.indiatimes.com/tech/telecom/rssfeeds/13357270.cms
https://telecomtalk.info/feed/
https://www.medianama.com/feed/
https://entrackr.com/feed/
https://www.lightreading.com/rss.xml
https://www.fiercetelecom.com/rss.xml
https://www.telecompaper.com/rss/all-news.xml
https://feeds.feedburner.com/gadgets360-latest
https://feeds.feedburner.com/TheHackersNews
https://venturebeat.com/category/ai/feed/
https://techcrunch.com/feed/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## TRENDING KEYWORDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use pytrends to pull from Google Trends India daily.
Seed keywords:
  "5G India", "Jio Airtel", "TRAI regulation", "telecom policy India",
  "smartphone launch India", "cybersecurity India", "AI telecom",
  "OTT streaming India", "BSNL", "satellite internet India"

Fallback if pytrends fails: use seed keywords randomly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## NEWS POST STRUCTURE (400-500 words)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Featured Image 1200x628 — Pexels + TMT logo watermark bottom-right]
[Badge based on tag: 🔴 BREAKING / 🚀 NEW LAUNCH / 🔥 TRENDING]

<p class="tmt-intro">
  <strong>[Hook — focus keyword in first sentence].</strong>
  [2-3 sentences of context.]
</p>

<div class="tmt-highlights">
  <h3>📌 Key Highlights</h3>
  <ul>
    <li>[Stat or fact with number]</li>
    <li>[Fact 2]</li>
    <li>[Fact 3]</li>
    <li>[Fact 4]</li>
  </ul>
</div>

<h2>[Heading — contains focus keyword]</h2>
<p>[150-180 words. Facts, India angle, real companies, real data.]</p>

<h2>[Impact heading]</h2>
<p>[120-150 words. Consequences. Industry impact.]</p>

<blockquote class="tmt-quote">
  "[Expert quote]" — Industry Analyst, Telecom Sector
</blockquote>

<h2>Outlook & What To Watch</h2>
<p>[100-120 words. Forward-looking. Specific milestones.]</p>

<p class="tmt-sources">
  <strong>Sources:</strong>
  <a href="https://www.trai.gov.in" target="_blank" rel="noopener nofollow">TRAI ↗</a> |
  <a href="https://www.gsma.com" target="_blank" rel="noopener nofollow">GSMA ↗</a> |
  <a href="https://www.coai.in" target="_blank" rel="noopener nofollow">COAI ↗</a>
</p>

[JSON-LD NewsArticle schema]
[Internal links auto-injected — see map below]
[Rank Math meta: title 50-60 chars, desc 120-158 chars, focus keyword, OG tags]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## BLOG POST STRUCTURE (800-950 words) — GOES IN INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Featured Image 1200x628 — fal.ai AI generated + TMT logo watermark]
[Badge: ⭐ EXCLUSIVE ANALYSIS]

<p class="tmt-intro">
  <strong>[Bold claim — focus keyword here].</strong>
  [3-4 sentences. Stakes. Why now.]
</p>

<div class="tmt-toc">
  <h3>📋 In This Article</h3>
  <ol>
    <li><a href="#s1">...</a></li>
    <li><a href="#s2">...</a></li>
    <li><a href="#s3">...</a></li>
    <li><a href="#s4">...</a></li>
    <li><a href="#s5">The Mobile Times Verdict</a></li>
  </ol>
</div>

<h2 id="s1">[Context — focus keyword] (180-200 words)</h2>
<h2 id="s2">[Core Problem/Opportunity] (180-200 words)</h2>

<blockquote class="tmt-quote">
  "[Editorial quote]" — The Mobile Times Editorial
</blockquote>

<h2 id="s3">[What Industry Gets Wrong — focus keyword] (150-170 words)</h2>

<div class="tmt-data-box">
  <h3>📊 By The Numbers</h3>
  <ul>
    <li><strong>[Metric]:</strong> [Figure]</li>
    <li><strong>[Metric]:</strong> [Figure]</li>
    <li><strong>[Metric]:</strong> [Figure]</li>
    <li><strong>[Metric]:</strong> [Figure]</li>
  </ul>
</div>

<h2 id="s4">[What Must Happen Next] (150-170 words)</h2>

<h2 id="s5">The Mobile Times Verdict</h2>
<p class="tmt-verdict">[120-140 words. TMT definitive position.]</p>

<p class="tmt-sources"><strong>Sources:</strong> TRAI ↗ | GSMA ↗ | Ericsson ↗</p>

[JSON-LD BlogPosting schema]
[Internal links auto-injected]
[Tags: assign relevant tags from the 3 available]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## WEEKLY BLOG TOPICS (AI picks Insights subcategory)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monday:    Jio vs Airtel 2025: Who Is Really Winning the Indian Telecom War?
Tuesday:   Why India's 5G Rollout Is Slower Than Promised — And What Must Change
Wednesday: BSNL's Revival Plan: A Genuine Comeback or Too Little Too Late?
Thursday:  How AI Is Reshaping Customer Service Across Indian Telecom
Friday:    The OTT Battleground: Can Indian Platforms Beat Netflix and Amazon?
Saturday:  Satellite Internet in India: Starlink, OneWeb and Rural Connectivity
Sunday:    India's Smartphone Market in 2025: Rise of Premium, Fall of Budget

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## IMAGE PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEWS (posts 1-5):
  Source:   Pexels API → https://api.pexels.com/v1/search
  Header:   Authorization: {PEXELS_API_KEY}
  Query:    focus keyword + "India technology"
  Per page: 5, orientation: landscape
  Pick:     random from top 3 results
  Size:     resize to 1200x628

BLOG (post 6):
  Source:   fal.ai → POST https://fal.run/fal-ai/flux/schnell
  Header:   Authorization: Key {FAL_API_KEY}
  Prompt:   "Professional editorial tech magazine photograph for
             article about [topic]. Clean, modern, high quality.
             No text, no watermarks, no faces."
  Size:     landscape_16_9 → resize to 1200x628
  Fallback: if fal.ai fails → use Pexels

ALL IMAGES — LOGO WATERMARK:
  Logo file: Circle_Logo.png (512x512, RGB, black background)
  Step 1: Convert to RGBA
  Step 2: Strip black background:
          for each pixel: if R<40 AND G<40 AND B<40 → alpha=0
  Step 3: Resize logo to 14% of image width
  Step 4: Opacity 88%
  Step 5: Place bottom-right corner, 22px padding
  Step 6: Cache cleaned logo (only strip once per run)

FALLBACK IMAGE (if both Pexels and fal.ai fail):
  Background: #0A1628 (dark navy)
  Title text: white, centered, DejaVu Bold font
  Bottom bar: #CC0000 (TMT red), 8px height
  Tagline: "The Mobile Times | India's Telecom Authority"

UPLOAD TO WORDPRESS:
  POST {WP_URL}/wp-json/wp/v2/media
  Content-Type: image/jpeg
  Content-Disposition: attachment; filename="tmt-{type}-{date}.jpg"
  Then PATCH media to set:
    alt_text: "{focus_keyword} — {title[:50]}"
    caption: "© The Mobile Times"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## RANK MATH SEO — 85+ SCORE ON EVERY POST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Set these fields via WordPress REST API meta:
  rank_math_title              → 50-60 chars, keyword + "| The Mobile Times"
  rank_math_description        → 120-158 chars, keyword + CTA
  rank_math_focus_keyword      → primary trending keyword
  rank_math_og_title           → 60-70 chars
  rank_math_og_description     → 180-200 chars
  rank_math_twitter_title      → same as og_title
  rank_math_twitter_description → same as og_description

Content must have:
  ✅ Focus keyword in title
  ✅ Focus keyword in first 100 words
  ✅ Focus keyword in minimum 2 H2 headings
  ✅ Focus keyword in meta description
  ✅ Focus keyword in URL slug
  ✅ Focus keyword in image alt text
  ✅ Meta description 120-158 chars
  ✅ Title 50-60 chars
  ✅ 400+ words (news) / 800+ words (blog)
  ✅ Min 2 internal links
  ✅ Min 1 external authority link
  ✅ JSON-LD schema
  ✅ OG + Twitter cards
  ✅ Keyword density 1-2%

IMPORTANT: Rank Math → General Settings → REST API must be ON
for meta fields to save via API.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## INTERNAL LINKS — AUTO-INJECT ON FIRST KEYWORD MATCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"5G"             → /category/industry-trends/5g-networks/
"cybersecurity"  → /category/technologies/cybersecurity/
"AI"             → /category/technologies/ai-machine-learning/
"smartphones"    → /category/devices-hardware/smartphones-tablets/
"IoT"            → /category/industry-trends/internet-of-things/
"OTT"            → /category/industry-trends/ott-streaming/
"telecom policy" → /category/policy-updates/
"market trends"  → /category/market-trends/
"wearables"      → /category/devices-hardware/accessories-wearables/
"data analytics" → /category/technologies/data-analytics/
"EV"             → /category/industry-trends/ev-smart-grids/
"software"       → /category/technologies/softwares/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## AUTHORITY BACKLINKS — USE 2-3 PER POST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRAI     → https://www.trai.gov.in
DOT      → https://dot.gov.in
GSMA     → https://www.gsma.com
COAI     → https://www.coai.in
ITU      → https://www.itu.int
Ericsson → https://www.ericsson.com/en/reports-and-papers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## INDEXING — RUN AFTER EVERY PUBLISH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. IndexNow ping (Bing → shared with Google):
   GET https://www.bing.com/indexnow?url={post_url}&key=tmt-indexnow

2. Google sitemap ping:
   GET https://www.google.com/ping?sitemap=https://themobiletimes.com/sitemap.xml

3. LiteSpeed cache purge:
   POST https://themobiletimes.com/wp-json/litespeed/v1/purge/all
   Authorization: Basic base64(WP_USER:WP_APP_PASS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SPEED OPTIMISATION — DO VIA WP REST API + DIRECT CALLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target: Under 2.5 second load time, Google PageSpeed 80+

1. LiteSpeed Cache settings (via plugin options API or direct):
   - Page Cache: ON
   - CSS/JS/HTML Minify: ON
   - Image Lazy Load: ON
   - WebP Conversion: ON
   - Browser Cache: ON
   - QUIC.cloud CDN: ON (free tier)

2. Verify these Hostinger server settings are active:
   - Gzip/Brotli compression
   - HTTP/2
   - PHP 8.2

3. Add to WordPress functions.php for performance:
   // Remove emoji scripts (saves ~15KB per page)
   remove_action('wp_head', 'print_emoji_detection_script', 7);
   remove_action('wp_print_styles', 'print_emoji_styles');
   // Remove query strings from static files
   function remove_query_strings($src) {
     if(strpos($src, '?ver=')) $src = remove_query_arg('ver', $src);
     return $src;
   }
   add_filter('style_loader_src', 'remove_query_strings', 10, 2);
   add_filter('script_loader_src', 'remove_query_strings', 10, 2);
   // Auto-unsticky old breaking/launch posts after 24 hours
   add_action('wp', 'tmt_unsticky_old_posts');
   function tmt_unsticky_old_posts() {
     $sticky_ids = get_option('sticky_posts');
     if (empty($sticky_ids)) return;
     foreach ($sticky_ids as $post_id) {
       $post_date = get_post_field('post_date', $post_id);
       if (strtotime($post_date) < strtotime('-24 hours')) {
         unstick_post($post_id);
       }
     }
   }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## WORDPRESS FIXES REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fix these via WordPress REST API where possible, else document
exact manual steps for Khush:

1. Homepage meta description — currently "Go to Cyber Security"
   Fix via Rank Math REST API or document Yoast/Rank Math path

2. Homepage title — currently "Home - The Mobile Times"
   Set to: "India Telecom News, 5G & Tech Updates | The Mobile Times"

3. Homepage meta description to set:
   "India's leading telecom trade publication covering 5G,
   smartphones, AI, cybersecurity and telecom policy. Daily
   news and expert analysis since 2009."

4. All 16 category pages are empty
   Write 100-word SEO intro for each category and provide
   as copy-paste content for Khush to add manually

5. Submit sitemaps to Google Search Console:
   - https://themobiletimes.com/sitemap.xml
   - https://themobiletimes.com/news-sitemap.xml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## WORDPRESS CSS — INJECT VIA REST API OR PROVIDE FOR MANUAL ADD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/* TMT Article Styles */
.tmt-featured-image{margin:0 0 2rem;border-radius:8px;overflow:hidden}
.tmt-featured-image img{width:100%;height:auto;display:block}
.tmt-featured-image figcaption{font-size:12px;color:#888;padding:6px 10px;background:#f7f7f7;text-align:right}
.tmt-intro{font-size:1.15rem;line-height:1.75;border-left:4px solid #CC0000;padding-left:1.25rem;margin-bottom:2rem}
.tmt-highlights{background:#fff5f5;border:1px solid #ffb3b3;border-radius:8px;padding:1.25rem 1.5rem;margin:1.75rem 0}
.tmt-highlights h3{font-size:1rem;font-weight:700;color:#CC0000;margin:0 0 .75rem;text-transform:uppercase;letter-spacing:.04em}
.tmt-highlights ul{margin:0;padding-left:1.25rem}
.tmt-highlights ul li{margin-bottom:.4rem;font-size:.95rem;line-height:1.55}
.tmt-toc{background:#f8f9fa;border:1px solid #e0e0e0;border-radius:8px;padding:1.25rem 1.5rem;margin:1.75rem 0}
.tmt-toc h3{font-size:.95rem;font-weight:700;color:#333;margin:0 0 .75rem;text-transform:uppercase}
.tmt-toc ol{margin:0;padding-left:1.4rem}
.tmt-toc ol li a{color:#CC0000;text-decoration:none;font-weight:500}
.tmt-quote{border-top:3px solid #CC0000;border-bottom:3px solid #CC0000;margin:2rem 0;padding:1.25rem 1.5rem;font-size:1.12rem;font-style:italic;background:#fff9f9;line-height:1.65}
.tmt-data-box{background:#0A1628;color:#e0f0ff;border-radius:8px;padding:1.25rem 1.5rem;margin:1.75rem 0}
.tmt-data-box h3{font-size:.95rem;font-weight:700;color:#ff9999;margin:0 0 .75rem;text-transform:uppercase}
.tmt-data-box ul{margin:0;padding:0;list-style:none}
.tmt-data-box ul li{border-bottom:1px solid rgba(255,255,255,.08);padding:.45rem 0;font-size:.93rem}
.tmt-data-box ul li strong{color:#ff9999}
.tmt-verdict{background:#fff5f5;border:1px solid #ffb3b3;border-radius:8px;padding:1.25rem 1.5rem;font-weight:500;line-height:1.7}
.tmt-sources{font-size:.82rem;color:#888;border-top:1px solid #eee;padding-top:.75rem;margin-top:2rem}
.tmt-sources a{color:#CC0000;text-decoration:none;margin:0 4px}
.tmt-breaking-badge{background:#CC0000;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.tmt-launch-badge{background:#0A1628;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.tmt-trending-badge{background:#FF6B00;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.tmt-exclusive-badge{background:#6B21A8;color:#fff;display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;font-weight:700;margin-bottom:1rem}
.entry-content h2{font-size:1.35rem;font-weight:700;margin:2rem 0 .75rem;padding-bottom:.4rem;border-bottom:2px solid #f0f0f0}
.entry-content a[href*="themobiletimes.com"]{color:#CC0000;font-weight:500}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PYTHON DEPENDENCIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pip install anthropic feedparser requests python-dotenv schedule Pillow pytrends

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## EXECUTION FLOW FOR CLAUDE CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO THESE IN ORDER:

PHASE 1 — SETUP
  1. Install Python dependencies
  2. Create .env file with all credentials above
  3. Fetch WP category IDs:
     GET {WP_URL}/wp-json/wp/v2/categories?per_page=100
  4. Build the 3 WordPress tags if they don't exist:
     POST {WP_URL}/wp-json/wp/v2/tags with {name, slug} for each:
     - name: "Trending",      slug: "trending"
     - name: "Breaking News", slug: "breaking-news"
     - name: "New Launch",    slug: "new-launch"
  5. Add CSS to WordPress Additional CSS via Customizer API
  6. Add functions.php performance code via file edit or API
  7. Configure LiteSpeed Cache settings
  8. Enable Rank Math REST API (document manual step if no API)

PHASE 2 — BUILD
  9. Write complete mobiletimes_agent.py script
  10. Write test_connections.py script
  11. Verify all API connections work

PHASE 3 — SPEED & SEO
  12. Test site speed (fetch homepage, measure response time)
  13. Verify Rank Math meta fields save correctly via test post
  14. Verify IndexNow ping works
  15. Verify LiteSpeed cache purge works

PHASE 4 — TEST RUN
  16. Run agent once: python mobiletimes_agent.py --run-now
  17. Verify 6 posts published on WordPress
  18. Check each post:
      - Correct category assigned?
      - Correct tags assigned (from only 3)?
      - Breaking/Launch set as sticky?
      - Featured image uploaded with TMT logo?
      - Rank Math meta filled in?
      - Schema present in source?
      - Internal links injected?
      - Word count correct?
  19. Report results — show Khush what was published

PHASE 5 — GO LIVE
  20. Schedule: python mobiletimes_agent.py --schedule
      Runs daily at 08:00 AM IST automatically

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## IMPORTANT NOTES FOR CLAUDE CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Hostinger blocks requests from some cloud servers/IPs.
   Run everything from LOCAL MACHINE, not cloud IDEs.

2. Rank Math REST API must be ON in WP admin:
   Rank Math → General Settings → REST API = ON
   Without this, meta fields won't save via API.

3. Circle_Logo.png has BLACK background — must strip it.
   Pixels where R<40 AND G<40 AND B<40 → set alpha to 0.
   Cache the cleaned logo after first process.

4. Tags (trending, breaking-news, new-launch) and Categories
   are COMPLETELY SEPARATE in WordPress.
   - Categories determine site section / URL structure
   - Tags are content labels for filtering
   - Do not mix them up in the API calls
   - Tags go in "tags" field, categories in "categories" field

5. Only 3 tags exist. Do not create any other tags.
   AI decides which 1-3 tags to assign per post.

6. Breaking-news and new-launch main posts = sticky=True.
   All others = sticky=False.
   Remove yesterday's sticky before setting today's.

7. Blog goes in Insights category — AI picks subcategory.
   It is NOT the same as the news posts.

8. Claude model for content: claude-sonnet-4-6
   Claude model for routing/meta: claude-haiku-4-5-20251001

9. Anthropic API needs credits added:
   console.anthropic.com/settings/billing → add $5 minimum

10. Test every single component before declaring done.
    Show Khush the published posts on WordPress after test run.
