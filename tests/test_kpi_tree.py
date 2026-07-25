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

    def test_no_false_positive_on_substrings(self):
        """過剰検知もガードの失敗。ラテン文字は単語境界で照合する。

        2026-07-25 の回帰: Channel("Threads") が "ads" の部分一致で弾かれた。
        指標側も同じ形（cache→cac 等）を踏まないことを固定する。
        """
        for ok in ("Threads の保存率", "cache ヒット率", "Roadmap 消化率"):
            self.assertEqual(KpiNode(ok, KpiKind.LEADING).name, ok)
        # 単語として現れれば従来どおり拒否する
        for bad in ("CPC", "ad spend", "月間 ROAS"):
            with self.assertRaises(ValueError):
                KpiNode(bad, KpiKind.LAGGING)


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

    def test_find(self):
        tree = self._tree()
        self.assertEqual(tree.find("オーガニック流入").kind, KpiKind.LEADING)
        self.assertIsNone(tree.find("フォロワー数"))

    def test_leaves_under(self):
        tree = self._tree()
        self.assertEqual(tree.leaves_under("オーガニック流入"), ["記事公開数"])
        # 葉そのものを指したらそれ自身
        self.assertEqual(tree.leaves_under("記事公開数"), ["記事公開数"])
        # 根を指したら全葉
        self.assertEqual(tree.leaves_under("北極星: 指名検索数"), ["記事公開数", "エンゲージ率"])

    def test_leaves_under_unknown_node(self):
        with self.assertRaises(ValueError):
            self._tree().leaves_under("フォロワー数")

    def test_forbid_paid_anywhere(self):
        with self.assertRaises(ValueError):
            KpiTree(KpiNode("北極星", KpiKind.LAGGING, [KpiNode("ROAS", KpiKind.LEADING)]))

    def test_roundtrip(self):
        tree = self._tree()
        self.assertEqual(KpiTree.from_dict(tree.to_dict()), tree)


if __name__ == "__main__":
    unittest.main()
