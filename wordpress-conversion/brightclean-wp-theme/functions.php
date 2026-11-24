<?php
/** BrightClean theme setup and Customizer controls. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function brightclean_setup() {
	load_theme_textdomain( 'brightclean', get_template_directory() . '/languages' );
	add_theme_support( 'title-tag' );
	add_theme_support( 'custom-logo', array( 'height' => 80, 'width' => 260, 'flex-height' => true, 'flex-width' => true ) );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'html5', array( 'search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script' ) );
	register_nav_menus( array( 'primary' => __( 'Primary Menu', 'brightclean' ), 'footer' => __( 'Footer Menu', 'brightclean' ) ) );
}
add_action( 'after_setup_theme', 'brightclean_setup' );

function brightclean_assets() {
	$version = wp_get_theme()->get( 'Version' );
	wp_enqueue_style( 'brightclean-theme', get_stylesheet_uri(), array(), $version );
	wp_enqueue_style( 'brightclean-site', get_theme_file_uri( 'assets/css/styles.css' ), array( 'brightclean-theme' ), $version );
	wp_enqueue_script( 'brightclean-main', get_theme_file_uri( 'assets/js/main.js' ), array(), $version, true );
	if ( get_theme_mod( 'brightclean_chat_enabled', true ) ) {
		wp_enqueue_style( 'brightclean-chat', get_theme_file_uri( 'assets/css/easiio-chatbot-widget.css' ), array(), $version );
		wp_enqueue_script( 'brightclean-chat', get_theme_file_uri( 'assets/js/easiio-chatbot-widget.js' ), array(), $version, true );
	}
}
add_action( 'wp_enqueue_scripts', 'brightclean_assets' );

function brightclean_chat_script_attributes( $tag, $handle, $src ) {
	if ( 'brightclean-chat' !== $handle ) { return $tag; }
	$attributes = array(
		'data-easiio-chatbot' => '',
		'data-site-id' => 'class3-brightclean-san-jose',
		'data-api-base' => get_theme_mod( 'brightclean_chat_api_base', 'http://127.0.0.1:8199' ),
		'data-remote-widget-config' => 'true',
		'data-position' => get_theme_mod( 'brightclean_chat_position', 'bottom-right' ),
		'data-title' => get_theme_mod( 'brightclean_chat_title', 'BrightClean Assistant' ),
		'data-primary-color' => get_theme_mod( 'brightclean_chat_primary_color', '#123d3a' ),
		'data-greeting' => get_theme_mod( 'brightclean_chat_greeting', "Hi! Ask me about BrightClean's demo services, prices, service area, or policies." ),
		'data-launcher-style' => 'bubble', 'data-launcher-size' => 'small', 'data-auto-open' => 'false',
		'data-rag-admin' => 'false', 'data-voice-enabled' => 'false', 'data-voice-input-enabled' => 'false',
	);
	$rendered = '';
	foreach ( $attributes as $name => $value ) { $rendered .= ' ' . esc_attr( $name ) . ( '' === $value ? '' : '="' . esc_attr( $value ) . '"' ); }
	return '<script src="' . esc_url( $src ) . '"' . $rendered . '></script>';
}
add_filter( 'script_loader_tag', 'brightclean_chat_script_attributes', 10, 3 );

function brightclean_phone_href() {
	return 'tel:' . preg_replace( '/[^0-9+]/', '', get_theme_mod( 'brightclean_phone', '(408) 555-0147' ) );
}
function brightclean_sanitize_checkbox( $value ) { return (bool) $value; }
function brightclean_sanitize_position( $value ) { return in_array( $value, array( 'bottom-right', 'bottom-left' ), true ) ? $value : 'bottom-right'; }
function brightclean_sanitize_api_url( $value ) { return esc_url_raw( trim( $value ), array( 'http', 'https' ) ); }

function brightclean_customize_register( $customizer ) {
	$customizer->add_section( 'brightclean_business', array( 'title' => __( 'BrightClean Business', 'brightclean' ), 'priority' => 30 ) );
	$fields = array(
		'brightclean_phone' => array( 'Phone', '(408) 555-0147', 'sanitize_text_field' ),
		'brightclean_email' => array( 'Email', 'hello@example.com', 'sanitize_email' ),
		'brightclean_cta_label' => array( 'Primary CTA label', 'Call for an Estimate', 'sanitize_text_field' ),
	);
	foreach ( $fields as $id => $field ) {
		$customizer->add_setting( $id, array( 'default' => $field[1], 'sanitize_callback' => $field[2], 'transport' => 'refresh' ) );
		$customizer->add_control( $id, array( 'section' => 'brightclean_business', 'label' => __( $field[0], 'brightclean' ), 'type' => 'text' ) );
	}
	$customizer->add_section( 'brightclean_chatbot', array( 'title' => __( 'BrightClean Chatbot', 'brightclean' ), 'priority' => 31 ) );
	$chat = array(
		'brightclean_chat_api_base' => array( 'API base URL', 'http://127.0.0.1:8199', 'brightclean_sanitize_api_url', 'url' ),
		'brightclean_chat_title' => array( 'Widget title', 'BrightClean Assistant', 'sanitize_text_field', 'text' ),
		'brightclean_chat_greeting' => array( 'Greeting', "Hi! Ask me about BrightClean's demo services, prices, service area, or policies.", 'sanitize_textarea_field', 'textarea' ),
		'brightclean_chat_primary_color' => array( 'Primary color', '#123d3a', 'sanitize_hex_color', 'color' ),
	);
	$customizer->add_setting( 'brightclean_chat_enabled', array( 'default' => true, 'sanitize_callback' => 'brightclean_sanitize_checkbox' ) );
	$customizer->add_control( 'brightclean_chat_enabled', array( 'section' => 'brightclean_chatbot', 'label' => __( 'Enable chatbot', 'brightclean' ), 'type' => 'checkbox' ) );
	foreach ( $chat as $id => $field ) {
		$customizer->add_setting( $id, array( 'default' => $field[1], 'sanitize_callback' => $field[2] ) );
		$customizer->add_control( $id, array( 'section' => 'brightclean_chatbot', 'label' => __( $field[0], 'brightclean' ), 'type' => $field[3] ) );
	}
	$customizer->add_setting( 'brightclean_chat_position', array( 'default' => 'bottom-right', 'sanitize_callback' => 'brightclean_sanitize_position' ) );
	$customizer->add_control( 'brightclean_chat_position', array( 'section' => 'brightclean_chatbot', 'label' => __( 'Position', 'brightclean' ), 'type' => 'select', 'choices' => array( 'bottom-right' => 'Bottom right', 'bottom-left' => 'Bottom left' ) ) );
}
add_action( 'customize_register', 'brightclean_customize_register' );

function brightclean_menu_fallback() {
	$items = array( 'services' => 'Services & Pricing', 'process' => 'How It Works', 'proof' => 'Customer Reviews', 'faq' => 'FAQ' );
	echo '<div class="desktop-nav">';
	foreach ( $items as $anchor => $label ) { printf( '<a href="%s">%s</a>', esc_url( home_url( '/#' . $anchor ) ), esc_html( $label ) ); }
	echo '</div>';
}
