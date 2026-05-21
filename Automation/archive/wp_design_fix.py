"""
wp_design_fix.py — Inject improved article CSS + reading progress bar.
Tries the WP REST API first. If that fails, saves CSS to file with instructions.
"""
import os, re, base64, zipfile, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASS")
creds   = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HDR     = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

# ─────────────────────────────────────────────────────────────────────────────
#  The CSS — complete article design system
# ─────────────────────────────────────────────────────────────────────────────
ARTICLE_CSS = """
/* ═══════════════════════════════════════════════════════════════
   THE MOBILE TIMES — Article Design System
   Last updated: 2026-05
═══════════════════════════════════════════════════════════════ */

/* ── Reading progress bar (driven by tmt-progress.js) ── */
#tmt-progress-bar {
  position: fixed; top: 0; left: 0; width: 0;
  height: 3px; background: #cc0000; z-index: 99999;
  transition: width 0.15s linear;
  box-shadow: 0 0 8px rgba(204,0,0,.5);
}

/* ── Article body text ── */
.single-post .cmsmasters-single-post-content.entry-content,
.single-post .entry-content {
  font-size: 16.5px;
  line-height: 1.85;
  color: #1c1c2e;
  max-width: 780px;
}

.single-post .entry-content p {
  margin-bottom: 1.5em;
  font-size: 16.5px;
  line-height: 1.85;
}

/* ── H2 in articles ── */
.single-post .entry-content h2 {
  font-size: 1.35em;
  font-weight: 800;
  line-height: 1.3;
  margin: 2.2em 0 0.7em;
  padding-left: 14px;
  border-left: 4px solid #cc0000;
  color: #0d0d1a;
}

/* ── Article title ── */
.single-post .entry-title,
.single-post .cmsmasters-single-post-title h1 {
  font-size: clamp(1.55rem, 2.8vw, 2.1rem) !important;
  font-weight: 800 !important;
  line-height: 1.3 !important;
}

/* ── Featured image ── */
.single-post .cmsmasters-single-post-thumbnail img,
.single-post .post-thumbnail img,
.single-post .wp-post-image {
  width: 100%; height: auto;
  border-radius: 6px;
  display: block;
}

/* ─────────────────────────────────────────────────────────────
   TMT BADGES
───────────────────────────────────────────────────────────── */
.tmt-exclusive-badge,
.tmt-breaking-badge,
.tmt-launch-badge,
.tmt-trending-badge {
  display: inline-block;
  padding: 5px 13px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  margin-bottom: 18px;
  vertical-align: middle;
}
.tmt-exclusive-badge { background: #0d0d1a; color: #fff; border: 1px solid #444; }
.tmt-breaking-badge  { background: #cc0000; color: #fff; animation: tmt-blink 1.6s ease-in-out infinite; }
.tmt-launch-badge    { background: #0055cc; color: #fff; }
.tmt-trending-badge  { background: #e65c00; color: #fff; }

@keyframes tmt-blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.7; }
}

/* ─────────────────────────────────────────────────────────────
   INTRO PARAGRAPH
───────────────────────────────────────────────────────────── */
.tmt-intro {
  font-size: 17.5px !important;
  line-height: 1.75 !important;
  background: #fafafa;
  border-left: 4px solid #cc0000;
  border-radius: 0 6px 6px 0;
  padding: 16px 22px !important;
  margin-bottom: 1.8em !important;
  color: #111 !important;
}
.tmt-intro strong { color: #cc0000; }

/* ─────────────────────────────────────────────────────────────
   TABLE OF CONTENTS
───────────────────────────────────────────────────────────── */
.tmt-toc {
  background: #f4f6fb;
  border: 1px solid #dde2ec;
  border-radius: 8px;
  padding: 20px 26px;
  margin: 28px 0 32px;
}
.tmt-toc h3 {
  font-size: 11.5px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #666;
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ccc;
}
.tmt-toc ol { margin: 0; padding-left: 18px; }
.tmt-toc ol li { padding: 4px 0; font-size: 14.5px; line-height: 1.55; }
.tmt-toc ol li a {
  color: #1a3a8f;
  text-decoration: none;
  font-weight: 500;
  transition: color .2s;
}
.tmt-toc ol li a:hover { color: #cc0000; }

/* ─────────────────────────────────────────────────────────────
   KEY HIGHLIGHTS
───────────────────────────────────────────────────────────── */
.tmt-highlights {
  background: linear-gradient(135deg,#fff8f8,#fff);
  border: 1px solid #f0d0d0;
  border-left: 4px solid #cc0000;
  border-radius: 0 8px 8px 0;
  padding: 20px 26px;
  margin: 26px 0;
}
.tmt-highlights h3 {
  font-size: 11.5px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #cc0000;
  margin: 0 0 14px;
}
.tmt-highlights ul { margin: 0; padding: 0; list-style: none; }
.tmt-highlights ul li {
  padding: 7px 0 7px 22px;
  position: relative;
  font-size: 15px;
  line-height: 1.55;
  border-bottom: 1px solid #f5e5e5;
}
.tmt-highlights ul li:last-child { border-bottom: none; }
.tmt-highlights ul li::before {
  content: "→";
  position: absolute; left: 0;
  color: #cc0000; font-weight: 800;
}

/* ─────────────────────────────────────────────────────────────
   EXPERT QUOTE
───────────────────────────────────────────────────────────── */
.tmt-quote {
  border: none !important;
  border-left: 5px solid #cc0000 !important;
  background: #0d0d1a;
  color: #f0f0f0;
  padding: 22px 28px;
  border-radius: 0 8px 8px 0;
  margin: 32px 0;
  font-size: 16px !important;
  font-style: italic;
  line-height: 1.7;
}
.tmt-quote::after {
  content: '';
  display: block;
  margin-top: 14px;
  height: 1px;
  background: #333;
}

/* ─────────────────────────────────────────────────────────────
   DATA BOX (blog posts)
───────────────────────────────────────────────────────────── */
.tmt-data-box {
  background: #0d0d1a;
  color: #f0f0f0;
  border-radius: 8px;
  padding: 22px 26px;
  margin: 28px 0;
}
.tmt-data-box h3 {
  font-size: 11.5px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #cc0000;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #2a2a3a;
}
.tmt-data-box ul { margin: 0; padding: 0; list-style: none; }
.tmt-data-box ul li {
  display: flex; gap: 10px;
  padding: 9px 0; font-size: 14.5px;
  border-bottom: 1px solid #1e1e2e;
}
.tmt-data-box ul li:last-child { border-bottom: none; }
.tmt-data-box ul li strong { color: #aaa; min-width: 130px; flex-shrink: 0; }

/* ─────────────────────────────────────────────────────────────
   VERDICT BOX (blog posts)
───────────────────────────────────────────────────────────── */
.tmt-verdict {
  background: linear-gradient(135deg,#0d0d1a,#1a1a3e);
  color: #f0f0f0;
  padding: 22px 26px;
  border-radius: 8px;
  font-size: 16px;
  line-height: 1.8;
  margin-top: 10px;
}

/* ─────────────────────────────────────────────────────────────
   SOURCES LINE
───────────────────────────────────────────────────────────── */
.tmt-sources {
  font-size: 13px !important;
  color: #999 !important;
  border-top: 1px solid #eee;
  padding-top: 16px;
  margin-top: 36px;
}
.tmt-sources a { color: #666; text-decoration: none; margin: 0 3px; }
.tmt-sources a:hover { color: #cc0000; }

/* ─────────────────────────────────────────────────────────────
   BLOCKQUOTE FALLBACK
───────────────────────────────────────────────────────────── */
.single-post .entry-content blockquote:not(.tmt-quote) {
  border-left: 4px solid #cc0000;
  padding: 14px 20px;
  margin: 24px 0;
  background: #f9f9fb;
  font-style: italic;
  color: #333;
  border-radius: 0 6px 6px 0;
}

/* ─────────────────────────────────────────────────────────────
   MOBILE
───────────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .single-post .entry-content { font-size: 15.5px !important; }
  .tmt-intro    { font-size: 15.5px !important; padding: 12px 16px !important; }
  .tmt-quote    { padding: 16px 18px; font-size: 15px !important; }
  .tmt-toc, .tmt-highlights, .tmt-data-box { padding: 16px 18px; }
  .single-post .entry-content h2 { font-size: 1.2em; }
  #tmt-progress-bar { height: 2px; }
}

html { scroll-behavior: smooth; }
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Reading Progress Bar JS (tiny — 12 lines)
# ─────────────────────────────────────────────────────────────────────────────
PROGRESS_JS = """
document.addEventListener('DOMContentLoaded', function() {
  var bar = document.createElement('div');
  bar.id = 'tmt-progress-bar';
  document.body.appendChild(bar);
  window.addEventListener('scroll', function() {
    var doc  = document.documentElement;
    var top  = window.pageYOffset || doc.scrollTop;
    var full = doc.scrollHeight - doc.clientHeight;
    bar.style.width = full > 0 ? (top / full * 100) + '%' : '0';
  }, { passive: true });
});
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Updated tmt-performance plugin — adds CSS + JS inline
# ─────────────────────────────────────────────────────────────────────────────
PLUGIN_PHP = f'''<?php
/**
 * Plugin Name: TMT Performance & Auto-Unsticky
 * Plugin URI:  https://themobiletimes.com
 * Description: Removes emoji scripts, disables XML-RPC, auto-unsticky posts >24h, injects article styles.
 * Version:     1.2
 * Author:      The Mobile Times
 */

if ( ! defined( 'ABSPATH' ) ) exit;

/* ── Remove emoji ── */
remove_action( 'wp_head',             'print_emoji_detection_script', 7 );
remove_action( 'admin_print_scripts', 'print_emoji_detection_script' );
remove_action( 'wp_print_styles',     'print_emoji_styles' );
remove_action( 'admin_print_styles',  'print_emoji_styles' );
remove_filter( 'the_content_feed',    'wp_staticize_emoji' );
remove_filter( 'comment_text_rss',    'wp_staticize_emoji' );
remove_filter( 'wp_mail',             'wp_staticize_emoji_for_email' );

/* ── Disable XML-RPC ── */
add_filter( 'xmlrpc_enabled', '__return_false' );

/* ── Remove query strings from static assets ── */
add_filter( 'script_loader_src', 'tmt_remove_ver', 15, 1 );
add_filter( 'style_loader_src',  'tmt_remove_ver', 15, 1 );
function tmt_remove_ver( $src ) {{
    if ( strpos( $src, 'ver=' ) )
        $src = remove_query_arg( 'ver', $src );
    return $src;
}}

/* ── Auto-unsticky posts older than 24 hours ── */
add_action( 'wp_scheduled_delete', 'tmt_auto_unsticky' );
add_action( 'init',                'tmt_auto_unsticky' );
function tmt_auto_unsticky() {{
    $sticky = get_option( 'sticky_posts', [] );
    if ( empty( $sticky ) ) return;
    foreach ( $sticky as $id ) {{
        $post = get_post( $id );
        if ( ! $post ) continue;
        $age = time() - strtotime( $post->post_date_gmt . ' UTC' );
        if ( $age > 86400 ) {{
            unstick_post( $id );
        }}
    }}
}}

/* ── Inject article CSS ── */
add_action( 'wp_head', 'tmt_article_css', 20 );
function tmt_article_css() {{
    echo '<style id="tmt-design-system">' . tmt_get_css() . '</style>';
}}

/* ── Inject reading progress bar JS (single posts only) ── */
add_action( 'wp_footer', 'tmt_progress_bar_js', 20 );
function tmt_progress_bar_js() {{
    if ( ! is_single() ) return;
    echo '<script id="tmt-progress-script">{PROGRESS_JS}</script>';
}}

function tmt_get_css() {{
    return <<<'ENDCSS'
{ARTICLE_CSS}
ENDCSS;
}}
'''

# Escape curly braces inside heredoc for PHP (they're literal in PHP heredoc)
# The heredoc content is the raw CSS — no PHP variable expansion inside it.

print("=" * 60)
print("  TMT Design Fix")
print("=" * 60)

# ── Step 1: Save CSS to file for manual fallback ──────────────────────────────
css_path = Path("tmt-article-styles.css")
css_path.write_text(ARTICLE_CSS, encoding="utf-8")
print(f"\n  CSS saved to: {css_path.resolve()}")

# ── Step 2: Build updated plugin ZIP ─────────────────────────────────────────
plugin_dir = Path("manual-install")
plugin_dir.mkdir(exist_ok=True)

php_path = plugin_dir / "tmt-performance.php"
php_path.write_text(PLUGIN_PHP, encoding="utf-8")

zip_path = plugin_dir / "tmt-performance.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(php_path, "tmt-performance/tmt-performance.php")

print(f"  Plugin ZIP: {zip_path.resolve()}")

# ── Step 3: Try WP REST API CSS injection ────────────────────────────────────
print("\n── Trying REST API CSS injection ────────────────────────")

# Method A: wp/v2/settings custom_css
r = requests.post(
    f"{WP_URL}/wp-json/wp/v2/settings",
    headers=HDR,
    json={"custom_css": ARTICLE_CSS},
    timeout=20
)
if r.ok and "custom_css" in r.json():
    print("  Method A: custom_css via settings — SUCCESS")
    css_injected = True
else:
    print(f"  Method A: settings endpoint — {r.status_code} (expected, trying next)")
    css_injected = False

# Method B: global-styles (block themes)
if not css_injected:
    rg = requests.get(f"{WP_URL}/wp-json/wp/v2/global-styles/themes/daily-bulletin",
                      headers=HDR, timeout=20)
    if rg.ok:
        gs = rg.json()
        gs_id = gs.get("id")
        existing_css = gs.get("settings", {}).get("custom", {}).get("css", "")
        new_css = existing_css + "\n" + ARTICLE_CSS
        rp = requests.post(
            f"{WP_URL}/wp-json/wp/v2/global-styles/{gs_id}",
            headers=HDR,
            json={"settings": {"custom": {"css": new_css}}},
            timeout=20
        )
        if rp.ok:
            print("  Method B: global-styles — SUCCESS")
            css_injected = True
        else:
            print(f"  Method B: global-styles — {rp.status_code}")
    else:
        print(f"  Method B: global-styles not available ({rg.status_code})")

# ── Step 4: Always rebuild plugin (it includes CSS + JS) ─────────────────────
print("\n── Plugin upload ────────────────────────────────────────")
try:
    with open(zip_path, "rb") as f:
        zip_data = f.read()
    upload_hdrs = {
        "Authorization": f"Basic {creds}",
        "Content-Disposition": "attachment; filename=tmt-performance.zip",
        "Content-Type": "application/zip",
    }
    ru = requests.post(
        f"{WP_URL}/wp-json/wp/v2/plugins",
        headers=upload_hdrs,
        data=zip_data,
        params={"overwrite": "true"},
        timeout=30
    )
    if ru.ok or ru.status_code == 201:
        print(f"  Plugin upload via REST — SUCCESS ({ru.status_code})")
        plugin_uploaded = True
    else:
        print(f"  Plugin upload via REST — {ru.status_code} (needs manual update)")
        plugin_uploaded = False
except Exception as e:
    print(f"  Plugin upload error: {e}")
    plugin_uploaded = False

# ── Final instructions ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  SUMMARY & NEXT STEPS")
print("=" * 60)

if css_injected:
    print("  CSS: AUTO-INJECTED via REST API")
else:
    print("  CSS: Needs manual paste (30 seconds):")
    print()
    print("  1. Open:  themobiletimes.com/wp-admin/")
    print("  2. Go to: Appearance → Customize")
    print("  3. Click: Additional CSS (bottom left)")
    print(f"  4. Paste the contents of: {css_path.resolve()}")
    print("  5. Click: Publish")

print()
if plugin_uploaded:
    print("  Plugin: AUTO-UPDATED — reading progress bar is live")
else:
    print("  Plugin (reading progress bar): Needs manual update:")
    print()
    print("  1. Open:  themobiletimes.com/wp-admin/plugins.php")
    print("  2. Deactivate 'TMT Performance & Auto-Unsticky'")
    print("  3. Delete it")
    print(f"  4. Go to: Plugins → Add New → Upload Plugin")
    print(f"  5. Upload: {zip_path.resolve()}")
    print("  6. Activate it")

print("=" * 60)
