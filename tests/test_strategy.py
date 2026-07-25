"""Strategy エンティティの単体テスト（TDD: 実装より先に書く）。

ドメインモデル（docs/domain-model.md）: 上流ループの産物。KPIツリーを背骨として持ち、
ロードマップの各施策は必ずツリーのノード（ドライバー）に紐づく。
「どの指標を動かすのか言えない施策」を作らせないための不変条件。
"""
import unittest

from takumi.domain.brand import BrandSlug
from takumi.domain.channel import Channel, ChannelKind
from takumi.domain.kpi_tree import KpiKind, KpiNode, KpiTree
from takumi.domain.strategy import RoadmapItem, Strategy


def _tree() -> KpiTree:
    return KpiTree(
        KpiNode("指名検索のシェア", KpiKind.LAGGING, [
            KpiNode("オーガニック流入", KpiKind.LEADING, [
                KpiNode("記事公開数", KpiKind.LEADING),
            ]),
            KpiNode("エンゲージ率", KpiKind.LEADING),
        ])
    )


def _item(driver: str = "記事公開数") -> RoadmapItem:
    return RoadmapItem("導入事例を月4本", Channel("自社ブログ", ChannelKind.OWNED_MEDIA), driver)


class TestRoadmapItem(unittest.TestCase):
    def test_create(self):
        item = _item()
        self.assertEqual(item.driver, "記事公開数")
        self.assertEqual(item.channel.kind, ChannelKind.OWNED_MEDIA)

    def test_blank_title_rejected(self):
        with self.assertRaises(ValueError):
            RoadmapItem("  ", Channel("X", ChannelKind.SNS), "記事公開数")


class TestStrategy(unittest.TestCase):
    def _strategy(self, items=None) -> Strategy:
        return Strategy(
            BrandSlug("acme"),
            "検索で見つかる前に思い出される会社になる",
            _tree(),
            list(items if items is not None else [_item()]),
        )

    def test_create(self):
        s = self._strategy()
        self.assertEqual(s.brand.value, "acme")
        self.assertEqual(len(s.roadmap), 1)

    def test_positioning_must_be_one_line(self):
        for bad in ("", "   ", "1行目\n2行目"):
            with self.assertRaises(ValueError, msg=f"{bad!r} は却下されるべき"):
                Strategy(BrandSlug("acme"), bad, _tree(), [])

    def test_roadmap_driver_must_exist_in_tree(self):
        """ツリーに無い指標を動かすと称する施策は作れない。"""
        with self.assertRaises(ValueError):
            self._strategy([_item("被リンク数")])

    def test_roadmap_can_be_empty_at_first(self):
        """立案直後（ツリーだけ引いた段階）は施策ゼロを許す。"""
        self.assertEqual(self._strategy([]).roadmap, [])

    def test_paid_metric_cannot_enter_via_tree(self):
        with self.assertRaises(ValueError):
            KpiTree(KpiNode("ROAS", KpiKind.LAGGING))

    def test_drivers_and_undriven_leaves(self):
        s = self._strategy()
        self.assertEqual(s.drivers(), ["記事公開数"])
        # 施策の紐づかない葉＝動かす当てのない指標を洗い出せる
        self.assertEqual(s.undriven_leaves(), ["エンゲージ率"])

    def test_roundtrip(self):
        s = self._strategy()
        self.assertEqual(Strategy.from_dict(s.to_dict()), s)


if __name__ == "__main__":
    unittest.main()
