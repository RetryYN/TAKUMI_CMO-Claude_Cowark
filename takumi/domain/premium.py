"""景品規制（景品表示法）の限度額 — 紹介特典・口コミキャンペーンの上限を計算する値オブジェクト。

**なぜコードにするか**: 「紹介したら特典」は、ゼロ広告費で最も効く攻めの手段のひとつだが、
日本では景品表示法の景品規制が**金額の上限**を定めている。上限は計算できる以上、
文章の注意書きではなく機械検査にする（規約は必ず機械検査とセットにする、という本プロダクトの方針）。

限度額の出典（消費者庁「景品規制の概要」ほか。詳細と原文引用は `skills/referral-advocacy-jp`）:

| 種別 | 最高額 | 総額 |
|---|---|---|
| 総付景品 | 取引価額 1,000円未満 → 200円 / 1,000円以上 → 取引価額の10分の2 | 定めなし |
| 一般懸賞 | 取引価額 5,000円未満 → 取引価額の20倍 / 5,000円以上 → 10万円 | 売上予定総額の2% |
| 共同懸賞 | 取引価額にかかわらず30万円 | 売上予定総額の3% |

**この値オブジェクトは法的助言ではない。** 「取引の価額」の認定や、そもそも景品類に当たるかの判断は
事案ごとの評価を含む。ここが計算するのは**上限の目安**であり、超えていれば止める用途に使う
（超えていなければ適法、という保証には使わない）。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .enum_guard import require_enum

# 景品類に当たらないもの（消費者庁が規制対象外として挙げる例）。
# **自動分類はしない** — 種別は呼び出し側が明示する（`PremiumKind`）。
# 自動判定は過剰検知（適法な施策を止める）と過小検知（違法な施策を通す）の両方を生み、
# どちらも法的判断を誤らせる。ここは事実の一覧として持ち、判断は人間に残す。
NOT_PREMIUM_EXAMPLES = (
    "値引き（自社の商品・役務の対価そのものを減額するもの）",
    "自他店共通の同額割引券",
    "商品の販売・使用または役務の提供のために必要な物品・サービス（配送料など）",
    "見本その他宣伝用の物品・サービス",
    "開店披露・創業記念等の行事に際して提供する物品・サービス",
    "アフターサービス・付随する物品（取引の本来の内容をなすもの）",
)


class PremiumKind(Enum):
    """景品類の提供方法。**推測せず、呼び出し側が宣言する。**"""

    TOTSUKE = "総付景品"          # 懸賞によらず、購入者・来店者にもれなく提供する
    GENERAL_LOTTERY = "一般懸賞"   # くじ等の偶然性、特定行為の優劣・正誤で提供先を決める
    JOINT_LOTTERY = "共同懸賞"     # 商店街・複数事業者が共同で行う懸賞


def _totsuke_max(transaction_value_yen: int) -> int:
    if transaction_value_yen < 1000:
        return 200
    # 「10分の2」。端数は切り捨てる（1円でも超えれば違反になりうるため安全側に倒す）
    return transaction_value_yen * 2 // 10


def _general_lottery_max(transaction_value_yen: int) -> int:
    if transaction_value_yen < 5000:
        return transaction_value_yen * 20
    return 100_000


@dataclass(frozen=True)
class PremiumOffer:
    """提供しようとしている景品類ひとつ分。

    Attributes:
        kind: 提供方法（総付／一般懸賞／共同懸賞）
        transaction_value_yen: 取引の価額
        premium_value_yen: 提供する景品類の価額
        expected_sales_yen: 懸賞に係る売上予定総額（懸賞のときだけ意味を持つ）
        total_premium_yen: 提供する景品類の総額（懸賞のときだけ意味を持つ）
    """

    kind: PremiumKind
    transaction_value_yen: int
    premium_value_yen: int
    expected_sales_yen: int | None = None
    total_premium_yen: int | None = None

    def __post_init__(self) -> None:
        # 種別が enum でなければ、以下の上限分岐がすべて偽になって素通りする（2026-07-26 F-1）
        require_enum(self.kind, PremiumKind, "kind（提供方法）")
        if self.transaction_value_yen <= 0:
            raise ValueError(
                f"取引の価額は正の数でなければならない: {self.transaction_value_yen}"
            )
        if self.premium_value_yen < 0:
            raise ValueError(f"景品類の価額は負にできない: {self.premium_value_yen}")

    @property
    def is_lottery(self) -> bool:
        """懸賞か（＝総額規制の対象か）。"""
        return self.kind in (PremiumKind.GENERAL_LOTTERY, PremiumKind.JOINT_LOTTERY)

    def max_premium_yen(self) -> int:
        """景品類1つあたりの最高額。"""
        if self.kind is PremiumKind.TOTSUKE:
            return _totsuke_max(self.transaction_value_yen)
        if self.kind is PremiumKind.GENERAL_LOTTERY:
            return _general_lottery_max(self.transaction_value_yen)
        if self.kind is PremiumKind.JOINT_LOTTERY:
            return 300_000  # 共同懸賞は取引価額にかかわらず30万円
        # ここに落ちるのは PremiumKind に種別を足して上限を書き忘れたとき。
        # **最後の分岐を「その他」の受け皿にしない** — 30万円（最も緩い上限）が
        # 新種別の既定になって黙って通ってしまう。判定不能として止める。
        raise ValueError(f"上限が定義されていない提供方法: {self.kind!r}")

    def max_total_premium_yen(self) -> int | None:
        """景品類の総額の上限。総付景品には総額規制が無いため None。

        懸賞であっても売上予定総額が未申告なら None（＝計算できない）を返す。
        **None を「上限なし」と読まないこと** — `violations()` は未申告を判定不能として報告する。
        """
        if not self.is_lottery or self.expected_sales_yen is None:
            return None
        rate = 2 if self.kind is PremiumKind.GENERAL_LOTTERY else 3
        return self.expected_sales_yen * rate // 100

    def violations(self) -> list[str]:
        """上限超過と、判定できなかった点を列挙する。空リスト＝止める理由が見つからなかった。"""
        found: list[str] = []

        limit = self.max_premium_yen()
        if self.premium_value_yen > limit:
            found.append(
                f"{self.kind.value}の最高額を超えている: "
                f"{self.premium_value_yen:,}円 > 上限 {limit:,}円"
                f"（取引の価額 {self.transaction_value_yen:,}円）"
            )

        if self.is_lottery:
            total_limit = self.max_total_premium_yen()
            if total_limit is None:
                found.append(
                    f"{self.kind.value}の総額規制が判定不能: "
                    "懸賞に係る売上予定総額（expected_sales_yen）が未申告。"
                    "**未申告を「問題なし」と扱わないこと**"
                )
            elif self.total_premium_yen is None:
                found.append(
                    f"{self.kind.value}の総額規制が判定不能: "
                    "提供する景品類の総額（total_premium_yen）が未申告"
                )
            elif self.total_premium_yen > total_limit:
                found.append(
                    f"{self.kind.value}の総額を超えている: "
                    f"{self.total_premium_yen:,}円 > 上限 {total_limit:,}円"
                    f"（売上予定総額 {self.expected_sales_yen:,}円）"
                )

        return found

    def assert_lawful(self) -> None:
        """上限を超えている、または判定不能な点があれば ValueError を投げる。"""
        found = self.violations()
        if found:
            raise ValueError(
                "景品規制の上限に抵触、または判定不能:\n  - " + "\n  - ".join(found)
            )
