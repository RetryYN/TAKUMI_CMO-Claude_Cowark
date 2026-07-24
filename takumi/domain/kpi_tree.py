"""KpiTree 集約 — 上流ループと下流ループが共有する背骨（KPIツリー）。

ユビキタス言語（docs/domain-model.md）:
    KPIツリー = KpiTree（集約）
    指標ノード = KpiNode（先行/遅行）

不変条件（ゼロ広告費）:
    KPIツリーは有料指標（CAC / LTV / ROAS / CPA / 広告費 等）をノードに持たない。
    オーガニック指標（流入・エンゲージ・被リンク・指名検索 等）のみで組む。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# 有料広告に紐づく指標（部分一致・大文字小文字/空白無視）。ゼロ広告費のためツリーに置けない。
_PAID_METRICS = (
    "cac", "ltv", "roas", "cpa", "cpc", "cpm",
    "adspend", "広告費", "広告予算", "出稿", "入札",
)


class KpiKind(Enum):
    """指標の種別。"""

    LEADING = "先行"   # 先行指標（打ち手に近い・早く動く）
    LAGGING = "遅行"   # 遅行指標（成果に近い・遅れて動く）


@dataclass
class KpiNode:
    """KPIツリーの指標ノード。"""

    name: str
    kind: KpiKind
    children: list["KpiNode"] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized = self.name.lower().replace(" ", "").replace("　", "")
        for token in _PAID_METRICS:
            if token in normalized:
                raise ValueError(
                    f"KPIツリーに有料指標は置けません（ゼロ広告費）: {self.name!r}"
                )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KpiNode":
        return cls(
            d["name"],
            KpiKind(d["kind"]),
            [cls.from_dict(c) for c in d.get("children", [])],
        )


@dataclass
class KpiTree:
    """KPIツリー（集約）。北極星指標を根に持つ。"""

    root: KpiNode

    def _walk(self, node: KpiNode):
        yield node
        for child in node.children:
            yield from self._walk(child)

    def all_names(self) -> list[str]:
        return [n.name for n in self._walk(self.root)]

    def leaves(self) -> list[KpiNode]:
        return [n for n in self._walk(self.root) if not n.children]

    def to_dict(self) -> dict:
        return {"root": self.root.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "KpiTree":
        return cls(KpiNode.from_dict(d["root"]))
