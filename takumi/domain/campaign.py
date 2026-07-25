"""Campaign エンティティ — 下流（実行）ループの統括単位。

ユビキタス言語（docs/domain-model.md）:
    キャンペーン = Campaign（エンティティ）

不変条件:
    1. 参加媒体は1つ以上・重複なし・すべてオーガニック（Channel が保証）。
    2. 同一ブランド区画に属する。
    3. 目標KPIは戦略の KPIツリーに実在するノード名（validate_against / for_strategy）。
       背骨から浮いたキャンペーンは、走らせても計測が上流に返らない。
"""
from __future__ import annotations

from dataclasses import dataclass

from .brand import BrandSlug
from .channel import Channel


@dataclass
class Campaign:
    """キャンペーン（エンティティ）。複数媒体を1つの目標の下に束ねる。"""

    name: str
    brand: BrandSlug
    goal_kpi: str
    channels: list[Channel]

    def __post_init__(self) -> None:
        if not self.name.strip(" 　"):
            raise ValueError("キャンペーン名が空です")
        if not self.goal_kpi.strip(" 　"):
            raise ValueError("目標KPIが空です")
        if not self.channels:
            raise ValueError("参加媒体が1つもありません（キャンペーンは媒体を束ねる単位）")
        if len(set(self.channels)) != len(self.channels):
            raise ValueError(f"参加媒体が重複しています: {[c.name for c in self.channels]}")

    def validate_against(self, strategy) -> "Campaign":
        """戦略との整合を検証する（ブランド一致・目標KPIがツリーに実在）。"""
        if strategy.brand != self.brand:
            raise ValueError(
                f"キャンペーンのブランド {self.brand.value!r} が "
                f"戦略のブランド {strategy.brand.value!r} と異なります（区画をまたげません）"
            )
        if self.goal_kpi not in strategy.kpi_tree.all_names():
            raise ValueError(
                f"目標KPI {self.goal_kpi!r} が KPIツリーにありません"
                f"（キャンペーンは必ずツリーのノードを目標にする）"
            )
        return self

    @classmethod
    def for_strategy(
        cls, strategy, name: str, goal_kpi: str, channels: list[Channel]
    ) -> "Campaign":
        """戦略に紐づけてキャンペーンを起こす（整合検証つき）。"""
        return cls(name, strategy.brand, goal_kpi, list(channels)).validate_against(strategy)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "brand": self.brand.value,
            "goal_kpi": self.goal_kpi,
            "channels": [c.to_dict() for c in self.channels],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Campaign":
        return cls(
            d["name"],
            BrandSlug(d["brand"]),
            d["goal_kpi"],
            [Channel.from_dict(c) for c in d.get("channels", [])],
        )
