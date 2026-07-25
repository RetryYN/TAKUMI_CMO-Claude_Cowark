"""Strategy エンティティ — 上流（戦略）ループの産物。

ユビキタス言語（docs/domain-model.md）:
    戦略           = Strategy（エンティティ）
    ロードマップ項目 = RoadmapItem（値オブジェクト）

不変条件:
    1. ブランドに属する（BrandSlug）。区画をまたがない。
    2. ポジショニングは1文（空・複数行は不可）。
    3. ロードマップの各施策は KPIツリーに実在するノード（ドライバー）に紐づく。
       「どの指標を動かすのか言えない施策」を持てない＝ツリーが背骨として機能する。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .brand import BrandSlug
from .channel import Channel
from .kpi_tree import KpiTree


@dataclass(frozen=True)
class RoadmapItem:
    """施策ロードマップの1項目（値オブジェクト）。"""

    title: str
    channel: Channel
    driver: str  # KPIツリー上のノード名。この施策で動かす指標

    def __post_init__(self) -> None:
        if not self.title.strip(" 　"):
            raise ValueError("施策のタイトルが空です")
        if not self.driver.strip(" 　"):
            raise ValueError("施策が動かすドライバー（KPIノード名）が空です")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "channel": self.channel.to_dict(),
            "driver": self.driver,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RoadmapItem":
        return cls(d["title"], Channel.from_dict(d["channel"]), d["driver"])


@dataclass
class Strategy:
    """戦略（エンティティ）。同一性はブランド — 1ブランドに1つの現行戦略。"""

    brand: BrandSlug
    positioning: str
    kpi_tree: KpiTree
    roadmap: list[RoadmapItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        p = self.positioning.strip(" 　")
        if not p:
            raise ValueError("ポジショニングが空です（誰に・何を・なぜ我々から を1文で）")
        if "\n" in p:
            raise ValueError(f"ポジショニングは1文で書きます（改行不可）: {self.positioning!r}")
        names = set(self.kpi_tree.all_names())
        for item in self.roadmap:
            if item.driver not in names:
                raise ValueError(
                    f"施策 {item.title!r} のドライバー {item.driver!r} が "
                    f"KPIツリーにありません（施策は必ずツリーのノードに紐づける）"
                )

    def drivers(self) -> list[str]:
        """ロードマップが動かすドライバー名（重複を除き、登場順）。"""
        seen: list[str] = []
        for item in self.roadmap:
            if item.driver not in seen:
                seen.append(item.driver)
        return seen

    def undriven_leaves(self) -> list[str]:
        """施策の紐づいていない葉＝動かす当てのない指標。"""
        driven = set(self.drivers())
        return [n.name for n in self.kpi_tree.leaves() if n.name not in driven]

    def channels(self) -> list[Channel]:
        """ロードマップが使う媒体（重複を除き、登場順）。"""
        seen: list[Channel] = []
        for item in self.roadmap:
            if item.channel not in seen:
                seen.append(item.channel)
        return seen

    def to_dict(self) -> dict:
        return {
            "brand": self.brand.value,
            "positioning": self.positioning,
            "kpi_tree": self.kpi_tree.to_dict(),
            "roadmap": [i.to_dict() for i in self.roadmap],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Strategy":
        return cls(
            BrandSlug(d["brand"]),
            d["positioning"],
            KpiTree.from_dict(d["kpi_tree"]),
            [RoadmapItem.from_dict(i) for i in d.get("roadmap", [])],
        )
