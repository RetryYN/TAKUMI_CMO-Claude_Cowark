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

from .paid_guard import EN_PAID_METRICS, JA_PAID_METRICS, find_paid_token


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
        hit = find_paid_token(self.name, JA_PAID_METRICS, EN_PAID_METRICS)
        if hit:
            raise ValueError(
                f"KPIツリーに有料指標は置けません（ゼロ広告費）: {self.name!r}（検出語: {hit}）"
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

    def find(self, name: str) -> KpiNode | None:
        """名前でノードを引く（同名は先に見つかった方。ツリー内で名前は一意に保つ）。"""
        for node in self._walk(self.root):
            if node.name == name:
                return node
        return None

    def leaves_under(self, name: str) -> list[str]:
        """指定ノード配下の葉の名前。ノード自身が葉ならそれ自身を返す。

        ∞の下り（UpstreamLoop.hand_down）で「この目標のために手元で動かす指標」を出す。
        """
        node = self.find(name)
        if node is None:
            raise ValueError(f"KPIツリーにありません: {name!r}")
        return [n.name for n in self._walk(node) if not n.children]

    def to_dict(self) -> dict:
        return {"root": self.root.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "KpiTree":
        return cls(KpiNode.from_dict(d["root"]))
