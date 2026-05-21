<?php
/**
 * Plugin Name: TMT Performance & Auto-Unsticky
 * Plugin URI:  https://themobiletimes.com
 * Description: Removes emoji scripts, disables XML-RPC, auto-unsticky posts >24h, injects article styles.
 * Version:     1.7
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
function tmt_remove_ver( $src ) {
    if ( strpos( $src, 'ver=' ) )
        $src = remove_query_arg( 'ver', $src );
    return $src;
}

/* ── Auto-unsticky posts older than 24 hours ── */
add_action( 'wp_scheduled_delete', 'tmt_auto_unsticky' );
add_action( 'init',                'tmt_auto_unsticky' );
function tmt_auto_unsticky() {
    $sticky = get_option( 'sticky_posts', [] );
    if ( empty( $sticky ) ) return;
    foreach ( $sticky as $id ) {
        $post = get_post( $id );
        if ( ! $post ) continue;
        $age = time() - strtotime( $post->post_date_gmt . ' UTC' );
        if ( $age > 86400 ) {
            unstick_post( $id );
        }
    }
}

/* ── Clean category archive titles (removes "Category: " prefix) ── */
add_filter( 'get_the_archive_title', 'tmt_clean_archive_title' );
function tmt_clean_archive_title( $title ) {
    if ( is_category() ) return single_cat_title( '', false );
    if ( is_tag() )      return single_tag_title( '', false );
    if ( is_tax() )      return single_term_title( '', false );
    return $title;
}

/* ── Show category description on archive pages ── */
add_action( 'template_redirect', 'tmt_inject_category_description' );
function tmt_inject_category_description() {
    if ( ! is_category() && ! is_tag() && ! is_tax() ) return;
    $desc = term_description();
    if ( empty( trim( strip_tags( $desc ) ) ) ) return;
    add_action( 'loop_start', function() use ( $desc ) {
        static $fired = false;
        if ( $fired ) return;
        $fired = true;
        echo '<div class="tmt-category-desc">' . wp_kses_post( $desc ) . '</div>';
    });
}

/* ── Exclude Elementor + jQuery from LiteSpeed JS deferral ── */
add_filter( 'litespeed_optm_js_defer_exc', 'tmt_ls_defer_excludes' );
function tmt_ls_defer_excludes( $excludes ) {
    $excludes[] = 'elementor';
    $excludes[] = 'jquery';
    $excludes[] = '/wp-includes/js/jquery/jquery';
    return $excludes;
}

/* ── Preconnect hints for faster resource loading ── */
add_action( 'wp_head', 'tmt_preconnect_hints', 1 );
function tmt_preconnect_hints() {
    echo '<link rel="preconnect" href="https://fonts.googleapis.com">' . "\n";
    echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' . "\n";
    echo '<link rel="preconnect" href="https://www.googletagmanager.com">' . "\n";
    echo '<link rel="dns-prefetch" href="//fonts.googleapis.com">' . "\n";
    echo '<link rel="dns-prefetch" href="//www.googletagmanager.com">' . "\n";
}

/* ── Organization / Entity schema (homepage only — Rank Math handles per-post) ── */
add_action( 'wp_head', 'tmt_organization_schema', 2 );
function tmt_organization_schema() {
    if ( ! is_front_page() ) return;
    $schema = [
        '@context'            => 'https://schema.org',
        '@type'               => 'NewsMediaOrganization',
        '@id'                 => 'https://themobiletimes.com/#organization',
        'name'                => 'The Mobile Times',
        'alternateName'       => [ 'TMT', 'TheMobileTimes' ],
        'url'                 => 'https://themobiletimes.com',
        'logo'                => [
            '@type'   => 'ImageObject',
            'url'     => 'https://themobiletimes.com/wp-content/uploads/circle-logo.png',
            'width'   => 400,
            'height'  => 400,
        ],
        'sameAs'              => [
            'https://twitter.com/themobiletimes',
            'https://www.linkedin.com/company/the-mobile-times',
            'https://www.facebook.com/themobiletimes',
        ],
        'description'         => 'The Mobile Times is India\'s leading telecom, 5G, and technology news publication. We cover TRAI regulations, Jio, Airtel, BSNL, smartphone launches, cybersecurity, AI, and IoT developments affecting the Indian market.',
        'foundingDate'        => '2024',
        'areaServed'          => [ 'IN' ],
        'inLanguage'          => 'en-IN',
        'publishingPrinciples'=> 'https://themobiletimes.com/about/',
        'masthead'            => 'https://themobiletimes.com/about/',
        'knowsAbout'          => [
            '5G technology', 'Indian telecom industry', 'TRAI regulations',
            'Jio', 'Airtel', 'BSNL', 'smartphones', 'cybersecurity', 'AI in India',
            'OTT streaming', 'IoT', 'electric vehicles', 'satellite internet',
        ],
    ];
    echo '<script type="application/ld+json">' . wp_json_encode( $schema ) . '</script>' . "\n";
}

/* ── fetchpriority=high on LCP image (first post thumbnail) ── */
add_filter( 'wp_get_attachment_image_attributes', 'tmt_lcp_fetchpriority', 10, 3 );
function tmt_lcp_fetchpriority( $attr, $attachment, $size ) {
    static $done = false;
    if ( ! $done && ( is_front_page() || is_home() || is_single() ) ) {
        $attr['fetchpriority'] = 'high';
        if ( isset( $attr['loading'] ) ) {
            unset( $attr['loading'] );
        }
        $done = true;
    }
    return $attr;
}

/* ── Author archive bio card ── */
add_action( 'loop_start', 'tmt_author_bio_card' );
function tmt_author_bio_card() {
    if ( ! is_author() ) return;
    static $done = false;
    if ( $done ) return;
    $done = true;

    $author     = get_queried_object();
    $name       = esc_html( $author->display_name );
    $bio        = esc_html( $author->description );
    $avatar_url = esc_url( get_avatar_url( $author->ID, [ 'size' => 120 ] ) );
    $post_count = (int) count_user_posts( $author->ID );
    $twitter    = esc_url( 'https://x.com/themobile_times' );
    $linkedin   = esc_url( 'https://www.linkedin.com/company/themobiletimes' );

    echo <<<HTML
<div class="tmt-author-card">
  <img class="tmt-author-avatar" src="{$avatar_url}" alt="{$name}" width="100" height="100">
  <div class="tmt-author-info">
    <h1 class="tmt-author-name">{$name}</h1>
    <p class="tmt-author-role">Editor-in-Chief &mdash; The Mobile Times</p>
    <p class="tmt-author-bio">{$bio}</p>
    <div class="tmt-author-meta">
      <span class="tmt-author-count">{$post_count} articles published</span>
      <span class="tmt-author-socials">
        <a href="{$twitter}" target="_blank" rel="noopener">X / Twitter</a>
        &nbsp;&middot;&nbsp;
        <a href="{$linkedin}" target="_blank" rel="noopener">LinkedIn</a>
      </span>
    </div>
  </div>
</div>
<h2 class="tmt-author-posts-heading">Articles by {$name}</h2>
HTML;
}

/* ── Inject article CSS ── */
add_action( 'wp_head', 'tmt_article_css', 20 );
function tmt_article_css() {
    echo '<style id="tmt-design-system">' . tmt_get_css() . '</style>';
}

/* ── Inject reading progress bar JS (single posts only) ── */
add_action( 'wp_footer', 'tmt_progress_bar_js', 20 );
function tmt_progress_bar_js() {
    if ( ! is_single() ) return;
    echo <<<'ENDJS'
<script id="tmt-progress-script">
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
</script>
ENDJS;
}

function tmt_get_css() {
    return <<<'ENDCSS'

/* ═══════════════════════════════════════════════════════════════
   THE MOBILE TIMES — Article Design System
   Last updated: 2026-05
═══════════════════════════════════════════════════════════════ */

/* ── Author archive bio card ── */
.tmt-author-card {
  display: flex; gap: 28px; align-items: flex-start;
  background: #fff; border: 1px solid #dde2ec;
  border-top: 4px solid #cc0000;
  border-radius: 0 0 10px 10px;
  padding: 32px 36px; margin: 0 0 40px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
}
.tmt-author-avatar {
  width: 100px; height: 100px; border-radius: 50%;
  object-fit: cover; flex-shrink: 0;
  border: 3px solid #cc0000;
}
.tmt-author-info { flex: 1; }
.tmt-author-name {
  font-size: 26px; font-weight: 800; color: #111;
  margin: 0 0 4px; line-height: 1.2;
}
.tmt-author-role {
  font-size: 13px; font-weight: 600; color: #cc0000;
  text-transform: uppercase; letter-spacing: .5px;
  margin: 0 0 14px;
}
.tmt-author-bio {
  font-size: 15px; line-height: 1.7; color: #444;
  margin: 0 0 16px;
}
.tmt-author-meta {
  display: flex; gap: 20px; align-items: center;
  flex-wrap: wrap;
}
.tmt-author-count {
  font-size: 12px; font-weight: 700; color: #1a3a8f;
  background: #eef2ff; padding: 4px 10px; border-radius: 20px;
}
.tmt-author-socials a {
  font-size: 13px; font-weight: 600; color: #1a3a8f;
  text-decoration: none;
}
.tmt-author-socials a:hover { color: #cc0000; }
.tmt-author-posts-heading {
  font-size: 18px; font-weight: 800; color: #111;
  border-bottom: 2px solid #cc0000;
  padding-bottom: 10px; margin: 0 0 24px;
}
@media (max-width: 640px) {
  .tmt-author-card { flex-direction: column; gap: 16px; padding: 20px; }
  .tmt-author-avatar { width: 72px; height: 72px; }
}

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

/* ─────────────────────────────────────────────────────────────
   RELATED ARTICLES
───────────────────────────────────────────────────────────── */
.tmt-related {
  background: #f4f6fb;
  border: 1px solid #dde2ec;
  border-left: 4px solid #cc0000;
  border-radius: 0 8px 8px 0;
  padding: 18px 24px;
  margin: 36px 0 20px;
}
.tmt-related h3 {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #cc0000;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ccc;
}
.tmt-related ul {
  margin: 0; padding: 0; list-style: none;
}
.tmt-related ul li {
  padding: 6px 0 6px 18px;
  position: relative;
  font-size: 14px;
  border-bottom: 1px solid #e8ecf4;
}
.tmt-related ul li:last-child { border-bottom: none; }
.tmt-related ul li::before {
  content: "→"; position: absolute; left: 0;
  color: #cc0000; font-weight: 800;
}
.tmt-related ul li a {
  color: #1a3a8f; text-decoration: none; font-weight: 500;
}
.tmt-related ul li a:hover { color: #cc0000; }

/* ── Category description box ── */
.tmt-category-desc {
  background: #f4f6fb;
  border-left: 4px solid #cc0000;
  border-radius: 0 6px 6px 0;
  padding: 14px 20px;
  margin: 0 0 28px;
  font-size: 14.5px;
  line-height: 1.65;
  color: #444;
}

ENDCSS;
}
