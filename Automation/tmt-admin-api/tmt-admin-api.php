<?php
/**
 * Plugin Name: TMT Admin API
 * Description: Full-site REST API for The Mobile Times. Authenticated via secret key.
 *              Handles SEO meta, content, media, terms, options, users, cache, and plugins.
 *              Secret can be overridden in wp-config.php: define('TMT_API_SECRET', 'your-key');
 * Version: 1.0
 * Author: The Mobile Times
 */

if ( ! defined( 'ABSPATH' ) ) exit;

/* ─── Force-enable Application Passwords (disabled by default on some hosts) ── */
add_filter( 'wp_is_application_passwords_available', '__return_true' );

/* ─── TMT Article Styles ──────────────────────────────────────────────────── */
add_action( 'wp_head', function () {
    echo '<style id="tmt-article-styles">
.tmt-highlights{background:#f8f9fa;border-left:3px solid #e63329;padding:16px 20px;margin:1.5rem 0;border-radius:4px}
.tmt-highlights h3,.tmt-data-box h3,.tmt-toc h3{font-size:.85rem;font-weight:700;margin:0 0 10px;text-transform:uppercase;letter-spacing:.05em;color:#e63329}
.tmt-toc{background:#f0f4ff;border:1px solid #d0d8ff;padding:16px 20px;margin:1.5rem 0;border-radius:4px}
.tmt-toc ol{margin:6px 0 0;padding-left:20px}
.tmt-toc a{color:#3b5bdb;text-decoration:none}
.tmt-toc a:hover{text-decoration:underline}
.tmt-data-box{background:#fff8f0;border-left:3px solid #ff6b35;padding:16px 20px;margin:1.5rem 0;border-radius:4px}
.tmt-quote{border-left:4px solid #e63329;background:#fafafa;padding:12px 20px;margin:1.5rem 0;font-style:italic;color:#374151}
.tmt-table-wrap{overflow-x:auto;margin:1.5rem 0;-webkit-overflow-scrolling:touch}
.tmt-table-wrap table{width:100%;border-collapse:collapse;font-size:.9rem}
.tmt-table-wrap th{background:#e63329;color:#fff;padding:9px 12px;text-align:left;font-weight:600}
.tmt-table-wrap td{padding:8px 12px;border-bottom:1px solid #e5e7eb}
.tmt-table-wrap tr:nth-child(even) td{background:#f9fafb}
.tmt-verdict{background:#f0fff4;border-left:4px solid #22c55e;padding:16px 20px;margin:1.5rem 0;border-radius:4px}
.tmt-related{background:#f8f9fa;border-top:2px solid #e5e7eb;padding:16px 20px;margin:2rem 0}
.tmt-related h3{font-size:.85rem;font-weight:700;margin:0 0 10px;text-transform:uppercase;letter-spacing:.05em;color:#6b7280}
.tmt-related ul{margin:0;padding-left:20px}
.tmt-sources{font-size:.82rem;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:8px;margin-top:2rem}
.tmt-body-img{margin:1.5rem 0}.tmt-body-img img{width:100%;height:auto;border-radius:6px;display:block}
.tmt-body-img figcaption{font-size:.8rem;color:#888;padding:4px 0}
</style>' . "\n";
}, 20 );

/* ─── Secret key ──────────────────────────────────────────────────────────── */
// Override in wp-config.php:  define( 'TMT_API_SECRET', 'your-strong-key-here' );
define( 'TMT_KEY', defined( 'TMT_API_SECRET' ) ? TMT_API_SECRET : 'TMT2026xK9mSEO' );

/* ─── Logger ──────────────────────────────────────────────────────────────── */
function tmt_log( string $msg ): void {
    $dir  = WP_CONTENT_DIR . '/tmt-api-logs';
    if ( ! file_exists( $dir ) ) wp_mkdir_p( $dir );
    $file = $dir . '/tmt-api-' . gmdate( 'Y-m-d' ) . '.log';
    $line = '[' . gmdate( 'Y-m-d H:i:s' ) . ' UTC] ' . $msg . PHP_EOL;
    file_put_contents( $file, $line, FILE_APPEND | LOCK_EX );
}

/* ─── Bootstrap ───────────────────────────────────────────────────────────── */
add_action( 'rest_api_init', function () {

    $ns   = 'tmt/v1';
    $open = '__return_true';

    $routes = [
        // health
        'health'             => 'tmt_health',

        // posts / pages
        'post/list'          => 'tmt_post_list',
        'post/get'           => 'tmt_post_get',
        'post/create'        => 'tmt_post_create',
        'post/update'        => 'tmt_post_update',
        'post/delete'        => 'tmt_post_delete',

        // meta (post, page, term)
        'meta/update'        => 'tmt_meta_update',
        'meta/get'           => 'tmt_meta_get',

        // backward-compat aliases for old seo_updater.py
        'update-meta'        => 'tmt_meta_update',
        'update-media'       => 'tmt_media_update',

        // media / images
        'media/list'         => 'tmt_media_list',
        'media/upload'       => 'tmt_media_upload',
        'media/update'       => 'tmt_media_update',

        // terms (categories, tags, custom taxonomies)
        'term/list'          => 'tmt_term_list',
        'term/create'        => 'tmt_term_create',
        'term/update'        => 'tmt_term_update',
        'term/delete'        => 'tmt_term_delete',

        // wordpress options
        'option/get'         => 'tmt_option_get',
        'option/set'         => 'tmt_option_set',

        // users
        'user/list'          => 'tmt_user_list',
        'user/update'        => 'tmt_user_update',

        // cache
        'cache/flush'        => 'tmt_cache_flush',

        // plugins
        'plugin/list'        => 'tmt_plugin_list',
        'plugin/activate'    => 'tmt_plugin_activate',
        'plugin/deactivate'  => 'tmt_plugin_deactivate',

        // site info
        'site/info'          => 'tmt_site_info',

        // views (Light Post Views Counter / Post Views Counter)
        'views/seed'         => 'tmt_views_seed',
    ];

    foreach ( $routes as $path => $callback ) {
        register_rest_route( $ns, '/' . $path, [
            'methods'             => 'POST',
            'callback'            => $callback,
            'permission_callback' => $open,
        ] );
    }
} );


/* ─── Auth helper ─────────────────────────────────────────────────────────── */
function tmt_auth( WP_REST_Request $req ): bool {
    return $req->get_param( 'secret' ) === TMT_KEY;
}
function tmt_no()       { return new WP_Error( 'forbidden',   'Invalid secret.',             [ 'status' => 403 ] ); }
function tmt_bad( $m )  { return new WP_Error( 'bad_request', (string) $m,                   [ 'status' => 400 ] ); }
function tmt_err( $m )  { return new WP_Error( 'server_error',(string) $m,                   [ 'status' => 500 ] ); }


/* ═══════════════════════════════════════════════════════════════════════════
   HEALTH
═══════════════════════════════════════════════════════════════════════════ */
function tmt_health( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();
    tmt_log( 'health check' );
    return [
        'success'    => true,
        'site'       => get_bloginfo( 'url' ),
        'name'       => get_bloginfo( 'name' ),
        'wp_version' => get_bloginfo( 'version' ),
        'php_version'=> PHP_VERSION,
        'time_utc'   => gmdate( 'Y-m-d H:i:s' ),
    ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   POSTS / PAGES
═══════════════════════════════════════════════════════════════════════════ */

function tmt_post_list( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $args = [
        'post_type'      => sanitize_text_field( $req->get_param( 'post_type'   ) ?: 'post' ),
        'post_status'    => sanitize_text_field( $req->get_param( 'post_status' ) ?: 'any' ),
        'posts_per_page' => absint(              $req->get_param( 'per_page'    ) ?: 100 ),
        'paged'          => absint(              $req->get_param( 'page'        ) ?: 1 ),
        'orderby'        => sanitize_text_field( $req->get_param( 'orderby'     ) ?: 'date' ),
        'order'          => sanitize_text_field( $req->get_param( 'order'       ) ?: 'DESC' ),
    ];
    if ( $s  = $req->get_param( 'search'      ) ) $args['s']   = sanitize_text_field( $s );
    if ( $id = absint( $req->get_param( 'author_id' ) ) ) $args['author'] = $id;
    if ( $c  = $req->get_param( 'category_id' ) ) $args['cat'] = absint( $c );

    $q = new WP_Query( $args );

    $posts = array_map( function( $p ) {
        return [
            'id'       => $p->ID,
            'title'    => $p->post_title,
            'slug'     => $p->post_name,
            'status'   => $p->post_status,
            'type'     => $p->post_type,
            'date'     => $p->post_date,
            'modified' => $p->post_modified,
            'excerpt'  => $p->post_excerpt,
            'url'      => get_permalink( $p->ID ),
        ];
    }, $q->posts );

    return [ 'success' => true, 'total' => $q->found_posts, 'posts' => $posts ];
}


function tmt_post_get( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $id = absint( $req->get_param( 'id' ) );
    if ( ! $id ) return tmt_bad( 'Missing id.' );

    $post = get_post( $id );
    if ( ! $post ) return tmt_bad( 'Post not found.' );

    return [
        'success'    => true,
        'id'         => $post->ID,
        'title'      => $post->post_title,
        'slug'       => $post->post_name,
        'content'    => $post->post_content,
        'excerpt'    => $post->post_excerpt,
        'status'     => $post->post_status,
        'type'       => $post->post_type,
        'date'       => $post->post_date,
        'modified'   => $post->post_modified,
        'url'        => get_permalink( $post->ID ),
        'categories' => wp_get_post_categories( $post->ID, [ 'fields' => 'names' ] ),
        'tags'       => wp_get_post_tags( $post->ID, [ 'fields' => 'names' ] ),
        'thumbnail'  => get_the_post_thumbnail_url( $post->ID, 'full' ),
        'meta'       => get_post_meta( $post->ID ),
        'author_id'  => $post->post_author,
    ];
}


function tmt_post_create( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $title = sanitize_text_field( $req->get_param( 'title' ) );
    if ( ! $title ) return tmt_bad( 'Missing title.' );

    $args = [
        'post_title'   => $title,
        'post_content' => wp_kses_post( $req->get_param( 'content' ) ?: '' ),
        'post_excerpt' => sanitize_textarea_field( $req->get_param( 'excerpt' ) ?: '' ),
        'post_status'  => sanitize_text_field( $req->get_param( 'status'    ) ?: 'draft' ),
        'post_type'    => sanitize_text_field( $req->get_param( 'post_type' ) ?: 'post' ),
        'post_author'  => absint( $req->get_param( 'author_id' ) ?: 1 ),
        'post_name'    => sanitize_title( $req->get_param( 'slug' ) ?: $title ),
    ];

    if ( $d = sanitize_text_field( $req->get_param( 'date' ) ) )     $args['post_date']     = $d;
    if ( $d = sanitize_text_field( $req->get_param( 'date_gmt' ) ) ) $args['post_date_gmt'] = $d;

    if ( $cats = $req->get_param( 'categories' ) ) $args['post_category'] = array_map( 'intval', (array) $cats );

    $id = wp_insert_post( $args, true );
    if ( is_wp_error( $id ) ) return tmt_err( $id->get_error_message() );

    // Tags: pass IDs directly so integer tag IDs work (tags_input only accepts names/slugs)
    if ( $tags = $req->get_param( 'tags' ) ) {
        wp_set_post_tags( $id, array_map( 'intval', (array) $tags ), false );
    }

    if ( $thumb = absint( $req->get_param( 'featured_image_id' ) ) ) set_post_thumbnail( $id, $thumb );
    if ( $req->get_param( 'sticky' ) )                               stick_post( $id );

    // Rank Math meta if supplied
    foreach ( [ 'rank_math_title', 'rank_math_description', 'rank_math_focus_keyword' ] as $mk ) {
        if ( $v = $req->get_param( $mk ) ) update_post_meta( $id, $mk, wp_kses_post( $v ) );
    }

    $url = get_permalink( $id );
    tmt_log( "post/create: ID=$id title=$title" );
    return [ 'success' => true, 'id' => $id, 'url' => $url, 'link' => $url ];
}


function tmt_post_update( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $id = absint( $req->get_param( 'id' ) );
    if ( ! $id ) return tmt_bad( 'Missing id.' );

    $args = [ 'ID' => $id ];
    if ( $v = $req->get_param( 'title'   ) ) $args['post_title']   = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'content' ) ) $args['post_content'] = wp_kses_post( $v );
    if ( $v = $req->get_param( 'excerpt' ) ) $args['post_excerpt'] = sanitize_textarea_field( $v );
    if ( $v = $req->get_param( 'status'  ) ) $args['post_status']  = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'slug'    ) ) $args['post_name']    = sanitize_title( $v );
    if ( $v = $req->get_param( 'date'    ) ) $args['post_date']    = sanitize_text_field( $v );
    if ( $cats = $req->get_param( 'categories' ) ) $args['post_category'] = array_map( 'intval', (array) $cats );
    if ( $tags = $req->get_param( 'tags'       ) ) $args['tags_input']    = (array) $tags;

    $result = wp_update_post( $args, true );
    if ( is_wp_error( $result ) ) return tmt_err( $result->get_error_message() );

    // Featured image
    $thumb = $req->get_param( 'featured_image_id' );
    if ( $thumb !== null ) {
        if ( $thumb === 'remove' || $thumb === 0 ) delete_post_thumbnail( $id );
        elseif ( absint( $thumb ) )               set_post_thumbnail( $id, absint( $thumb ) );
    }

    // Rank Math meta if supplied
    foreach ( [ 'rank_math_title', 'rank_math_description', 'rank_math_focus_keyword',
                'rank_math_robots', 'rank_math_canonical_url' ] as $mk ) {
        if ( ( $v = $req->get_param( $mk ) ) !== null ) update_post_meta( $id, $mk, wp_kses_post( $v ) );
    }

    tmt_log( "post/update: ID=$id" );
    return [ 'success' => true, 'id' => $id, 'url' => get_permalink( $id ) ];
}


function tmt_post_delete( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $id    = absint( $req->get_param( 'id' ) );
    $force = (bool) $req->get_param( 'force' ); // true = bypass trash
    if ( ! $id ) return tmt_bad( 'Missing id.' );

    $result = wp_delete_post( $id, $force );
    if ( ! $result ) return tmt_err( 'Could not delete post.' );

    tmt_log( "post/delete: ID=$id force=$force" );
    return [ 'success' => true, 'id' => $id, 'permanent' => $force ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   META  (works for posts, pages, AND terms)
═══════════════════════════════════════════════════════════════════════════ */

function tmt_meta_update( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    // Support both new field names and old seo_updater.py field names
    $object_id   = absint( $req->get_param( 'objectID'   ) ?: $req->get_param( 'object_id'   ) );
    $object_type = sanitize_text_field( $req->get_param( 'objectType' ) ?: $req->get_param( 'object_type' ) ?: 'post' );
    $meta        = $req->get_param( 'meta' );

    if ( ! $object_id || ! is_array( $meta ) ) return tmt_bad( 'Missing objectID or meta array.' );

    $updated = [];
    foreach ( $meta as $key => $value ) {
        $key   = sanitize_key( $key );
        $value = wp_kses_post( $value );
        if ( $object_type === 'term' ) update_term_meta( $object_id, $key, $value );
        else                           update_post_meta( $object_id, $key, $value );
        $updated[] = $key;
    }

    tmt_log( "meta/update: {$object_type} {$object_id} keys=" . implode( ',', $updated ) );
    return [ 'success' => true, 'object_id' => $object_id, 'type' => $object_type, 'updated' => $updated ];
}


function tmt_meta_get( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $object_id   = absint( $req->get_param( 'objectID' ) );
    $object_type = sanitize_text_field( $req->get_param( 'objectType' ) ?: 'post' );
    $key         = sanitize_key( $req->get_param( 'key' ) ?: '' );

    if ( ! $object_id ) return tmt_bad( 'Missing objectID.' );

    if ( $object_type === 'term' ) $meta = $key ? get_term_meta( $object_id, $key ) : get_term_meta( $object_id );
    else                            $meta = $key ? get_post_meta( $object_id, $key ) : get_post_meta( $object_id );

    return [ 'success' => true, 'object_id' => $object_id, 'meta' => $meta ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   MEDIA
═══════════════════════════════════════════════════════════════════════════ */

function tmt_media_list( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $q = new WP_Query( [
        'post_type'      => 'attachment',
        'post_status'    => 'inherit',
        'posts_per_page' => absint( $req->get_param( 'per_page'  ) ?: 100 ),
        'paged'          => absint( $req->get_param( 'page'      ) ?: 1 ),
        'post_mime_type' => sanitize_text_field( $req->get_param( 'mime_type' ) ?: '' ),
    ] );

    $media = array_map( function( $p ) {
        return [
            'id'      => $p->ID,
            'title'   => $p->post_title,
            'url'     => wp_get_attachment_url( $p->ID ),
            'alt'     => get_post_meta( $p->ID, '_wp_attachment_image_alt', true ),
            'caption' => $p->post_excerpt,
            'mime'    => $p->post_mime_type,
            'date'    => $p->post_date,
        ];
    }, $q->posts );

    return [ 'success' => true, 'total' => $q->found_posts, 'media' => $media ];
}


function tmt_media_upload( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $b64      = $req->get_param( 'image_base64' );
    $filename = sanitize_file_name( $req->get_param( 'filename' ) ?: 'image.jpg' );
    if ( ! $b64 ) return tmt_bad( 'Missing image_base64.' );

    $image_data = base64_decode( $b64 );
    if ( ! $image_data ) return tmt_bad( 'Invalid base64 data.' );

    require_once ABSPATH . 'wp-admin/includes/image.php';
    require_once ABSPATH . 'wp-admin/includes/file.php';
    require_once ABSPATH . 'wp-admin/includes/media.php';

    $tmp = wp_tempnam( $filename );
    file_put_contents( $tmp, $image_data );

    $attachment_id = media_handle_sideload( [
        'name'     => $filename,
        'tmp_name' => $tmp,
        'type'     => 'image/jpeg',
        'size'     => strlen( $image_data ),
        'error'    => UPLOAD_ERR_OK,
    ], 0 );

    @unlink( $tmp );

    if ( is_wp_error( $attachment_id ) ) return tmt_err( $attachment_id->get_error_message() );

    $alt   = sanitize_text_field( $req->get_param( 'alt_text' ) ?: '' );
    $title = sanitize_text_field( $req->get_param( 'title'    ) ?: $alt );

    wp_update_post( [ 'ID' => $attachment_id, 'post_title' => $title, 'post_excerpt' => '© The Mobile Times' ] );
    update_post_meta( $attachment_id, '_wp_attachment_image_alt', $alt );

    $src = wp_get_attachment_url( $attachment_id );
    tmt_log( "media/upload: ID=$attachment_id file=$filename" );
    return [ 'success' => true, 'id' => $attachment_id, 'source_url' => $src, 'link' => $src ];
}


function tmt_media_update( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    // Support both 'media_id' (new) and 'media_id' (old seo_updater.py param)
    $media_id = absint( $req->get_param( 'media_id' ) );
    if ( ! $media_id ) return tmt_bad( 'Missing media_id.' );

    $args = [ 'ID' => $media_id ];
    if ( $v = $req->get_param( 'title'   ) ) $args['post_title']   = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'caption' ) ) $args['post_excerpt'] = sanitize_text_field( $v );
    if ( count( $args ) > 1 ) wp_update_post( $args );

    if ( $v = $req->get_param( 'alt_text' ) ) update_post_meta( $media_id, '_wp_attachment_image_alt', sanitize_text_field( $v ) );

    tmt_log( "media/update: ID=$media_id" );
    return [ 'success' => true, 'media_id' => $media_id ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   TERMS  (categories, tags, or any custom taxonomy)
═══════════════════════════════════════════════════════════════════════════ */

function tmt_term_list( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $taxonomy = sanitize_text_field( $req->get_param( 'taxonomy' ) ?: 'category' );
    $terms    = get_terms( [ 'taxonomy' => $taxonomy, 'hide_empty' => false, 'number' => 500 ] );
    if ( is_wp_error( $terms ) ) return tmt_err( $terms->get_error_message() );

    return [
        'success' => true,
        'terms'   => array_map( function( $t ) {
            return [
                'id'          => $t->term_id,
                'name'        => $t->name,
                'slug'        => $t->slug,
                'description' => $t->description,
                'count'       => $t->count,
                'parent'      => $t->parent,
                'url'         => get_term_link( $t ),
            ];
        }, $terms ),
    ];
}


function tmt_term_create( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $name     = sanitize_text_field( $req->get_param( 'name'     ) );
    $taxonomy = sanitize_text_field( $req->get_param( 'taxonomy' ) ?: 'category' );
    if ( ! $name ) return tmt_bad( 'Missing name.' );

    $args = [ 'slug' => sanitize_title( $req->get_param( 'slug' ) ?: $name ) ];
    if ( $v = $req->get_param( 'description' ) ) $args['description'] = sanitize_textarea_field( $v );
    if ( $p = absint( $req->get_param( 'parent_id' ) ) ) $args['parent'] = $p;

    $result = wp_insert_term( $name, $taxonomy, $args );
    if ( is_wp_error( $result ) ) return tmt_err( $result->get_error_message() );

    tmt_log( "term/create: taxonomy=$taxonomy name=$name id={$result['term_id']}" );
    return [ 'success' => true, 'term_id' => $result['term_id'] ];
}


function tmt_term_update( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $term_id  = absint( $req->get_param( 'term_id'  ) );
    $taxonomy = sanitize_text_field( $req->get_param( 'taxonomy' ) ?: 'category' );
    if ( ! $term_id ) return tmt_bad( 'Missing term_id.' );

    $args = [];
    if ( $v = $req->get_param( 'name'        ) ) $args['name']        = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'slug'        ) ) $args['slug']        = sanitize_title( $v );
    if ( $v = $req->get_param( 'description' ) ) $args['description'] = sanitize_textarea_field( $v );

    $result = wp_update_term( $term_id, $taxonomy, $args );
    if ( is_wp_error( $result ) ) return tmt_err( $result->get_error_message() );

    tmt_log( "term/update: ID=$term_id" );
    return [ 'success' => true, 'term_id' => $term_id ];
}


function tmt_term_delete( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $term_id  = absint( $req->get_param( 'term_id'  ) );
    $taxonomy = sanitize_text_field( $req->get_param( 'taxonomy' ) ?: 'category' );
    if ( ! $term_id ) return tmt_bad( 'Missing term_id.' );

    $result = wp_delete_term( $term_id, $taxonomy );
    if ( is_wp_error( $result ) ) return tmt_err( $result->get_error_message() );

    tmt_log( "term/delete: ID=$term_id" );
    return [ 'success' => true, 'term_id' => $term_id, 'deleted' => (bool) $result ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   OPTIONS
═══════════════════════════════════════════════════════════════════════════ */

function tmt_option_get( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $name = sanitize_text_field( $req->get_param( 'name' ) );
    if ( ! $name ) return tmt_bad( 'Missing name.' );
    return [ 'success' => true, 'name' => $name, 'value' => get_option( $name ) ];
}


function tmt_option_set( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $name  = sanitize_text_field( $req->get_param( 'name'  ) );
    $value = $req->get_param( 'value' );
    if ( ! $name ) return tmt_bad( 'Missing name.' );

    // Hard-block the options that would break the site if changed accidentally
    $blocked = [ 'siteurl', 'home', 'blogname', 'admin_email' ];
    if ( in_array( $name, $blocked, true ) ) {
        return new WP_Error( 'blocked', "Option '$name' is protected. Change it via WP Admin.", [ 'status' => 403 ] );
    }

    update_option( $name, $value );
    tmt_log( "option/set: $name" );
    return [ 'success' => true, 'name' => $name ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   USERS
═══════════════════════════════════════════════════════════════════════════ */

function tmt_user_list( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $users = get_users( [
        'fields' => [ 'ID', 'display_name', 'user_email', 'user_login', 'user_registered' ],
        'number' => 100,
    ] );

    return [
        'success' => true,
        'users'   => array_map( function( $u ) {
            return [
                'id'           => $u->ID,
                'login'        => $u->user_login,
                'name'         => $u->display_name,
                'email'        => $u->user_email,
                'registered'   => $u->user_registered,
                'roles'        => get_userdata( $u->ID )->roles,
                'profile_url'  => get_author_posts_url( $u->ID ),
            ];
        }, $users ),
    ];
}


function tmt_user_update( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $id = absint( $req->get_param( 'id' ) );
    if ( ! $id ) return tmt_bad( 'Missing id.' );

    $args = [ 'ID' => $id ];
    if ( $v = $req->get_param( 'display_name'  ) ) $args['display_name']  = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'first_name'    ) ) $args['first_name']    = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'last_name'     ) ) $args['last_name']     = sanitize_text_field( $v );
    if ( $v = $req->get_param( 'description'   ) ) $args['description']   = sanitize_textarea_field( $v );
    if ( $v = $req->get_param( 'url'           ) ) $args['user_url']      = esc_url_raw( $v );

    $result = wp_update_user( $args );
    if ( is_wp_error( $result ) ) return tmt_err( $result->get_error_message() );

    // Social / profile meta
    $social = [ 'twitter', 'facebook', 'linkedin', 'instagram', 'youtube' ];
    foreach ( $social as $field ) {
        if ( ( $v = $req->get_param( $field ) ) !== null ) {
            update_user_meta( $id, $field, esc_url_raw( $v ) );
        }
    }

    tmt_log( "user/update: ID=$id" );
    return [ 'success' => true, 'user_id' => $id ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   CACHE
═══════════════════════════════════════════════════════════════════════════ */

function tmt_cache_flush( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $flushed = [];

    // WordPress object cache
    wp_cache_flush();
    $flushed[] = 'object_cache';

    // Transients
    global $wpdb;
    $wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_%'" );
    $wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE '_site_transient_%'" );
    $flushed[] = 'transients';

    // LiteSpeed Cache
    if ( class_exists( 'LiteSpeed_Cache_API' ) ) {
        LiteSpeed_Cache_API::purge_all();
        $flushed[] = 'litespeed';
    } elseif ( class_exists( 'LiteSpeed\Purge' ) ) {
        \LiteSpeed\Purge::purge_all();
        $flushed[] = 'litespeed';
    }

    // WP Super Cache
    if ( function_exists( 'wp_cache_clear_cache' ) ) {
        wp_cache_clear_cache();
        $flushed[] = 'wp_super_cache';
    }

    // W3 Total Cache
    if ( function_exists( 'w3tc_flush_all' ) ) {
        w3tc_flush_all();
        $flushed[] = 'w3tc';
    }

    // Rank Math sitemap cache
    if ( class_exists( 'RankMath\Sitemap\Cache' ) ) {
        \RankMath\Sitemap\Cache::invalidate_storage();
        $flushed[] = 'rankmath_sitemap';
    }

    // Autoptimize
    if ( class_exists( 'autoptimizeCache' ) ) {
        autoptimizeCache::clearall();
        $flushed[] = 'autoptimize';
    }

    tmt_log( 'cache/flush: ' . implode( ', ', $flushed ) );
    return [ 'success' => true, 'flushed' => $flushed ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   PLUGINS
═══════════════════════════════════════════════════════════════════════════ */

function tmt_plugin_list( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    if ( ! function_exists( 'get_plugins' ) ) require_once ABSPATH . 'wp-admin/includes/plugin.php';
    $all_plugins = get_plugins();
    $active      = get_option( 'active_plugins', [] );

    $list = [];
    foreach ( $all_plugins as $file => $data ) {
        $list[] = [
            'file'        => $file,
            'name'        => $data['Name'],
            'version'     => $data['Version'],
            'description' => $data['Description'],
            'active'      => in_array( $file, $active, true ),
        ];
    }
    return [ 'success' => true, 'plugins' => $list ];
}


function tmt_plugin_activate( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $file = sanitize_text_field( $req->get_param( 'file' ) );
    if ( ! $file ) return tmt_bad( 'Missing file (e.g. "akismet/akismet.php").' );

    if ( ! function_exists( 'activate_plugin' ) ) require_once ABSPATH . 'wp-admin/includes/plugin.php';
    $result = activate_plugin( $file );
    if ( is_wp_error( $result ) ) return tmt_err( $result->get_error_message() );

    tmt_log( "plugin/activate: $file" );
    return [ 'success' => true, 'file' => $file ];
}


function tmt_plugin_deactivate( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    $file = sanitize_text_field( $req->get_param( 'file' ) );
    if ( ! $file ) return tmt_bad( 'Missing file.' );

    if ( ! function_exists( 'deactivate_plugins' ) ) require_once ABSPATH . 'wp-admin/includes/plugin.php';
    deactivate_plugins( $file );

    tmt_log( "plugin/deactivate: $file" );
    return [ 'success' => true, 'file' => $file ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   SITE INFO
═══════════════════════════════════════════════════════════════════════════ */

function tmt_site_info( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    if ( ! function_exists( 'get_plugins' ) ) require_once ABSPATH . 'wp-admin/includes/plugin.php';
    $all_plugins = get_plugins();
    $active      = get_option( 'active_plugins', [] );
    $active_names = array_values( array_map(
        fn( $f ) => $all_plugins[ $f ]['Name'] ?? $f,
        $active
    ) );

    return [
        'success'         => true,
        'url'             => get_bloginfo( 'url' ),
        'name'            => get_bloginfo( 'name' ),
        'description'     => get_bloginfo( 'description' ),
        'wp_version'      => get_bloginfo( 'version' ),
        'php_version'     => PHP_VERSION,
        'language'        => get_bloginfo( 'language' ),
        'theme'           => wp_get_theme()->get( 'Name' ),
        'theme_version'   => wp_get_theme()->get( 'Version' ),
        'active_plugins'  => $active_names,
        'total_plugins'   => count( $all_plugins ),
        'post_counts'     => (array) wp_count_posts(),
        'page_counts'     => (array) wp_count_posts( 'page' ),
        'user_count'      => (array) count_users(),
        'time_utc'        => gmdate( 'Y-m-d H:i:s' ),
    ];
}


/* ═══════════════════════════════════════════════════════════════════════════
   VIEWS  (Light Views Counter — custom table wp_lvc_post_views)
═══════════════════════════════════════════════════════════════════════════ */

function tmt_lvc_set_views( int $post_id, int $count ): bool {
    global $wpdb;
    $table = $wpdb->prefix . 'lvc_post_views';
    $result = $wpdb->query( $wpdb->prepare(
        "INSERT INTO `$table` (post_id, view_count, last_updated)
         VALUES (%d, %d, NOW())
         ON DUPLICATE KEY UPDATE view_count = %d, last_updated = NOW()",
        $post_id, $count, $count
    ) );
    return $result !== false;
}

function tmt_views_seed( WP_REST_Request $req ) {
    if ( ! tmt_auth( $req ) ) return tmt_no();

    global $wpdb;
    $table = $wpdb->prefix . 'lvc_post_views';
    $bulk  = (bool) $req->get_param( 'bulk' );
    $force = (bool) $req->get_param( 'force' );

    if ( $bulk ) {
        $posts = get_posts( [
            'post_type'      => 'post',
            'post_status'    => 'publish',
            'posts_per_page' => -1,
            'fields'         => 'ids',
        ] );
        $seeded = 0;
        foreach ( $posts as $id ) {
            if ( ! $force ) {
                $existing = $wpdb->get_var( $wpdb->prepare(
                    "SELECT view_count FROM `$table` WHERE post_id = %d", $id
                ) );
                if ( $existing !== null ) continue;
            }
            tmt_lvc_set_views( (int) $id, rand( 300, 2000 ) );
            $seeded++;
        }
        tmt_log( "views/seed bulk: seeded=$seeded total=" . count( $posts ) );
        return [ 'success' => true, 'seeded' => $seeded, 'total' => count( $posts ) ];
    }

    $post_id = absint( $req->get_param( 'post_id' ) );
    if ( ! $post_id ) return tmt_bad( 'Missing post_id (or pass bulk=true to seed all posts).' );

    $count = absint( $req->get_param( 'count' ) ?: rand( 300, 2000 ) );
    tmt_lvc_set_views( $post_id, $count );
    tmt_log( "views/seed: ID=$post_id count=$count" );
    return [ 'success' => true, 'post_id' => $post_id, 'count' => $count ];
}
