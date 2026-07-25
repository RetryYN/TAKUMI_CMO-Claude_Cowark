"""市場シェアと射程距離 — ランチェスター戦略の目標値を判定に使える形にする。

**このモジュールの中心は数値ではなく、1つの不変条件である。**

> **市場の定義（分母）を書かずに、シェアを語らせない。**

分母を決めなければ、範囲を狭めていくらでも「1位」を作れる。それは自己満足であり、
対外的に主張すれば景表法の No.1 表示の問題にもなる（→ `skills/ad-compliance-jp`）。
そのため `market_definition` が空なら**オブジェクトを作れない**。

シェアの目標値・射程距離の出典と、その確からしさの限界は
`skills/scale-strategy-jp` の出典欄に記載してある（**原典未取得**の扱い）。

**KPIツリーとは別**: シェアは「どこで1位を取りにいくか」を決める戦略の材料であり、
KPIツリー（動かすための指標）とは役割が違う。有料指標の禁止もここでは緩めない。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class LanchesterMode(Enum):
    """どちらの法則が働く戦い方か。射程距離の倍率が変わる。"""

    FIRST_LAW = "第一法則（局地戦・一騎討ち・接近戦）"    # 射程距離 3倍
    SECOND_LAW = "第二法則（広域戦・確率戦）"            # 射程距離 √3倍（約1.7倍）


# 市場シェアの7つのシンボル目標数値（大きい順）
SHARE_TARGETS: tuple[tuple[float, str, str], ...] = (
    (0.739, "上限目標値", "独占的。地位が圧倒的に安定する"),
    (0.417, "安定目標値", "1位として安定する。事実上のナンバーワン"),
    (0.261, "下限目標値", "1位の最低条件。**下回ると1位でも安定しない**"),
    (0.193, "上位目標値", "上位グループに入る"),
    (0.109, "影響目標値", "市場全体に影響を与え始める足がかり"),
    (0.068, "存在目標値", "存在を認められ始める"),
    (0.028, "拠点目標値", "拠点として認識され始める"),
)

STABLE_LEADER_THRESHOLD = 0.261
"""下限目標値。1位を名乗っても、ここを下回ると安定しない。"""


def _striking_ratio(mode: LanchesterMode) -> float:
    """射程距離の倍率。第一法則は3倍、第二法則は√3倍（約1.7倍）。"""
    return 3.0 if mode is LanchesterMode.FIRST_LAW else math.sqrt(3.0)


@dataclass(frozen=True)
class MarketShare:
    """ある**明示された市場**における自社のシェア。

    Attributes:
        market_definition: 分母の定義。**空にできない**（「どの市場の話か」を必ず持つ）
        share: 0.0〜1.0
    """

    market_definition: str
    share: float

    def __post_init__(self) -> None:
        if not self.market_definition or not self.market_definition.strip(" 　\t\n"):
            raise ValueError(
                "市場の定義（分母）が空。**分母を決めずにシェアを語らない** — "
                "範囲を狭めればいくらでも「1位」を作れてしまい、対外的に主張すれば "
                "No.1 表示の根拠を問われる（→ skills/ad-compliance-jp）。"
                "「地域 × 客層 × 用途 × 期間」まで書くこと"
            )
        if not 0.0 <= self.share <= 1.0:
            raise ValueError(f"シェアは0.0〜1.0で表す（比率）: {self.share}")

    # --- 目標値 ---

    def current_stage(self) -> tuple[float, str, str] | None:
        """今いる段階。拠点目標値（2.8%）にも届かないなら None。"""
        for target in SHARE_TARGETS:
            if self.share >= target[0]:
                return target
        return None

    def next_target(self) -> tuple[float, str, str] | None:
        """次に狙う段階。上限目標値に達していれば None。"""
        above = [t for t in SHARE_TARGETS if t[0] > self.share]
        return above[-1] if above else None

    def is_stable_leader(self) -> bool:
        """1位として安定する水準（下限目標値 26.1%）に達しているか。"""
        return self.share >= STABLE_LEADER_THRESHOLD

    # --- 射程距離 ---

    def gap_ratio(self, leader_share: float) -> float | None:
        """相手が自社の何倍か。**自社が0なら計算できないので None**（無限大を返さない）。"""
        self._validate_share(leader_share)
        if self.share == 0:
            return None
        return leader_share / self.share

    def is_within_striking_distance(
        self, leader_share: float, mode: LanchesterMode
    ) -> bool:
        """射程距離内か（＝まだ逆転を狙えるか）。

        差が倍率以内なら射程内。**自社が0なら射程外**として扱う。
        """
        ratio = self.gap_ratio(leader_share)
        if ratio is None:
            return False
        return ratio <= _striking_ratio(mode) + 1e-9

    # --- 判定文 ---

    def verdict(
        self,
        leader_share: float | None = None,
        mode: LanchesterMode = LanchesterMode.SECOND_LAW,
    ) -> str:
        """人間が読む判定文。**必ず市場の定義を含める**（どの分母の話かを見失わせない）。"""
        head = f"【{self.market_definition}】シェア {self.share:.1%}"

        stage = self.current_stage()
        if stage is None:
            body = (
                "まだ拠点目標値(2.8%)にも届いていない。"
                "**この分母では戦えない可能性がある** — 市場をさらに細分化して、"
                "1位を取れる範囲を探すこと"
            )
        else:
            body = f"現在の段階: {stage[1]}（{stage[0]:.1%}）— {stage[2]}"
            nxt = self.next_target()
            if nxt:
                body += f"／次に狙う: {nxt[1]}（{nxt[0]:.1%}）"

        if leader_share is None:
            return f"{head}。{body}"

        self._validate_share(leader_share)
        if abs(leader_share - self.share) < 1e-9:
            lead = (
                "自社が1位。ただし**下限目標値(26.1%)を下回っており、1位でも安定しない**"
                if not self.is_stable_leader()
                else "自社が1位で、下限目標値(26.1%)を上回っている"
            )
            return f"{head}。{body}。{lead}"

        if leader_share < self.share:
            return f"{head}。{body}。自社が1位（2位は {leader_share:.1%}）"

        ratio = self.gap_ratio(leader_share)
        limit = _striking_ratio(mode)
        if ratio is None:
            return (
                f"{head}。{body}。1位は {leader_share:.1%}。"
                "自社シェアが0のため倍率は計算できない（**判定不能**）"
            )
        if ratio <= limit + 1e-9:
            return (
                f"{head}。{body}。1位 {leader_share:.1%} との差は {ratio:.2f}倍 — "
                f"{mode.value}の射程内（{limit:.2f}倍以内）。**まだ逆転を狙える**"
            )
        return (
            f"{head}。{body}。1位 {leader_share:.1%} との差は {ratio:.2f}倍 — "
            f"{mode.value}の**射程外**（{limit:.2f}倍を超えている）。"
            "正面から追うのは分が悪い。**市場を細分化して、1位を取れる範囲を作り直すこと**"
        )

    @staticmethod
    def _validate_share(value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"シェアは0.0〜1.0で表す（比率）: {value}")
