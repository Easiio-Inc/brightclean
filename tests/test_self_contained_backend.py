import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SelfContainedBackendTests(unittest.TestCase):
    def test_public_server_uses_only_repository_local_backend(self):
        source = (ROOT / "public_server.py").read_text(encoding="utf-8")
        self.assertNotIn("/home/jianl/.hermes", source)
        self.assertNotIn("website_chatbot/backend/app.py", source)
        self.assertTrue((ROOT / "backend" / "chatbot_app.py").is_file())
        self.assertTrue((ROOT / "backend" / "crm_core.py").is_file())

        tree = ast.parse(source)
        backend_paths = [
            node.args[1]
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "spec_from_file_location"
            and len(node.args) >= 2
        ]
        self.assertTrue(backend_paths, "public_server must explicitly load its backend")
        assignments = {
            target.id: ast.unparse(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        path_expression = ast.unparse(backend_paths[0])
        if path_expression in assignments:
            path_expression = assignments[path_expression]
        self.assertIn("ROOT", path_expression)
        self.assertIn("backend", path_expression)
        self.assertIn("chatbot_app.py", path_expression)


if __name__ == "__main__":
    unittest.main()
