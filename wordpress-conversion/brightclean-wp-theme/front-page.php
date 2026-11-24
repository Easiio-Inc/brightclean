<?php
/** Front page. */
get_header();
?>
<main id="main">
  <section class="hero">
    <div class="shell hero-grid">
      <div class="hero-copy">
        <div class="eyebrow"><span class="live-dot"></span> San Jose, CA · Demo availability shown</div>
        <h1>Come home to clean.<br><em>We make it simple.</em></h1>
        <p class="hero-lead">Friendly home-cleaning professionals, transparent demo pricing, and a simple inquiry process for San Jose households.</p>
        <div class="hero-actions"><a class="btn btn-primary" href="<?php echo esc_attr( brightclean_phone_href() ); ?>"><?php echo esc_html( get_theme_mod( 'brightclean_cta_label', 'Call for an Estimate' ) ); ?> <span>→</span></a><a class="text-link" href="<?php echo esc_url( home_url( '/#services' ) ); ?>">View Demo Pricing</a></div>
        <div class="micro-proof"><span>✓ Clear demo pricing</span><span>✓ Supplies included</span><span>✓ Satisfaction follow-up</span></div>
      </div>
      <div class="hero-visual">
        <img src="<?php echo esc_url( get_theme_file_uri( 'assets/images/brightclean-hero-clean.jpg' ) ); ?>" alt="Professional cleaner providing home cleaning in a bright modern living room" width="1200" height="675">
        <div class="availability-card"><span class="avatar">M</span><div><small>Sample nearby cleaner</small><strong>Maria · 4.9 ★</strong></div><span class="arrival">Demo ETA</span></div>
      </div>
    </div>
    <div class="shell stats" aria-label="Demo service data">
      <div><strong>2,400<sup>+</sup></strong><span>Sample completed jobs</span></div><div><strong>4.9<sup>★</sup></strong><span>Sample rating</span></div><div><strong>60<sup>min</sup></strong><span>Sample response</span></div><div><strong>98<sup>%</sup></strong><span>Sample on-time rate</span></div>
    </div>
  </section>

  <section class="intent section">
    <div class="shell split-heading"><div><span class="section-kicker">Designed Around Your Needs</span><h2>Cleaning help for the moments<br><strong>that matter most.</strong></h2></div><p>Guests arriving, a move-out deadline, or a busy week—choose the cleaning option that matches your situation.</p></div>
    <div class="shell moment-grid">
      <article class="moment-card featured"><span class="moment-no">01</span><div class="moment-icon">⌁</div><h3>Guests are coming</h3><p>Refresh the living room, kitchen, and bathrooms before your guests arrive.</p><a href="<?php echo esc_attr( brightclean_phone_href() ); ?>">Ask about availability →</a></article>
      <article class="moment-card"><span class="moment-no">02</span><div class="moment-icon">□</div><h3>Move-in / Move-out</h3><p>A more detailed clean for empty homes, apartments, and rental transitions.</p><a href="<?php echo esc_url( home_url( '/#services' ) ); ?>">View deep cleaning →</a></article>
      <article class="moment-card"><span class="moment-no">03</span><div class="moment-icon">✦</div><h3>Keep it clean every week</h3><p>Recurring service helps keep routine cleaning off your weekly schedule.</p><a href="<?php echo esc_url( home_url( '/#services' ) ); ?>">View recurring plans →</a></article>
    </div>
  </section>

  <section class="services section" id="services">
    <div class="shell section-head"><div><span class="section-kicker">Transparent Demo Pricing</span><h2>Choose the service that fits your home</h2></div><p>These prices are fictional classroom examples. Verify real rates, service areas, and availability before publishing.</p></div>
    <div class="shell pricing-grid">
      <article class="price-card"><div class="price-top"><span>Standard Cleaning</span><b>Popular</b></div><h3>A reliable routine refresh</h3><p class="price"><small>$</small>45 <span>/ hour</span></p><p class="minimum">3-hour demo minimum · Basic supplies included</p><ul><li>Vacuuming and floor care</li><li>Kitchen counters and stovetop</li><li>Bathroom cleaning</li><li>Surface dusting</li></ul><a class="btn btn-dark" href="<?php echo esc_attr( brightclean_phone_href() ); ?>">Ask About Standard Cleaning</a></article>
      <article class="price-card popular"><div class="popular-tag">Demo Favorite</div><div class="price-top"><span>Deep Cleaning</span></div><h3>Extra attention for built-up dirt</h3><p class="price"><small>$</small>65 <span>/ hour</span></p><p class="minimum">4-hour demo minimum · Specialty supplies included</p><ul><li>Includes standard-cleaning tasks</li><li>Detailed kitchen cleaning</li><li>Bathroom buildup and edges</li><li>Baseboards and overlooked areas</li></ul><a class="btn btn-primary" href="<?php echo esc_attr( brightclean_phone_href() ); ?>">Ask About Deep Cleaning</a></article>
      <article class="price-card"><div class="price-top"><span>Recurring Cleaning</span><b>Convenient</b></div><h3>Ongoing help for a cleaner home</h3><p class="price"><small>$</small>40 <span>/ hour</span></p><p class="minimum">Weekly demo plan · Cleaner consistency when available</p><ul><li>Standard-cleaning tasks</li><li>Recurring scheduling priority</li><li>Saved household preferences</li><li>Rotating monthly focus areas</li></ul><a class="btn btn-dark" href="<?php echo esc_attr( brightclean_phone_href() ); ?>">Ask About Recurring Cleaning</a></article>
    </div>
    <div class="shell price-note"><span>i</span><p><strong>How is the price calculated?</strong> The cleaner confirms the expected duration before work begins. Specialty cleaning, appliance interiors, and high-access work require a separate estimate.</p></div>
  </section>

  <section class="promise section" id="process">
    <div class="shell promise-grid">
      <div class="promise-copy"><span class="section-kicker light">Service Promise</span><h2>Turn uncertainty into<br>four clear expectations.</h2><p>Customers should understand who is coming, when to expect them, how demo pricing works, and how concerns are handled.</p><a class="btn btn-cream" href="<?php echo esc_attr( brightclean_phone_href() ); ?>">Ask About Availability</a></div>
      <ol class="steps">
        <li><span>01</span><div><h3>Clear timing</h3><p>Confirm the address and needs, then receive available appointment options.</p></div></li>
        <li><span>02</span><div><h3>Clear pricing</h3><p>Review the pricing basis and estimated duration before service begins.</p></div></li>
        <li><span>03</span><div><h3>Clear assignment</h3><p>Receive the cleaner name and estimated arrival information before service.</p></div></li>
        <li><span>04</span><div><h3>Clear follow-up</h3><p>Review completed work and contact the team promptly about concerns within the agreed scope.</p></div></li>
      </ol>
    </div>
  </section>

  <section class="proof section" id="proof">
    <div class="shell section-head"><div><span class="section-kicker">Trust Must Be Earned</span><h2>Use verified proof—not invented claims.</h2></div><p>The reviews below are fictional classroom examples and must be replaced with authorized customer feedback before publication.</p></div>
    <div class="shell review-grid">
      <article class="review featured-review"><div class="stars">★★★★★</div><blockquote>“The booking process was clear, and the kitchen and bathrooms received the attention we discussed.”</blockquote><footer><span class="review-avatar">A</span><div><strong>Alex R.</strong><small>Downtown · Standard Cleaning</small></div><b>Demo Review</b></footer></article>
      <div class="review-stack"><article class="review"><div class="stars">★★★★★</div><blockquote>“The move-out cleaning checklist made it easy to discuss priorities.”</blockquote><footer><span class="review-avatar">J</span><div><strong>Jordan T.</strong><small>Almaden · Deep Cleaning</small></div></footer></article><article class="review"><div class="stars">★★★★★</div><blockquote>“Recurring notes helped keep our priorities consistent from visit to visit.”</blockquote><footer><span class="review-avatar">S</span><div><strong>Sam K.</strong><small>Cambrian · Recurring Cleaning</small></div></footer></article></div>
    </div>
  </section>

  <section class="service-area section">
    <div class="shell area-grid"><div><span class="section-kicker">Service Area</span><h2>Serving San Jose neighborhoods</h2><p>Share your ZIP code so the team can confirm whether the address is within the demonstration service area.</p><div class="districts"><span>Downtown</span><span>Willow Glen</span><span>Almaden</span><span>Cambrian</span><span>Berryessa</span><span>Evergreen</span><span>Rose Garden</span><span>Japantown</span></div></div><div class="map-card" aria-label="San Jose demonstration service area map"><div class="map-rings"></div><span class="pin p1">Downtown</span><span class="pin p2">Willow Glen</span><span class="pin p3">Berryessa</span><span class="pin p4">Evergreen</span><div class="map-center">Bright<br>Clean</div></div></div>
  </section>

  <section class="faq section" id="faq">
    <div class="shell faq-grid"><div class="faq-intro"><span class="section-kicker">FAQ</span><h2>Questions before you inquire</h2><p>Ask the assistant or call with your ZIP code, home size, and cleaning priorities.</p><a class="text-link" href="<?php echo esc_attr( brightclean_phone_href() ); ?>"><?php echo esc_html( get_theme_mod( 'brightclean_phone', '(408) 555-0147' ) ); ?> →</a></div><div class="accordions">
      <details open><summary>Can I book same-day cleaning?<span>+</span></summary><p>Availability depends on the service area and schedule. Any availability shown on this classroom site is fictional and not a live booking promise.</p></details>
      <details><summary>Do cleaners bring supplies?<span>+</span></summary><p>The demonstration service includes basic cleaning supplies. Discuss special materials, equipment, allergies, or product preferences before service.</p></details>
      <details><summary>How do I avoid unexpected extra time?<span>+</span></summary><p>Confirm priorities and estimated duration before work begins. Any extension should be discussed and approved first.</p></details>
      <details><summary>What if I have a concern?<span>+</span></summary><p>Review the completed work and report concerns promptly. Any remedy depends on the final published service policy.</p></details>
    </div></div>
  </section>

  <section class="final-cta"><div class="shell final-grid"><div><span class="section-kicker light">A cleaner home starts with one conversation</span><h2>Tell us your ZIP code and priorities.<br>Ask about available options.</h2></div><div class="cta-box"><small>Demo inquiry line · 8:00 AM–8:00 PM</small><a href="<?php echo esc_attr( brightclean_phone_href() ); ?>"><?php echo esc_html( get_theme_mod( 'brightclean_phone', '(408) 555-0147' ) ); ?></a><p>Ask questions first, then decide whether to request an estimate.</p><a class="btn btn-cream" href="<?php echo esc_url( home_url( '/#services' ) ); ?>">View Demo Pricing</a></div></div></section>
</main>
<?php get_footer(); ?>
