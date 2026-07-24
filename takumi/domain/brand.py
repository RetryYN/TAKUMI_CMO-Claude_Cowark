"""Brand 集約 — マルチブランドの分離単位。

ユビキタス言語との対応（docs/domain-model.md）:
    ブランド        = Brand（集約ルート）
    ブランドslug    = BrandSlug（値オブジェクト）
    ブランド区画    = BrandPartition（値オブジェクト）
    ブランド台帳    = BrandRegistry（集約）

不変条件:
    1. slug 一意（BrandRegistry）
    2. 区画隔離（BrandPartition.contains）
    3. アクティブ確定前段（BrandRegistry.active）
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# slug: 小文字英数字とハイフン。先頭末尾はハイフン不可。2〜40字。
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
_SLUG_MIN = 2
_SLUG_MAX = 40

_BRANDS_ROOT = "knowledge/brands"


@dataclass(frozen=True)
class BrandSlug:
    """ブランドの不変な識別子（区画ディレクトリ名）。"""

    value: str

    def __post_init__(self) -> None:
        v = self.value
        if not isinstance(v, str) or not (_SLUG_MIN <= len(v) <= _SLUG_MAX):
            raise ValueError(f"ブランドslugは{_SLUG_MIN}〜{_SLUG_MAX}字: {v!r}")
        if not _SLUG_RE.match(v):
            raise ValueError(
                f"ブランドslugは小文字英数字とハイフンのみ・先頭末尾ハイフン不可: {v!r}"
            )

    def __str__(self) -> str:
        return self.value


class BrandStatus(Enum):
    """ブランドの状態。"""

    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class BrandPartition:
    """ブランドの記憶区画 `knowledge/brands/<slug>/`。他区画から隔離される。"""

    slug: BrandSlug

    @property
    def base(self) -> str:
        return f"{_BRANDS_ROOT}/{self.slug.value}"

    def resolve(self, relative: str) -> str:
        """区画内の相対パスを絶対（リポジトリ相対）パスへ。"""
        return f"{self.base}/{relative.lstrip('/')}"

    def contains(self, path: str) -> bool:
        """path がこの区画（base 自身または base/ 配下）に属するか。

        兄弟区画（例: acme に対する acme-2）の prefix 誤マッチを防ぐ。
        """
        p = path.strip().rstrip("/")
        return p == self.base or p.startswith(self.base + "/")


@dataclass
class Brand:
    """ブランド（集約ルート）。同一性は slug。"""

    slug: BrandSlug
    name: str
    status: BrandStatus = BrandStatus.ACTIVE
    created: str | None = None

    @classmethod
    def new(
        cls,
        slug: str,
        name: str,
        status: BrandStatus = BrandStatus.ACTIVE,
        created: str | None = None,
    ) -> "Brand":
        return cls(BrandSlug(slug), name, status, created)

    @property
    def partition(self) -> BrandPartition:
        return BrandPartition(self.slug)

    def to_dict(self) -> dict:
        return {
            "slug": self.slug.value,
            "name": self.name,
            "status": self.status.value,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Brand":
        return cls(
            BrandSlug(d["slug"]),
            d["name"],
            BrandStatus(d["status"]),
            d.get("created"),
        )


class BrandRegistry:
    """ブランド台帳（集約）— 全ブランドの集合とアクティブブランドの指し先。

    永続化先: knowledge/brands.yaml（brands）+ knowledge/.active-brand（active）。
    """

    def __init__(self) -> None:
        self._brands: dict[str, Brand] = {}
        self._active_slug: str | None = None

    # --- 登録・取得 ---
    def register(self, brand: Brand) -> Brand:
        key = brand.slug.value
        if key in self._brands:  # 不変条件1: slug 一意
            raise ValueError(f"slug は既に登録済み: {key!r}")
        self._brands[key] = brand
        return brand

    def get(self, slug: str) -> Brand:
        return self._brands[slug]

    def slugs(self) -> list[str]:
        return list(self._brands.keys())

    def brands(self) -> list[Brand]:
        return list(self._brands.values())

    def __len__(self) -> int:
        return len(self._brands)

    # --- アクティブブランド ---
    @property
    def active(self) -> Brand | None:
        if self._active_slug is None:
            return None
        return self._brands[self._active_slug]

    def set_active(self, slug: str) -> None:
        if slug not in self._brands:  # 未登録はアクティブにできない
            raise KeyError(slug)
        self._active_slug = slug

    def archive(self, slug: str) -> None:
        brand = self._brands[slug]  # 未登録は KeyError
        brand.status = BrandStatus.ARCHIVED
        if self._active_slug == slug:  # アーカイブ済みはアクティブから外す
            self._active_slug = None

    # --- 永続化 ---
    def to_dict(self) -> dict:
        return {
            "active": self._active_slug,
            "brands": [b.to_dict() for b in self._brands.values()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BrandRegistry":
        reg = cls()
        for bd in d.get("brands", []):
            reg.register(Brand.from_dict(bd))
        active = d.get("active")
        if active:
            reg.set_active(active)
        return reg

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BrandRegistry):
            return NotImplemented
        return (
            self._brands == other._brands
            and self._active_slug == other._active_slug
        )
