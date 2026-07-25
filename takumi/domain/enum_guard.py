"""Enum 型の共通検査 — 「宣言された種別」が本物の Enum であることを実行時に確かめる。

**なぜコードにするか**: `@dataclass` の型注釈は実行時に検証されない。`kind: PremiumKind` と
書いてあっても、呼び出し側が `kind="totsuke"` のような**文字列**を渡せばそのまま入る。
すると `if self.kind is PremiumKind.TOTSUKE` のような分岐が**すべて偽**になり、
上限チェックを一度も通らずに素通りする。フェイルオープン（黙って通る）であり、
「機械で止まる」という設計の前提そのものが崩れる。

2026-07-26 の Tier 2 perfect ラン（F-1）で `PremiumOffer(kind='total', ...)` が
景品規制の上限超過を素通りさせることを実測した。ドメイン層の Enum フィールド6箇所すべてが
同じ穴を持っていたため、個別の場当たりではなく共通ガードにして横展開する。

**判定不能は「問題なし」ではない** — 種別が特定できない時点で ValueError にして止める。
"""
from __future__ import annotations

from enum import Enum


def require_enum(value, enum_cls: type[Enum], field_name: str) -> None:
    """`value` が `enum_cls` のメンバーでなければ ValueError を投げる。

    文字列で「それらしい値」を渡された場合も**受け付けない**。似た文字列を enum に
    読み替える親切設計にはしない — 読み替えは推測であり、種別の取り違えを隠すため。
    呼び出し側に enum を明示させることが、そのまま「宣言したのは誰か」の記録になる。
    """
    if not isinstance(value, enum_cls):
        allowed = " / ".join(f"{enum_cls.__name__}.{m.name}" for m in enum_cls)
        raise ValueError(
            f"{field_name} は {enum_cls.__name__} で宣言してください"
            f"（受け取った値: {value!r} / 型: {type(value).__name__}）。"
            f"指定できるのは {allowed}。"
            "文字列は受け付けません（種別の取り違えが機械検査をすり抜けるため）"
        )
