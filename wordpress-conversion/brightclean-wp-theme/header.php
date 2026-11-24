<?php /** Site header. */ ?><!doctype html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#123d3a">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<a class="skip-link" href="#main"><?php esc_html_e( 'Skip to main content', 'brightclean' ); ?></a>
<header class="site-header" id="top"><div class="shell nav-wrap">
<?php if ( has_custom_logo() ) : the_custom_logo(); else : ?><a class="brand" href="<?php echo esc_url( home_url( '/' ) ); ?>" aria-label="<?php esc_attr_e( 'BrightClean home', 'brightclean' ); ?>"><span class="brand-mark" aria-hidden="true">B</span><span><?php bloginfo( 'name' ); ?><small>SAN JOSE</small></span></a><?php endif; ?>
<?php wp_nav_menu( array( 'theme_location' => 'primary', 'container' => 'nav', 'container_class' => 'desktop-nav', 'fallback_cb' => 'brightclean_menu_fallback', 'depth' => 1 ) ); ?>
<a class="nav-phone" href="<?php echo esc_attr( brightclean_phone_href() ); ?>"><span>Appointments Available</span><strong><?php echo esc_html( get_theme_mod( 'brightclean_phone', '(408) 555-0147' ) ); ?></strong></a>
<button class="menu-btn" aria-expanded="false" aria-controls="mobile-nav" aria-label="Open menu"><span></span><span></span></button>
</div><nav class="mobile-nav" id="mobile-nav" aria-label="Mobile navigation"><a href="<?php echo esc_url( home_url( '/#services' ) ); ?>">Services &amp; Pricing</a><a href="<?php echo esc_url( home_url( '/#process' ) ); ?>">How It Works</a><a href="<?php echo esc_url( home_url( '/#proof' ) ); ?>">Customer Reviews</a><a href="<?php echo esc_url( home_url( '/#faq' ) ); ?>">FAQ</a><a href="<?php echo esc_attr( brightclean_phone_href() ); ?>">Call to Inquire</a></nav></header>
