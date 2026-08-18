import ast
import pathlib
import unittest


class BoundaryTests(unittest.TestCase):
    def test_no_alpha_engine_private_imports(self):
        root=pathlib.Path(__file__).resolve().parents[1]/"src"/"ae_prediction_markets"
        bad=[]
        for path in root.rglob("*.py"):
            tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("alpha_engine."): bad.append((path,alias.name))
                if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith("alpha_engine."):
                    bad.append((path,node.module))
        self.assertEqual(bad,[])
