<?php /** Generic index. */ get_header(); ?>
<main id="main" class="section"><div class="shell">
<?php if ( have_posts() ) : while ( have_posts() ) : the_post(); ?><article <?php post_class(); ?>><h1><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h1><?php the_excerpt(); ?></article><?php endwhile; the_posts_navigation(); else : ?><p><?php esc_html_e( 'No content found.', 'brightclean' ); ?></p><?php endif; ?>
</div></main><?php get_footer(); ?>
