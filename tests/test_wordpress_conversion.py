import re
import unittest
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CONVERSION = ROOT / "wordpress-conversion"
THEME = CONVERSION / "brightclean-wp-theme"
ZIP = CONVERSION / "dist" / "brightclean-wp-theme.zip"


class WordPressConversionTests(unittest.TestCase):
    def text(self, relative):
        return (THEME / relative).read_text(encoding="utf-8")

    def test_required_theme_structure(self):
        for name in ("style.css", "functions.php", "header.php", "front-page.php",
                     "footer.php", "index.php", "page.php", "README.md"):
            self.assertTrue((THEME / name).is_file(), name)
        self.assertRegex(self.text("style.css"), r"(?i)Theme Name:\s*BrightClean")

    def test_wordpress_hooks_and_supports(self):
        all_php = "\n".join(p.read_text() for p in THEME.glob("*.php"))
        for token in ("wp_head()", "wp_body_open()", "wp_footer()", "body_class()",
                      "language_attributes()", "bloginfo( 'charset' )"):
            self.assertIn(token, all_php)
        functions = self.text("functions.php")
        for feature in ("title-tag", "custom-logo", "post-thumbnails", "html5"):
            self.assertIn(feature, functions)
        self.assertIn("wp_enqueue_style", functions)
        self.assertIn("wp_enqueue_script", functions)
        self.assertIn("register_nav_menus", functions)

    def test_homepage_and_safe_links(self):
        page = self.text("front-page.php")
        for section in ('id="services"', 'id="process"', 'id="proof"', 'id="faq"'):
            self.assertIn(section, page)
        self.assertIn("home_url( '/#services' )", page)
        self.assertNotRegex(page, r'(?:src|href)=["\']assets/')
        self.assertIn("brightclean_phone_href", page)

    def test_chatbot_customizer_is_safe_and_configurable(self):
        functions = self.text("functions.php")
        footer = self.text("footer.php")
        combined = functions + footer
        for key in ("brightclean_chat_enabled", "brightclean_chat_api_base", "brightclean_chat_title",
                    "brightclean_chat_greeting", "brightclean_chat_primary_color", "brightclean_chat_position"):
            self.assertIn(key, combined)
        self.assertIn("class3-brightclean-san-jose", combined)
        self.assertIn("esc_url", combined)
        self.assertNotIn("OPENAI_API_KEY", combined)
        readme = self.text("README.md")
        self.assertIn("HTTPS", readme)
        self.assertIn("CORS", readme)
        self.assertIn("rollback", readme.lower())

    def test_business_customizer_fields(self):
        functions = self.text("functions.php")
        for key in ("brightclean_phone", "brightclean_email", "brightclean_cta_label"):
            self.assertIn(key, functions)
        self.assertIn("sanitize_email", functions)

    def test_assets_and_no_secrets(self):
        for name in ("assets/css/styles.css", "assets/css/easiio-chatbot-widget.css",
                     "assets/js/main.js", "assets/js/easiio-chatbot-widget.js",
                     "assets/images/brightclean-hero-clean.jpg"):
            self.assertTrue((THEME / name).is_file(), name)
        secret = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=)")
        for path in THEME.rglob("*"):
            if path.is_file() and path.suffix.lower() not in {".jpg", ".png", ".zip"}:
                self.assertIsNone(secret.search(path.read_text(errors="ignore")), str(path))

    def test_zip_is_valid_and_paths_are_safe(self):
        self.assertTrue(ZIP.is_file())
        with zipfile.ZipFile(ZIP) as zf:
            self.assertIsNone(zf.testzip())
            names = zf.namelist()
            self.assertIn("brightclean-wp-theme/style.css", names)
            for name in names:
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual(path.parts[0], "brightclean-wp-theme")


if __name__ == "__main__":
    unittest.main()
