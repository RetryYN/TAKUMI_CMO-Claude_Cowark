"""匠の∞ループ — 上流（戦略）と下流（実行）の受け渡し規則。

ユビキタス言語（docs/domain-model.md）:
    上流ループ   = UpstreamLoop（ドメインサービス）
    下流ループ   = DownstreamLoop（ドメインサービス）
    計画の受け渡し = PlanHandoff（値オブジェクト・∞の下り）
    計測の受け渡し = MeasurementHandoff（値オブジェクト・∞の上り）

不変条件:
    受け渡しの両端は必ず KPIツリーのノードを経由する。
    下りで「ツリーに無い目標」を渡せず、上りで「ツリーに無い実測」を返せない。
    これが切れると ∞ が閉じず、実行の結果が戦略に返らない。
"""
from __future__ import annotations

from dataclasses import dataclass

from .brand import BrandSlug
from .campaign import Campaign
from .channel import Channel
from .strategy import Strategy


@dataclass(frozen=True)
class PlanHandoff:
    """∞の下り — 戦略から実行へ渡す計画（実行ブリーフ）。"""

    brand: BrandSlug
    goal_kpi: str
    channels: list[Channel]
    driver_leaves: list[str]  # 目標KPIの配下にある葉＝手元で動かす指標


@dataclass(frozen=True)
class MeasurementHandoff:
    """∞の上り — 実行から戦略へ返す計測。"""

    brand: BrandSlug
    readings: dict[str, float]  # KPIツリーのノード名 → 実測値


def _require_known(strategy: Strategy, names) -> None:
    known = set(strategy.kpi_tree.all_names())
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(
            f"KPIツリーに無い指標は受け渡せません: {unknown}"
            f"（測るなら先にツリーへ置く。定義を後から変えると過去と比較できない）"
        )


class UpstreamLoop:
    """上流ループ（リサーチ→仮説→戦略→計画→改善）。下流へ計画を流す。"""

    @staticmethod
    def hand_down(strategy: Strategy, campaign: Campaign) -> PlanHandoff:
        """戦略とキャンペーンから実行ブリーフを組み立てる（整合検証つき）。"""
        campaign.validate_against(strategy)
        return PlanHandoff(
            brand=strategy.brand,
            goal_kpi=campaign.goal_kpi,
            channels=list(campaign.channels),
            driver_leaves=strategy.kpi_tree.leaves_under(campaign.goal_kpi),
        )


class DownstreamLoop:
    """下流ループ（計画→リサーチ→企画→実行→計測→改善）。上流へ計測を返す。"""

    @staticmethod
    def hand_up(strategy: Strategy, readings: dict[str, float]) -> MeasurementHandoff:
        """実測を KPIツリーのノードに紐づけて上流へ返す。"""
        _require_known(strategy, readings)
        return MeasurementHandoff(brand=strategy.brand, readings=dict(readings))

    @staticmethod
    def stalled_nodes(
        strategy: Strategy,
        previous: dict[str, float],
        current: dict[str, float],
        threshold: float = 0.05,
    ) -> list[str]:
        """伸びが閾値未満のノード＝ /戦略 の再立案フラグ。

        threshold は前回比の増加率（0.05 = 5%）。前回値が 0 のノードは、
        今回値が 0 のときだけ停滞とみなす（0 → 正の値は伸びとして扱う）。
        """
        _require_known(strategy, list(previous) + list(current))
        stalled = []
        for name, before in previous.items():
            after = current.get(name)
            if after is None:
                continue
            if before == 0:
                if after <= 0:
                    stalled.append(name)
                continue
            if (after - before) / abs(before) < threshold:
                stalled.append(name)
        return stalled

    @staticmethod
    def unmeasured_leaves(strategy: Strategy, readings: dict[str, float]) -> list[str]:
        """一度も測っていない葉＝測る当てのない指標。"""
        return [n.name for n in strategy.kpi_tree.leaves() if n.name not in readings]
