"""ローカル検索プロフィールの不変条件テスト（TDD: このファイルが先に赤くなる）。

守りたいのは2点:

1. **プロフィール名に看板に無い語を足さない** — 一時的に効いてしまうので誘惑が強く、
   Google のガイドライン違反はプロフィールの停止につながる（面ごと失う＝ほぼ不可逆）。
2. **対価と引き換えの口コミを依頼しない** — 日本のステマ規制は「表示すれば可」だが、
   Google のポリシーは対価と引き換えの口コミ自体を認めない。**表示では解決しない。**
"""
import ast
import unittest
from pathlib import Path

from takumi.domain.local_profile import (
    ProfileName,
    ReviewSolicitation,
    SolicitationTarget,
)


class TestProfileName(unittest.TestCase):
    def test_看板名と一致していれば通る(self):
        name = ProfileName(storefront_name="珈琲 いちょう", listed_name="珈琲 いちょう")
        self.assertEqual(name.extra_terms(), [])
        self.assertEqual(name.violations(), [])
        name.assert_matches_storefront()  # 例外を投げない

    def test_空白の違いは違反にしない(self):
        """全角・半角スペースの差だけなら、実質同じ名称として扱う。"""
        name = ProfileName(storefront_name="珈琲　いちょう", listed_name="珈琲 いちょう")
        self.assertEqual(name.violations(), [])

    def test_キーワードを後ろに足したら落ちる(self):
        name = ProfileName(
            storefront_name="珈琲 いちょう",
            listed_name="珈琲 いちょう｜渋谷 自家焙煎 コーヒー豆",
        )
        self.assertIn("｜渋谷自家焙煎コーヒー豆", "".join(name.extra_terms()))
        with self.assertRaises(ValueError) as cm:
            name.assert_matches_storefront()
        self.assertIn("看板", str(cm.exception))

    def test_キーワードを前に足しても落ちる(self):
        name = ProfileName(
            storefront_name="いちょう歯科",
            listed_name="【渋谷駅徒歩3分】いちょう歯科",
        )
        self.assertTrue(name.violations())

    def test_看板と別の名称なら別の理由で落ちる(self):
        name = ProfileName(storefront_name="いちょう歯科", listed_name="渋谷デンタルクリニック")
        found = name.violations()
        self.assertTrue(found)
        self.assertIn("一致", "".join(found))

    def test_看板名が空なら判定しない(self):
        """看板名を宣言せずに可否を出さない（推測で通さない）。"""
        with self.assertRaises(ValueError):
            ProfileName(storefront_name="   ", listed_name="いちょう歯科")

    def test_掲載名が空なら落ちる(self):
        with self.assertRaises(ValueError):
            ProfileName(storefront_name="いちょう歯科", listed_name="")


class TestReviewSolicitation(unittest.TestCase):
    def test_顧客に対価なしで頼むのは通る(self):
        s = ReviewSolicitation(target=SolicitationTarget.CUSTOMER, incentive=False)
        self.assertEqual(s.violations(), [])
        s.assert_allowed()

    def test_対価を渡す依頼は表示しても通らない(self):
        s = ReviewSolicitation(target=SolicitationTarget.CUSTOMER, incentive=True)
        found = s.violations()
        self.assertTrue(found)
        joined = "".join(found)
        # 「#PR を付ければよい」という誤読を止める文言が入っていること
        self.assertIn("表示", joined)
        with self.assertRaises(ValueError):
            s.assert_allowed()

    def test_対価が未申告なら判定不能として報告する(self):
        """黙って「問題なし」を返さない。"""
        s = ReviewSolicitation(target=SolicitationTarget.CUSTOMER)
        found = s.violations()
        self.assertTrue(found)
        self.assertIn("判定不能", "".join(found))

    def test_従業員への依頼は対価が無くても通らない(self):
        s = ReviewSolicitation(target=SolicitationTarget.EMPLOYEE, incentive=False)
        self.assertTrue(s.violations())
        self.assertIn("利害", "".join(s.violations()))

    def test_元従業員と取引先も同じ扱い(self):
        for target in (SolicitationTarget.FORMER_EMPLOYEE, SolicitationTarget.CONTRACTOR):
            with self.subTest(target=target):
                s = ReviewSolicitation(target=target, incentive=False)
                self.assertTrue(s.violations())

    def test_競合への投稿は依頼先として選べない(self):
        """自社の口コミ集めの文脈で競合先に投稿させる導線を作らせない。"""
        s = ReviewSolicitation(target=SolicitationTarget.COMPETITOR, incentive=False)
        self.assertTrue(s.violations())


class TestNoKpiTreeDependency(unittest.TestCase):
    def test_kpiツリーに依存しない(self):
        """ローカル検索の可否判定は、KPIツリー（動かす指標）とは別の層にある。"""
        import takumi.domain.local_profile as lp

        tree = ast.parse(Path(lp.__file__).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse([m for m in imported if "kpi_tree" in m])


if __name__ == "__main__":
    unittest.main()
