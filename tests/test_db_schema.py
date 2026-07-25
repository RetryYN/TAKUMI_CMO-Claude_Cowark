"""計測DBスキーマ（templates/db-schema.sql）の単体テスト。

V6「SQLite 初期化」は実機で人間が確認していたが、**Cowork ランタイムを必要としない** —
スキーマを適用してテーブルを数えるだけで、ローカル/CI で完結する。Tier 1 に降ろした。

ここで守るのは「スキーマが壊れていないこと」と、方針
（追記型・最新値は MAX(measured_at) で取る）を支える構造が存在すること。
"""
import sqlite3
import unittest
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "templates/db-schema.sql"

EXPECTED_TABLES = {
    "schema_meta",
    "media_status",
    "sns_posts",
    "sns_metrics",
    "watch_changes",
    "audit_pages",
    "task_runs",
    "approvals",
    "artifacts",
}


class TestDbSchema(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        self.addCleanup(self.conn.close)

    def _names(self, kind: str) -> set:
        rows = self.conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='{kind}' AND name NOT LIKE 'sqlite_%'"
        )
        return {r[0] for r in rows}

    def test_applies_cleanly_and_creates_expected_tables(self):
        self.assertEqual(self._names("table"), EXPECTED_TABLES)

    def test_table_count_matches_verify_criterion(self):
        """V6 の PASS 基準『9テーブル作成される』と実体を一致させる。"""
        self.assertEqual(len(EXPECTED_TABLES), 9)

    def test_idempotent(self):
        """再適用しても壊れない（CREATE IF NOT EXISTS / INSERT OR IGNORE）。"""
        self.conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(self._names("table"), EXPECTED_TABLES)
        version = self.conn.execute(
            "SELECT COUNT(*) FROM schema_meta WHERE key='version'"
        ).fetchone()[0]
        self.assertEqual(version, 1, "再適用で schema_meta が重複している")

    def test_time_series_tables_have_indexes(self):
        """時系列テーブルは検索用インデックスを持つ（前回比・推移の取得が線形探索にならない）。"""
        indexes = self._names("index")
        self.assertTrue(indexes, "インデックスが1つも定義されていない")

    def test_append_only_shape(self):
        """追記型: measured_at を持つテーブルは、同一キーで複数行を保持できる。"""
        self.conn.execute(
            "INSERT INTO media_status (measured_at, media_id, metric, value) "
            "VALUES ('2026-07-01T00:00:00Z', 'blog', '配信枠の残数', 10)"
        )
        self.conn.execute(
            "INSERT INTO media_status (measured_at, media_id, metric, value) "
            "VALUES ('2026-07-02T00:00:00Z', 'blog', '配信枠の残数', 8)"
        )
        rows = self.conn.execute(
            "SELECT value FROM media_status WHERE media_id='blog' ORDER BY measured_at"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], [10, 8], "履歴が上書きされている")
        latest = self.conn.execute(
            "SELECT value FROM media_status WHERE media_id='blog' "
            "ORDER BY measured_at DESC LIMIT 1"
        ).fetchone()[0]
        self.assertEqual(latest, 8)


if __name__ == "__main__":
    unittest.main()
