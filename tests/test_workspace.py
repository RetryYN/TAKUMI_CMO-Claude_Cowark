"""ワークスペース検証の単体テスト（TDD: 実装より先に書く）。

`scripts/lint.py` がワークスペースの `knowledge/brands/**` をドメインモデルで検証する
（docs/domain-model.md・docs/開発ワークフロー.md §3）。その判定ロジックをここで固定する。

読み込みは呼び出し側から注入する（テストは stdlib の json だけで完結させ、
YAML パーサへの依存をドメイン側に持ち込まない）。
"""
import json
import tempfile
import unittest
from pathlib import Path

from takumi.workspace import validate_workspace


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


_TREE = {
    "root": {
        "name": "指名検索のシェア",
        "kind": "遅行",
        "children": [
            {"name": "オーガニック流入", "kind": "先行", "children": [
                {"name": "記事公開数", "kind": "先行", "children": []},
            ]},
        ],
    }
}


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, rel: str, data) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            data if isinstance(data, str) else json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )

    def registry(self, active="acme", slugs=("acme",)):
        return {
            "active": active,
            "brands": [
                {"slug": s, "name": s.upper(), "status": "active", "created": "2026-07-25"}
                for s in slugs
            ],
        }

    def errors(self):
        return validate_workspace(self.root, _load_json)


class TestNoWorkspace(WorkspaceCase):
    def test_absent_knowledge_is_not_an_error(self):
        """プラグインリポジトリ単体（ワークスペース無し）では何も言わない。"""
        self.assertEqual(self.errors(), [])


class TestRegistry(WorkspaceCase):
    def test_valid_registry(self):
        self.write("knowledge/brands.yaml", self.registry())
        self.write("knowledge/.active-brand", "acme")
        (self.root / "knowledge/brands/acme").mkdir(parents=True)
        self.assertEqual(self.errors(), [])

    def test_duplicate_slug_rejected(self):
        reg = self.registry()
        reg["brands"].append(dict(reg["brands"][0]))
        self.write("knowledge/brands.yaml", reg)
        (self.root / "knowledge/brands/acme").mkdir(parents=True)
        self.assertTrue(any("acme" in e for e in self.errors()))

    def test_invalid_slug_rejected(self):
        self.write("knowledge/brands.yaml", self.registry(active="Acme", slugs=("Acme",)))
        self.assertTrue(self.errors())

    def test_active_pointing_to_unregistered_brand(self):
        self.write("knowledge/brands.yaml", self.registry(active="beta", slugs=("acme",)))
        (self.root / "knowledge/brands/acme").mkdir(parents=True)
        self.assertTrue(any("beta" in e for e in self.errors()))

    def test_partition_without_registry_entry(self):
        self.write("knowledge/brands.yaml", self.registry())
        (self.root / "knowledge/brands/acme").mkdir(parents=True)
        (self.root / "knowledge/brands/orphan").mkdir(parents=True)
        self.assertTrue(any("orphan" in e for e in self.errors()))

    def test_registry_entry_without_partition(self):
        self.write("knowledge/brands.yaml", self.registry(slugs=("acme", "beta")))
        (self.root / "knowledge/brands/acme").mkdir(parents=True)
        self.assertTrue(any("beta" in e for e in self.errors()))

    def test_active_brand_file_disagrees_with_registry(self):
        self.write("knowledge/brands.yaml", self.registry(active="acme", slugs=("acme", "beta")))
        self.write("knowledge/.active-brand", "beta")
        for s in ("acme", "beta"):
            (self.root / f"knowledge/brands/{s}").mkdir(parents=True)
        self.assertTrue(any(".active-brand" in e for e in self.errors()))


class TestKpiTree(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.write("knowledge/brands.yaml", self.registry())
        (self.root / "knowledge/brands/acme").mkdir(parents=True)

    def test_valid_tree(self):
        self.write("knowledge/brands/acme/strategy/kpi-tree.yaml", _TREE)
        self.assertEqual(self.errors(), [])

    def test_paid_metric_in_tree_rejected(self):
        bad = json.loads(json.dumps(_TREE))
        bad["root"]["children"][0]["name"] = "ROAS"
        self.write("knowledge/brands/acme/strategy/kpi-tree.yaml", bad)
        self.assertTrue(any("ROAS" in e for e in self.errors()))

    def test_bare_node_without_root_wrapper_accepted(self):
        self.write("knowledge/brands/acme/strategy/kpi-tree.yaml", _TREE["root"])
        self.assertEqual(self.errors(), [])

    def test_malformed_tree_reported(self):
        self.write("knowledge/brands/acme/strategy/kpi-tree.yaml", {"root": {"kind": "遅行"}})
        self.assertTrue(self.errors())


class TestCampaign(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.write("knowledge/brands.yaml", self.registry())
        (self.root / "knowledge/brands/acme").mkdir(parents=True)
        self.write("knowledge/brands/acme/strategy/kpi-tree.yaml", _TREE)

    def camp(self, rel, data):
        self.write(f"knowledge/brands/acme/strategy/campaigns/{rel}", data)

    def test_valid_campaign(self):
        self.camp("spring.yaml", {"goal_kpi": "オーガニック流入", "channels": ["X", "自社ブログ"]})
        self.assertEqual(self.errors(), [])

    def test_goal_outside_the_tree_rejected(self):
        self.camp("spring.yaml", {"goal_kpi": "フォロワー数", "channels": ["X"]})
        self.assertTrue(any("フォロワー数" in e for e in self.errors()))

    def test_paid_channel_rejected(self):
        self.camp("spring.yaml", {"goal_kpi": "オーガニック流入", "channels": ["Google広告"]})
        self.assertTrue(any("Google広告" in e for e in self.errors()))

    def test_channel_as_mapping_accepted(self):
        self.camp("spring.yaml", {
            "goal_kpi": "オーガニック流入",
            "channels": [{"name": "X", "kind": "SNS"}],
        })
        self.assertEqual(self.errors(), [])

    def test_unknown_keys_are_tolerated(self):
        """実運用の YAML は自由記述を含む。認識できないキーでは落とさない。"""
        self.camp("spring.yaml", {"schedule": "4月", "notes": "事例特集", "owner": "編集部"})
        self.assertEqual(self.errors(), [])

    def test_campaign_without_tree_is_reported(self):
        self.write("knowledge/brands.yaml", self.registry(slugs=("acme", "beta")))
        (self.root / "knowledge/brands/beta").mkdir(parents=True)
        self.write(
            "knowledge/brands/beta/strategy/campaigns/x.yaml",
            {"goal_kpi": "オーガニック流入"},
        )
        self.assertTrue(any("beta" in e and "kpi-tree" in e for e in self.errors()))


class TestUnreadableFile(WorkspaceCase):
    def test_broken_file_is_reported_not_raised(self):
        self.write("knowledge/brands.yaml", "{ this is not valid json")
        errs = self.errors()
        self.assertTrue(errs)
        self.assertTrue(any("brands.yaml" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
