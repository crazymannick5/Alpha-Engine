import pathlib
import sqlite3
import unittest

class MigrationTests(unittest.TestCase):
    def test_namespaced_migration_applies_cleanly(self):
        migration = pathlib.Path(__file__).resolve().parents[2] / "migrations" / "0001_arbitrage_namespace.sql"
        sql = migration.read_text(encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.executescript(sql)
        tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
        self.assertIn("plugin_ae_arbitrage_cross_market_relationships", tables)
        self.assertTrue(all(name.startswith("plugin_ae_arbitrage_cross_market_") for name in tables))
        conn.close()
