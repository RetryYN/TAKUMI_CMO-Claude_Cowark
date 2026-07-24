"""Brand 集約の単体テスト（TDD: 実装より先に書く）。

ドメインモデル: docs/domain-model.md の Brand 集約と不変条件に対応する。
"""
import unittest

from takumi.domain.brand import (
    Brand,
    BrandPartition,
    BrandRegistry,
    BrandSlug,
    BrandStatus,
)


class TestBrandSlug(unittest.TestCase):
    def test_valid_slugs(self):
        for s in ("acme", "acme-cola", "brand2", "a1", "x" * 40):
            self.assertEqual(BrandSlug(s).value, s)

    def test_invalid_slugs_rejected(self):
        for s in (
            "",           # 空
            "a",          # 短すぎ（最小2）
            "x" * 41,     # 長すぎ（最大40）
            "Acme",       # 大文字
            "acme cola",  # 空白
            "-acme",      # 先頭ハイフン
            "acme-",      # 末尾ハイフン
            "acme_cola",  # アンダースコア
            "café",       # 非ASCII
            "acme/x",     # スラッシュ（区画横断の芽）
        ):
            with self.assertRaises(ValueError, msg=f"{s!r} は拒否されるべき"):
                BrandSlug(s)

    def test_value_object_semantics(self):
        self.assertEqual(BrandSlug("acme"), BrandSlug("acme"))
        self.assertNotEqual(BrandSlug("acme"), BrandSlug("other"))
        self.assertEqual(str(BrandSlug("acme")), "acme")
        # 不変（frozen）
        with self.assertRaises(Exception):
            BrandSlug("acme").value = "x"  # type: ignore[misc]


class TestBrandPartition(unittest.TestCase):
    def test_base_path(self):
        p = BrandPartition(BrandSlug("acme"))
        self.assertEqual(p.base, "knowledge/brands/acme")

    def test_resolve(self):
        p = BrandPartition(BrandSlug("acme"))
        self.assertEqual(
            p.resolve("strategy/kpi-tree.yaml"),
            "knowledge/brands/acme/strategy/kpi-tree.yaml",
        )

    def test_contains_isolation(self):
        p = BrandPartition(BrandSlug("acme"))
        self.assertTrue(p.contains("knowledge/brands/acme"))
        self.assertTrue(p.contains("knowledge/brands/acme/brand.yaml"))
        self.assertTrue(p.contains("knowledge/brands/acme/strategy/kpi-tree.yaml"))
        # 他ブランド区画は含まない（不変条件2: 区画隔離）
        self.assertFalse(p.contains("knowledge/brands/other/brand.yaml"))
        # 兄弟の prefix 誤マッチを防ぐ（acme-2 は acme 区画ではない）
        self.assertFalse(p.contains("knowledge/brands/acme-2/brand.yaml"))
        # 区画外
        self.assertFalse(p.contains("knowledge/logs/x.md"))


class TestBrand(unittest.TestCase):
    def test_new_defaults_active(self):
        b = Brand.new("acme", "Acme Inc")
        self.assertEqual(b.slug, BrandSlug("acme"))
        self.assertEqual(b.name, "Acme Inc")
        self.assertEqual(b.status, BrandStatus.ACTIVE)
        self.assertEqual(b.partition.base, "knowledge/brands/acme")

    def test_roundtrip_dict(self):
        b = Brand.new("acme", "Acme Inc", created="2026-07-25")
        self.assertEqual(Brand.from_dict(b.to_dict()), b)


class TestBrandRegistry(unittest.TestCase):
    def test_register_and_get(self):
        reg = BrandRegistry()
        reg.register(Brand.new("acme", "Acme"))
        self.assertEqual(reg.get("acme").name, "Acme")
        self.assertEqual(len(reg), 1)

    def test_duplicate_slug_rejected(self):
        reg = BrandRegistry()
        reg.register(Brand.new("acme", "Acme"))
        with self.assertRaises(ValueError):  # 不変条件1: slug 一意
            reg.register(Brand.new("acme", "Dup"))

    def test_active_pointer(self):
        reg = BrandRegistry()
        self.assertIsNone(reg.active)
        reg.register(Brand.new("acme", "Acme"))
        reg.register(Brand.new("beta", "Beta"))
        reg.set_active("beta")
        self.assertEqual(reg.active.slug, BrandSlug("beta"))
        with self.assertRaises(KeyError):
            reg.set_active("ghost")  # 未登録はアクティブにできない

    def test_archive_clears_active(self):
        reg = BrandRegistry()
        reg.register(Brand.new("acme", "Acme"))
        reg.set_active("acme")
        reg.archive("acme")
        self.assertEqual(reg.get("acme").status, BrandStatus.ARCHIVED)
        self.assertIsNone(reg.active)  # アーカイブ済みはアクティブから外れる

    def test_roundtrip_dict(self):
        reg = BrandRegistry()
        reg.register(Brand.new("acme", "Acme", created="2026-07-25"))
        reg.register(Brand.new("beta", "Beta", created="2026-07-25"))
        reg.set_active("acme")
        self.assertEqual(BrandRegistry.from_dict(reg.to_dict()), reg)


if __name__ == "__main__":
    unittest.main()
