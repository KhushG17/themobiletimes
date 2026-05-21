# Google News Publisher Center — Submission Guide for The Mobile Times

## Step 1: Apply at Google News Publisher Center

1. Go to: https://publishercenter.google.com
2. Sign in with: **goyalkhush1214@gmail.com** (your Google account)
3. Click **"Add publication"**
4. Enter:
   - Publication name: **The Mobile Times**
   - URL: **https://themobiletimes.com**
   - Country: **India**
   - Language: **English**
5. Click **Continue**

---

## Step 2: Verify ownership

Google will ask you to verify ownership. **Choose: "Google Search Console"**
- Since you already have GSC set up, this is instant — just click Verify.

---

## Step 3: Configure publication settings

In the Publisher Center dashboard:
- **Category**: Technology → Telecommunications
- **Description**: India's leading telecom and 5G news publication. Coverage of TRAI, Jio, Airtel, BSNL, smartphones, cybersecurity, AI, and IoT.
- **Logo**: Upload the circle logo (400×400 px or rectangular version)
- **RSS feed URL**: https://themobiletimes.com/feed/
- **Publication type**: News Publisher

---

## Step 4: Sections (important for Google News ranking)

Add these sections mapping to your RSS:
| Section Name        | RSS Feed URL                                          |
|---------------------|-------------------------------------------------------|
| All News            | https://themobiletimes.com/feed/                      |
| 5G Networks         | https://themobiletimes.com/category/industry-trends/5g-networks/feed/ |
| Cybersecurity       | https://themobiletimes.com/category/technologies/cybersecurity/feed/  |
| Smartphones         | https://themobiletimes.com/category/devices-hardware/smartphones-tablets/feed/ |
| Policy Updates      | https://themobiletimes.com/category/policy-updates/feed/ |

---

## Step 5: Editorial guidelines (you must confirm)

Google asks you to confirm:
- ✅ Clear authorship (Sanjay Goyal is named on posts)
- ✅ About page exists (run: `python entity_schema_updater.py`)
- ✅ Contact information available
- ✅ No misleading content or clickbait

---

## Step 6: Submit for review

- Click **"Request review"**
- Review takes **2–6 weeks**
- Google checks: content quality, site traffic, editorial standards

---

## While waiting: things that speed up approval

1. **Publish 20+ news articles** before applying (you already have 16+ — keep going with the daily agent)
2. **Author bylines visible on all posts** — the author schema fix in this update handles JSON-LD; also add "By Sanjay Goyal" visually in the post template if your theme supports it
3. **No duplicate content** — the agent now deduplicates
4. **Consistent publishing** — the daily agent runs at 08:00 IST; make sure it's running every day

---

## After approval: what changes

- Posts from themobiletimes.com appear in Google News feed → millions more impressions
- Breaking news posts get a "Breaking News" label in Google News → huge CTR boost
- Site gets included in Google News alerts for tracked topics

---

## Troubleshooting if rejected

| Rejection reason | Fix |
|-----------------|-----|
| "Not enough original content" | Keep publishing daily for 30 days, then reapply |
| "Unclear ownership" | Ensure About page (run entity_schema_updater.py) is live |
| "Formatting issues" | Check that all posts render cleanly on mobile |
| "Insufficient traffic" | Wait 60 days and ensure Google Analytics / GSC is connected |
