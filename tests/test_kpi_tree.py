"""KpiTree 集約の単体テスト（TDD）。

ドメイン不変条件（docs/domain-model.md）: KPIツリーは有料指標（CAC/LTV/ROAS/広告費 等）を
ノードに持たない＝ゼロ広告費をコードで強制する。
"""
import unittest

from takumi.domain.kpi_tree import KpiKind, KpiNode, KpiTree


class TestKpiNode(unittest.TestCase):
    def test_create(self):
        n = KpiNode("オーガニック流入", KpiKind.LEADING)
        self.assertEqual(n.name, "オーガニック流入")
        self.assertEqual(n.kind, KpiKind.LEADING)
        self.assertEqual(n.children, [])

    def test_forbid_paid_metrics(self):
        for bad in ("CAC", "LTV", "ROAS", "CPA", "広告費", "ad spend", "広告予算"):
            with self.assertRaises(ValueError, msg=f"{bad!r} は有料指標として拒否されるべき"):
                KpiNode(bad, KpiKind.LAGGING)

    def test_organic_names_allowed(self):
        for ok in ("指名検索数", "エンゲージ率", "記事公開数", "被リンク数"):
            self.assertEqual(KpiNode(ok, KpiKind.LEADING).name, ok)


class TestKpiTree(unittest.TestCase):
    def _tree(self):
        return KpiTree(
            KpiNode("北極星: 指名検索数", KpiKind.LAGGING, [
                KpiNode("オーガニック流入", KpiKind.LEADING, [
                    KpiNode("記事公開数", KpiKind.LEADING),
                ]),
                KpiNode("エンゲージ率", KpiKind.LEADING),
            ])
        )

    def test_all_names_and_leaves(self):
        tree = self._tree()
        self.assertIn("オーガニック流入", tree.all_names())
        leaves = [n.name for n in tree.leaves()]
        self.assertIn("記事公開数", leaves)
        self.assertIn("エンゲージ率", leaves)
        self.assertNotIn("オーガニック流入", leaves)  # 子を持つので葉ではない

    def test_forbid_paid_anywhere(self):
        with self.assertRaises(ValueError):
            KpiTree(KpiNode("北極星", KpiKind.LAGGING, [KpiNode("ROAS", KpiKind.LEADING)]))

    def test_roundtrip(self):
        tree = self._tree()
        self.assertEqual(KpiTree.from_dict(tree.to_dict()), tree)


if __name__ == "__main__":
    unittest.main()
