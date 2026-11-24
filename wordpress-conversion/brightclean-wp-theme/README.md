# BrightClean San Jose WordPress Theme

A classic WordPress conversion of the fictional classroom demo. Pricing, reviews, availability, names, and service claims remain demonstration content and must be verified before any real publication.

## Install and preview

1. Back up the WordPress database and `wp-content` directory.
2. In **Appearance → Themes → Add New → Upload Theme**, upload `brightclean-wp-theme.zip`.
3. Install, then use **Live Preview** before activation. Do not replace or delete the existing theme.
4. In **Settings → Reading**, choose a static front page if desired; `front-page.php` always provides the designed homepage.
5. Assign a menu to **Primary Menu**, or retain the safe built-in section-link fallback.

## Customizer

Open **Appearance → Customize**:

- **Site Identity**: title and optional custom logo.
- **BrightClean Business**: display phone, email, and primary CTA label.
- **BrightClean Chatbot**: enabled state, API base URL, title, greeting, primary color, and bottom-left/right position.

All options are sanitized and escaped. The fixed tenant/site ID is `class3-brightclean-san-jose`; it is an identifier, not a secret.

## Chatbot backend, HTTPS, and CORS

The local default `http://127.0.0.1:8199` is only for same-machine classroom development. **Before production, configure an HTTPS public backend URL**. A visitor's browser cannot reach your server's localhost. Configure the backend's CORS allowlist to the exact public WordPress origin (for example, `https://www.example.com`), permit only required methods/headers, and test from a private browser window.

Never put an OpenAI API key, token, password, or other secret in this theme, Customizer settings, page source, or chatbot JavaScript. Secrets belong only in protected server-side environment/configuration. The public backend must authenticate/limit requests as appropriate.

## Deployment checklist

1. Test the ZIP on staging or Live Preview first.
2. Confirm responsive desktop/mobile layout, menu, phone/email, keyboard navigation, and all disclaimers.
3. Configure the HTTPS API URL and strict CORS origin; verify chatbot success and failure states.
4. Check caching/minification, browser console, page source, and network calls for accidental secrets.
5. Activate during a low-risk window and smoke-test the public site. No live deployment is performed by this package.

## Rollback

Keep the prior theme installed. If checks fail, immediately reactivate it under **Appearance → Themes**. If unavailable, restore the backed-up `wp-content/themes` and database. Clear WordPress/CDN caches, verify the old homepage, and investigate on staging before retrying. Theme activation does not delete posts or pages.

## Package notes

Assets are locally bundled and loaded through WordPress enqueue APIs. The homepage preserves the static demo's sections and responsive CSS. A static `preview.html` is included for visual comparison only; WordPress/PHP behavior requires a WordPress environment.
