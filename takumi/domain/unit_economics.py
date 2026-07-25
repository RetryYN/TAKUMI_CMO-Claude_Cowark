"""ビジネスモデルとキャッシュの計算 — 損益分岐点・キャッシュコンバージョンサイクル・獲得コスト。

マーケティングの意思決定は、最後は「**儲かるのか・現金が回るのか**」で決まる。
ここは計算できるので、注意書きではなく機械検査にする。

**この module の設計上の要点は「計算できないときに黙って数字を返さない」こと。**

- 変動費率が1以上なら**損益分岐点は存在しない**（売るほど赤字が増える）→ `ValueError`
- 獲得件数が0なら獲得単価は**判定不能**であり、0円でも無限大でもない → `None` と「判定不能」の判定文
- 負のCCCで「マイナスの運転資金が必要」と読ませない → 0 に丸める

**KPIツリーとは混ぜない。** KPIツリー（`kpi_tree.py`）は「**動かすため**の指標」で、
葉が実行できる手順書に紐づく。ここが扱うのは「**続けるか・やめるか**を決めるための指標」で、
性質が違う。混ぜると「獲得単価を下げる」が施策目標になり、**獲得を減らせば達成できてしまう**。
（この分離は `tests/test_unit_economics.py::TestNotAKpiNode` で固定してある。）
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BreakEven:
    """損益分岐点。

    Attributes:
        fixed_cost_yen: 固定費（期間あたり）
        variable_cost_ratio: 変動費率（売上に対する割合。0 以上 1 未満）
    """

    fixed_cost_yen: int
    variable_cost_ratio: float

    def __post_init__(self) -> None:
        if self.fixed_cost_yen < 0:
            raise ValueError(f"固定費は負にできない: {self.fixed_cost_yen}")
        if self.variable_cost_ratio < 0:
            raise ValueError(f"変動費率は負にできない: {self.variable_cost_ratio}")
        if self.variable_cost_ratio >= 1:
            raise ValueError(
                f"変動費率が {self.variable_cost_ratio:.0%} — **損益分岐点が存在しない**。"
                "売上を伸ばすほど赤字が増える構造なので、"
                "集客の前に原価・提供方法・価格のどれかを変える必要がある"
            )

    def contribution_margin_ratio(self) -> float:
        """限界利益率（売上のうち固定費の回収に回る割合）。"""
        return 1 - self.variable_cost_ratio

    def break_even_sales_yen(self) -> int:
        """損益分岐点売上高。端数は切り上げる（届かない額を「届いた」と言わないため）。"""
        return math.ceil(self.fixed_cost_yen / self.contribution_margin_ratio())

    def required_sales_yen(self, target_profit_yen: int) -> int:
        """目標利益を出すのに必要な売上高。"""
        if target_profit_yen < 0:
            raise ValueError(f"目標利益は負にできない: {target_profit_yen}")
        return math.ceil(
            (self.fixed_cost_yen + target_profit_yen) / self.contribution_margin_ratio()
        )

    def margin_of_safety_ratio(self, actual_sales_yen: int) -> float:
        """安全余裕率。現状売上が損益分岐点をどれだけ上回っているか。

        **負なら赤字。** 小さいほど、売上が少し落ちただけで赤字に落ちる。
        """
        if actual_sales_yen <= 0:
            raise ValueError(f"実績売上は正の数でなければならない: {actual_sales_yen}")
        return 1 - self.break_even_sales_yen() / actual_sales_yen


@dataclass(frozen=True)
class CashCycle:
    """キャッシュコンバージョンサイクル（CCC）— 現金が出てから戻るまでの日数。

    **黒字でも現金が尽きれば終わる。** 成長するほど現金が減る構造かどうかがここで分かる。

    Attributes:
        inventory_days: 棚卸資産回転日数（仕入れてから売れるまで）
        receivable_days: 売上債権回転日数（売れてから入金まで）
        payable_days: 仕入債務回転日数（仕入れてから支払いまで）
    """

    inventory_days: float
    receivable_days: float
    payable_days: float

    def __post_init__(self) -> None:
        for name, value in (
            ("棚卸資産回転日数", self.inventory_days),
            ("売上債権回転日数", self.receivable_days),
            ("仕入債務回転日数", self.payable_days),
        ):
            if value < 0:
                raise ValueError(f"{name}は負にできない: {value}")

    def ccc_days(self) -> float:
        """CCC = 棚卸資産回転日数 + 売上債権回転日数 − 仕入債務回転日数。"""
        return self.inventory_days + self.receivable_days - self.payable_days

    def is_cash_generating(self) -> bool:
        """CCC が負か（＝**売れるほど手元現金が増える**構造。前受金・即時決済モデル）。"""
        return self.ccc_days() < 0

    def working_capital_need_yen(self, daily_sales_yen: int) -> int:
        """必要運転資金の目安 ＝ 日商 × CCC。

        **CCC が負のときは 0 を返す**（「マイナスの運転資金が必要」は意味を成さないため）。
        売上を伸ばす計画を立てる前に、この額を用意できるかを確認する。
        """
        if daily_sales_yen < 0:
            raise ValueError(f"日商は負にできない: {daily_sales_yen}")
        days = self.ccc_days()
        if days <= 0:
            return 0
        return math.ceil(daily_sales_yen * days)


@dataclass(frozen=True)
class OrganicAcquisitionCost:
    """オーガニックな獲得コスト — **ゼロ広告費でも、獲得コストはゼロではない**。

    広告費を使わなくても**時間が原価**として出ていく。「無料でやっている」は錯覚で、
    時間を計上しないと「効率が良い施策」と「ただ人件費で埋めているだけの施策」が区別できない。

    Attributes:
        hours_spent: 投下時間（制作・運用・対応のすべて）
        hourly_rate_yen: 時間単価（自分の時間の値段。決めていないなら決めるところから）
        customers_acquired: その期間に獲得した件数（**証跡のある確定数だけ**）
    """

    hours_spent: float
    hourly_rate_yen: int
    customers_acquired: int

    def __post_init__(self) -> None:
        if self.hours_spent < 0:
            raise ValueError(f"投下時間は負にできない: {self.hours_spent}")
        if self.hourly_rate_yen <= 0:
            raise ValueError(
                f"時間単価は正の数でなければならない: {self.hourly_rate_yen}"
                "（自分の時間を0円にすると、あらゆる施策が「効率的」に見えてしまう）"
            )
        if self.customers_acquired < 0:
            raise ValueError(f"獲得件数は負にできない: {self.customers_acquired}")

    def total_cost_yen(self) -> int:
        """投下した時間の金額換算。"""
        return math.ceil(self.hours_spent * self.hourly_rate_yen)

    def cost_per_customer_yen(self) -> int | None:
        """1件あたりの獲得コスト。**獲得0件なら None（判定不能）**。

        None を 0 や「効率が良い」と読み替えないこと。
        """
        if self.customers_acquired == 0:
            return None
        return math.ceil(self.total_cost_yen() / self.customers_acquired)

    def verdict(self, gross_profit_per_customer_yen: int | None = None) -> str:
        """人間が読む判定文。判定できないときは、そう書く。"""
        per = self.cost_per_customer_yen()
        if per is None:
            return (
                f"判定不能: 投下 {self.total_cost_yen():,}円（{self.hours_spent:g}時間）に対し獲得0件。"
                "**「コスト0円」でも「効率が良い」でもない。** "
                "期間が短すぎるのか、施策が効いていないのかを切り分けること"
            )
        if gross_profit_per_customer_yen is None:
            return (
                f"獲得単価 {per:,}円/件（投下 {self.total_cost_yen():,}円 ÷ {self.customers_acquired}件）。"
                "**1件あたりの粗利を渡すと、回収できているかを判定できる**"
            )
        if gross_profit_per_customer_yen < 0:
            raise ValueError(
                f"1件あたり粗利は負にできない: {gross_profit_per_customer_yen}"
            )
        if per > gross_profit_per_customer_yen:
            return (
                f"回収できていない: 獲得単価 {per:,}円 > 1件あたり粗利 {gross_profit_per_customer_yen:,}円。"
                "**続けるほど損をする。** 時間の投下先を変えるか、単価・粗利の側を動かすこと"
            )
        return (
            f"回収できている: 獲得単価 {per:,}円 ≦ 1件あたり粗利 "
            f"{gross_profit_per_customer_yen:,}円（差 {gross_profit_per_customer_yen - per:,}円/件）"
        )
