import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_ID = "class3-brightclean-san-jose"
MAIN_URL = "http://127.0.0.1:8188/"


class DemoContentTests(unittest.TestCase):
    def test_main_website_summary_is_available_to_rag(self):
        document = json.loads((ROOT / "data" / "rag-content.json").read_text())
        homepage_items = [
            item for item in document["sites"][SITE_ID]
            if item.get("url") == MAIN_URL and "2,400" in item.get("content", "")
        ]
        self.assertEqual(len(homepage_items), 1)
        content = homepage_items[0]["content"]
        self.assertIn("sample completed jobs", content.lower())
        self.assertIn("fictional classroom", content.lower())

    def test_chatbot_renders_safe_markdown_for_bot_answers(self):
        widget_paths = (
            ROOT / "assets/js/easiio-chatbot-widget.js",
            ROOT / "wordpress-conversion/brightclean-wp-theme/assets/js/easiio-chatbot-widget.js",
        )
        for widget_path in widget_paths:
            source = widget_path.read_text(encoding="utf-8")
            self.assertIn("function renderSafeMarkdown", source, str(widget_path))
            self.assertIn("message.innerHTML = renderSafeMarkdown(text)", source, str(widget_path))
            self.assertIn("message.textContent = text", source, str(widget_path))
            self.assertIn("escapeHtml", source, str(widget_path))


if __name__ == "__main__":
    unittest.main()
