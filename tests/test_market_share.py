"""市場シェアと射程距離の判定（ランチェスター戦略の目標値）の単体テスト。

**なぜドメインに置くか**: 「1位を取る」は規模の小さい側にとって現実的な唯一の勝ち方だが、
**分母（市場の定義）を書かずにシェアを語ると、いくらでも「1位」を作れてしまう。**
それは自己満足であり、対外的に言えば景表法の No.1 表示の問題にもなる（→ skills/ad-compliance-jp）。

そこで **市場の定義が空ならオブジェクトを作れない**ようにする。
シェアの数値そのものより、この不変条件のほうが重要である。
"""
import unittest

from takumi.domain.market_share import LanchesterMode, MarketShare


class TestMarketDefinitionRequired(unittest.TestCase):
    """分母を定義せずにシェアを語らせない（このモジュールの中心的な不変条件）。"""

    def test_empty_definition_rejected(self):
        for bad in ("", "   ", "　"):
            with self.assertRaises(ValueError) as ctx:
                MarketShare(bad, 0.3)
            self.assertIn("市場の定義", str(ctx.exception))

    def test_definition_is_kept_verbatim(self):
        ms = MarketShare("名古屋市の個人向けピアノ教室（月謝制）", 0.3)
        self.assertEqual(ms.market_definition, "名古屋市の個人向けピアノ教室（月謝制）")


class TestShareRange(unittest.TestCase):
    def test_negative_or_over_one_rejected(self):
        for bad in (-0.01, 1.01, 30):
            with self.assertRaises(ValueError):
                MarketShare("ある市場", bad)

    def test_boundaries_allowed(self):
        self.assertEqual(MarketShare("ある市場", 0.0).share, 0.0)
        self.assertEqual(MarketShare("ある市場", 1.0).share, 1.0)


class TestSymbolTargets(unittest.TestCase):
    """7つのシンボル目標値（上限73.9 / 安定41.7 / 下限26.1 / 上位19.3 / 影響10.9 / 存在6.8 / 拠点2.8）。"""

    def test_current_stage(self):
        self.assertEqual(MarketShare("m", 0.80).current_stage()[1], "上限目標値")
        self.assertEqual(MarketShare("m", 0.45).current_stage()[1], "安定目標値")
        self.assertEqual(MarketShare("m", 0.30).current_stage()[1], "下限目標値")
        self.assertEqual(MarketShare("m", 0.12).current_stage()[1], "影響目標値")
        self.assertEqual(MarketShare("m", 0.03).current_stage()[1], "拠点目標値")

    def test_below_all_targets_has_no_stage(self):
        """拠点目標値（2.8%）にも届かないときは None。「まだどの段階にも乗っていない」。"""
        self.assertIsNone(MarketShare("m", 0.01).current_stage())

    def test_next_target_is_the_one_above(self):
        self.assertEqual(MarketShare("m", 0.03).next_target()[1], "存在目標値")
        self.assertEqual(MarketShare("m", 0.30).next_target()[1], "安定目標値")
        self.assertEqual(MarketShare("m", 0.01).next_target()[1], "拠点目標値")

    def test_no_next_target_at_top(self):
        self.assertIsNone(MarketShare("m", 0.80).next_target())

    def test_leader_stability_threshold_is_26_1(self):
        """1位でも26.1%を下回ると安定しない、が下限目標値の意味。"""
        self.assertFalse(MarketShare("m", 0.25).is_stable_leader())
        self.assertTrue(MarketShare("m", 0.262).is_stable_leader())


class TestStrikingDistance(unittest.TestCase):
    """射程距離理論: 第一法則（局地戦・一騎討ち）は3倍、第二法則（広域戦）は√3倍（約1.7倍）。"""

    def test_first_law_needs_three_times(self):
        follower = MarketShare("m", 0.10)
        # 3倍ちょうどは射程内（＝まだ逆転可能）、3倍超は射程外
        self.assertTrue(follower.is_within_striking_distance(0.30, LanchesterMode.FIRST_LAW))
        self.assertFalse(follower.is_within_striking_distance(0.31, LanchesterMode.FIRST_LAW))

    def test_second_law_needs_root_three(self):
        follower = MarketShare("m", 0.10)
        self.assertTrue(follower.is_within_striking_distance(0.17, LanchesterMode.SECOND_LAW))
        self.assertFalse(follower.is_within_striking_distance(0.18, LanchesterMode.SECOND_LAW))

    def test_gap_ratio(self):
        self.assertAlmostEqual(MarketShare("m", 0.10).gap_ratio(0.30), 3.0)

    def test_zero_share_gap_is_undecidable(self):
        """自社シェアが0のとき「何倍差か」は計算できない。無限大を返さず None。"""
        self.assertIsNone(MarketShare("m", 0.0).gap_ratio(0.30))

    def test_leader_share_must_be_valid(self):
        with self.assertRaises(ValueError):
            MarketShare("m", 0.1).is_within_striking_distance(1.5, LanchesterMode.FIRST_LAW)


class TestVerdict(unittest.TestCase):
    def test_verdict_includes_market_definition(self):
        """判定文には必ず市場の定義が入る（どの分母の話かを見失わせない）。"""
        ms = MarketShare("名古屋市の個人向けピアノ教室", 0.30)
        self.assertIn("名古屋市の個人向けピアノ教室", ms.verdict())

    def test_verdict_warns_unstable_leader(self):
        ms = MarketShare("m", 0.22)
        self.assertIn("安定しない", ms.verdict(leader_share=0.22))

    def test_verdict_reports_out_of_range(self):
        ms = MarketShare("m", 0.05)
        text = ms.verdict(leader_share=0.40, mode=LanchesterMode.FIRST_LAW)
        self.assertIn("射程外", text)
        self.assertIn("細分化", text)

    def test_verdict_reports_within_range(self):
        ms = MarketShare("m", 0.20)
        text = ms.verdict(leader_share=0.35, mode=LanchesterMode.FIRST_LAW)
        self.assertIn("射程内", text)


class TestNotAKpiNode(unittest.TestCase):
    """シェアは戦略の判断材料であって、KPIツリーのノード設計とは別。

    有料指標の禁止は、シェアを扱えるようにしても緩まない。
    """

    def test_module_does_not_depend_on_kpi_tree(self):
        import ast
        from pathlib import Path

        import takumi.domain.market_share as ms

        tree = ast.parse(Path(ms.__file__).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse([m for m in imported if "kpi_tree" in m])

    def test_paid_metrics_still_rejected(self):
        from takumi.domain.kpi_tree import KpiKind, KpiNode

        for banned in ("CAC", "広告費"):
            with self.assertRaises(ValueError):
                KpiNode(banned, KpiKind.LAGGING)


if __name__ == "__main__":
    unittest.main()
