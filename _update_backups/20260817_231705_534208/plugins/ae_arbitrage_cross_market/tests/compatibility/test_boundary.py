import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2] / "src" / "ae_arbitrage_cross_market"

class BoundaryTests(unittest.TestCase):
    def test_no_core_private_imports(self):
        violations = []
        for path in ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("alpha_engine"):
                            violations.append((path, alias.name))
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("alpha_engine"):
                    violations.append((path, node.module))
        self.assertEqual(violations, [])

    def test_no_live_execution_keywords_in_runtime_calls(self):
        forbidden_attr = {"place_order", "submit_order", "cancel_order", "withdraw", "transfer_funds"}
        violations = []
        for path in ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_attr:
                    violations.append((path, node.func.attr))
        self.assertEqual(violations, [])
