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


if __name__ == "__main__":
    unittest.main()
