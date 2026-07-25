"""Channel 値オブジェクト — 施策を載せる媒体。

ユビキタス言語（docs/domain-model.md）:
    媒体   = Channel（値オブジェクト）
    媒体種別 = ChannelKind（値オブジェクト）

不変条件（ゼロ広告費）:
    媒体はオーガニックのみ。有料出稿・課金導線を伴う媒体は値オブジェクトの段階で作れない。
    KpiNode が有料「指標」を拒むのと対になり、施策の「入れ物」の側からも有料前提を締め出す。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .enum_guard import require_enum
from .paid_guard import EN_PAID_CHANNELS, JA_PAID_CHANNELS, find_paid_token


class ChannelKind(Enum):
    """媒体の種別（すべてオーガニック）。

    マーケティングの三分類 Owned / Earned / Paid のうち、**Paid は構造的に持たない**
    （ゼロ広告費）。SNS〜メールは Owned（自社の場）、EARNED は他者の場・他者の口。
    """

    SNS = "SNS"
    CONTENT = "コンテンツ"
    WEBSITE = "Webサイト"
    OWNED_MEDIA = "オウンドメディア"
    EMAIL = "メール"
    EARNED = "広報・連携"   # 他者の場を借りる（広報・パートナー・コミュニティ）


@dataclass(frozen=True)
class Channel:
    """オーガニック媒体（値オブジェクト）。同一性は名前と種別。"""

    name: str
    kind: ChannelKind

    def __post_init__(self) -> None:
        require_enum(self.kind, ChannelKind, "kind（媒体の種別）")
        if not isinstance(self.name, str) or not self.name.strip(" 　"):
            raise ValueError(f"媒体名が空です: {self.name!r}")
        hit = find_paid_token(self.name, JA_PAID_CHANNELS, EN_PAID_CHANNELS)
        if hit:
            raise ValueError(
                f"有料出稿の媒体は扱えません（ゼロ広告費）: {self.name!r}（検出語: {hit}）"
            )

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind.value}

    @classmethod
    def from_dict(cls, d: dict) -> "Channel":
        return cls(d["name"], ChannelKind(d["kind"]))
