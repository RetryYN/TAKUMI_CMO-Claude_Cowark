"""Campaign エンティティの単体テスト（TDD: 実装より先に書く）。

ドメインモデル（docs/domain-model.md）: 複数媒体を1つの目標の下に束ねる下流の統括単位。
不変条件は「目標KPIが戦略のKPIツリーに実在すること」— キャンペーンが背骨から
浮くと、走らせても上流に返す計測が KPIツリーのどのノードにも紐づかなくなる。
"""
import unittest

from takumi.domain.brand import BrandSlug
from takumi.domain.campaign import Campaign
from takumi.domain.channel import Channel, ChannelKind
from takumi.domain.kpi_tree import KpiKind, KpiNode, KpiTree
from takumi.domain.strategy import RoadmapItem, Strategy

_X = Channel("X", ChannelKind.SNS)
_BLOG = Channel("自社ブログ", ChannelKind.OWNED_MEDIA)


def _strategy() -> Strategy:
    tree = KpiTree(
        KpiNode("指名検索のシェア", KpiKind.LAGGING, [
            KpiNode("オーガニック流入", KpiKind.LEADING, [
                KpiNode("記事公開数", KpiKind.LEADING),
            ]),
        ])
    )
    return Strategy(
        BrandSlug("acme"),
        "検索で見つかる前に思い出される会社になる",
        tree,
        [RoadmapItem("導入事例を月4本", _BLOG, "記事公開数")],
    )


class TestCampaign(unittest.TestCase):
    def test_create(self):
        c = Campaign("春の事例特集", BrandSlug("acme"), "オーガニック流入", [_X, _BLOG])
        self.assertEqual(c.goal_kpi, "オーガニック流入")
        self.assertEqual(len(c.channels), 2)

    def test_requires_at_least_one_channel(self):
        with self.assertRaises(ValueError):
            Campaign("春の事例特集", BrandSlug("acme"), "オーガニック流入", [])

    def test_rejects_duplicate_channels(self):
        with self.assertRaises(ValueError):
            Campaign("春の事例特集", BrandSlug("acme"), "オーガニック流入", [_X, _X])

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            Campaign("  ", BrandSlug("acme"), "オーガニック流入", [_X])

    def test_for_strategy_binds_to_the_tree(self):
        s = _strategy()
        c = Campaign.for_strategy(s, "春の事例特集", "オーガニック流入", [_X, _BLOG])
        self.assertEqual(c.brand, s.brand)

    def test_for_strategy_rejects_goal_outside_the_tree(self):
        """KPIツリーに無い目標は立てられない（背骨から浮いたキャンペーンを作らせない）。"""
        s = _strategy()
        with self.assertRaises(ValueError):
            Campaign.for_strategy(s, "春の事例特集", "フォロワー数", [_X])

    def test_for_strategy_rejects_other_brand(self):
        s = _strategy()
        c = Campaign("春の事例特集", BrandSlug("beta"), "オーガニック流入", [_X])
        with self.assertRaises(ValueError):
            c.validate_against(s)

    def test_roundtrip(self):
        c = Campaign("春の事例特集", BrandSlug("acme"), "オーガニック流入", [_X, _BLOG])
        self.assertEqual(Campaign.from_dict(c.to_dict()), c)


if __name__ == "__main__":
    unittest.main()
