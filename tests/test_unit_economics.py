"""ビジネスモデルとキャッシュの計算（損益分岐点・CCC・オーガニック獲得コスト）の単体テスト。

**なぜドメインに置くか**: マーケティングの意思決定は最終的に「儲かるのか・現金が回るのか」で決まる。
ここは計算できるので、文章の注意書きではなく機械検査にする（本プロダクトの一貫方針）。

**設計上の要点は「計算できないときに黙って数字を返さない」こと。**
変動費率が1以上なら損益分岐点は存在しない（売っても赤字が増える）。
獲得件数が0なら獲得単価は判定不能であり、**0円でも無限大でもない**。
ここで嘘の数字を返すと、意思決定がまるごと狂う。
"""
import unittest

from takumi.domain.unit_economics import BreakEven, CashCycle, OrganicAcquisitionCost


class TestBreakEven(unittest.TestCase):
    def test_contribution_margin_ratio(self):
        self.assertAlmostEqual(BreakEven(1_000_000, 0.4).contribution_margin_ratio(), 0.6)

    def test_break_even_sales(self):
        # 固定費100万 / 限界利益率0.6 = 1,666,666.7 → 切り上げ
        self.assertEqual(BreakEven(1_000_000, 0.4).break_even_sales_yen(), 1_666_667)

    def test_zero_variable_cost(self):
        self.assertEqual(BreakEven(500_000, 0.0).break_even_sales_yen(), 500_000)

    def test_required_sales_for_target_profit(self):
        # (固定費100万 + 目標利益50万) / 0.6
        self.assertEqual(BreakEven(1_000_000, 0.4).required_sales_yen(500_000), 2_500_000)

    def test_variable_ratio_one_has_no_break_even(self):
        """変動費率が1 = 売っても限界利益がゼロ。損益分岐点は存在しない。"""
        with self.assertRaises(ValueError) as ctx:
            BreakEven(1_000_000, 1.0)
        self.assertIn("損益分岐点", str(ctx.exception))

    def test_variable_ratio_over_one_rejected(self):
        """売るほど赤字が増える構造。数字を返さず止める。"""
        with self.assertRaises(ValueError):
            BreakEven(1_000_000, 1.2)

    def test_negative_inputs_rejected(self):
        with self.assertRaises(ValueError):
            BreakEven(-1, 0.4)
        with self.assertRaises(ValueError):
            BreakEven(1_000_000, -0.1)

    def test_margin_of_safety(self):
        """安全余裕率: 現状売上が損益分岐点をどれだけ上回っているか。"""
        be = BreakEven(1_000_000, 0.4)
        self.assertAlmostEqual(be.margin_of_safety_ratio(2_500_000), 1 - 1_666_667 / 2_500_000, places=4)

    def test_margin_of_safety_below_break_even_is_negative(self):
        be = BreakEven(1_000_000, 0.4)
        self.assertLess(be.margin_of_safety_ratio(1_000_000), 0)


class TestCashCycle(unittest.TestCase):
    def test_ccc_is_inventory_plus_receivable_minus_payable(self):
        self.assertAlmostEqual(CashCycle(30, 45, 60).ccc_days(), 15)

    def test_negative_cycle_detected(self):
        """前受金・即時決済モデルは CCC が負になり、成長するほど現金が増える。"""
        cycle = CashCycle(inventory_days=0, receivable_days=0, payable_days=30)
        self.assertAlmostEqual(cycle.ccc_days(), -30)
        self.assertTrue(cycle.is_cash_generating())

    def test_positive_cycle_is_not_cash_generating(self):
        self.assertFalse(CashCycle(30, 45, 60).is_cash_generating())

    def test_working_capital_need(self):
        """CCC が正なら、売上が増えるほど運転資金が要る。日商 × CCC。"""
        cycle = CashCycle(30, 45, 60)
        self.assertEqual(cycle.working_capital_need_yen(daily_sales_yen=100_000), 1_500_000)

    def test_working_capital_need_is_zero_when_cash_generating(self):
        """負のCCCで「マイナスの運転資金が必要」と読ませない（0 に丸める）。"""
        cycle = CashCycle(0, 0, 30)
        self.assertEqual(cycle.working_capital_need_yen(daily_sales_yen=100_000), 0)

    def test_negative_days_rejected(self):
        for bad in ((-1, 0, 0), (0, -1, 0), (0, 0, -1)):
            with self.assertRaises(ValueError):
                CashCycle(*bad)


class TestOrganicAcquisitionCost(unittest.TestCase):
    """ゼロ広告費でも獲得コストはゼロではない — **時間が原価**。"""

    def test_total_cost_is_hours_times_rate(self):
        cost = OrganicAcquisitionCost(hours_spent=40, hourly_rate_yen=5_000, customers_acquired=8)
        self.assertEqual(cost.total_cost_yen(), 200_000)

    def test_cost_per_customer(self):
        cost = OrganicAcquisitionCost(hours_spent=40, hourly_rate_yen=5_000, customers_acquired=8)
        self.assertEqual(cost.cost_per_customer_yen(), 25_000)

    def test_zero_customers_is_undecidable_not_zero(self):
        """獲得0件を「コスト0円」とも「効率が良い」とも読ませない。

        判定不能を有利な数字に化けさせるのが、最も高くつく間違い
        （→ skills/hypothesis-design-jp「判定不能を『効果あり』と書かない」）。
        """
        cost = OrganicAcquisitionCost(hours_spent=40, hourly_rate_yen=5_000, customers_acquired=0)
        self.assertIsNone(cost.cost_per_customer_yen())
        self.assertIn("判定不能", cost.verdict())

    def test_verdict_reports_unprofitable(self):
        """1件あたりの粗利より獲得コストが高いなら、続けるほど損をする。"""
        cost = OrganicAcquisitionCost(hours_spent=40, hourly_rate_yen=5_000, customers_acquired=2)
        # 1件 100,000円 のコストに対し、粗利 30,000円
        self.assertIn("回収できていない", cost.verdict(gross_profit_per_customer_yen=30_000))

    def test_verdict_reports_profitable(self):
        cost = OrganicAcquisitionCost(hours_spent=10, hourly_rate_yen=3_000, customers_acquired=6)
        # 1件 5,000円 のコストに対し、粗利 30,000円
        self.assertIn("回収できている", cost.verdict(gross_profit_per_customer_yen=30_000))

    def test_negative_or_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            OrganicAcquisitionCost(hours_spent=10, hourly_rate_yen=0, customers_acquired=1)
        with self.assertRaises(ValueError):
            OrganicAcquisitionCost(hours_spent=-1, hourly_rate_yen=3_000, customers_acquired=1)
        with self.assertRaises(ValueError):
            OrganicAcquisitionCost(hours_spent=10, hourly_rate_yen=3_000, customers_acquired=-1)


class TestNotAKpiNode(unittest.TestCase):
    """これらは経営の分析であって、KPIツリーのノードではない。

    KPIツリーは「動かすための指標」で、葉が手順書に紐づく。獲得単価や損益分岐点は
    **「続けるか・やめるか」を決めるための指標**であり、性質が違う。
    混ぜると「獲得単価を下げる」が施策目標になり、**獲得を減らせば達成できてしまう**。
    """

    def test_module_does_not_depend_on_kpi_tree(self):
        """import を実際に走査する（文字列検索では docstring の解説まで拾ってしまう）。"""
        import ast
        from pathlib import Path

        import takumi.domain.unit_economics as ue

        tree = ast.parse(Path(ue.__file__).read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
                imported += [f"{node.module}.{a.name}" for a in node.names]
        self.assertFalse(
            [m for m in imported if "kpi_tree" in m],
            f"unit_economics は KPIツリーに依存しない設計（実際の import: {imported}）",
        )

    def test_paid_metric_names_still_rejected_by_kpi_tree(self):
        """ユニットエコノミクスを扱えるようにしても、KPIツリーの有料指標禁止は緩まない。"""
        from takumi.domain.kpi_tree import KpiKind, KpiNode

        for banned in ("CAC", "LTV", "ROAS", "広告費"):
            with self.assertRaises(ValueError):
                KpiNode(banned, KpiKind.LAGGING)


if __name__ == "__main__":
    unittest.main()
