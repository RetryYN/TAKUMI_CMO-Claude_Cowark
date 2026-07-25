"""匠の∞ループ（上流/下流の受け渡し規則）の単体テスト（TDD: 実装より先に書く）。

ドメインモデル（docs/domain-model.md）: 上流 UpstreamLoop（戦略）と下流 DownstreamLoop（実行）が
**計画**（下り）と**計測**（上り）で結ばれる。両ループが共有する背骨は KpiTree。
ここで守るのは「受け渡しの両端が必ず KPIツリーのノードを経由すること」— これが切れると
∞ が閉じず、実行の結果が戦略に返らない。
"""
import unittest

from takumi.domain.brand import BrandSlug
from takumi.domain.campaign import Campaign
from takumi.domain.channel import Channel, ChannelKind
from takumi.domain.kpi_tree import KpiKind, KpiNode, KpiTree
from takumi.domain.loop import (
    DownstreamLoop,
    MeasurementHandoff,
    PlanHandoff,
    UpstreamLoop,
)
from takumi.domain.strategy import RoadmapItem, Strategy

_X = Channel("X", ChannelKind.SNS)
_BLOG = Channel("自社ブログ", ChannelKind.OWNED_MEDIA)


def _strategy() -> Strategy:
    tree = KpiTree(
        KpiNode("指名検索のシェア", KpiKind.LAGGING, [
            KpiNode("オーガニック流入", KpiKind.LEADING, [
                KpiNode("記事公開数", KpiKind.LEADING),
            ]),
            KpiNode("エンゲージ率", KpiKind.LEADING),
        ])
    )
    return Strategy(
        BrandSlug("acme"),
        "検索で見つかる前に思い出される会社になる",
        tree,
        [RoadmapItem("導入事例を月4本", _BLOG, "記事公開数")],
    )


class TestUpstreamLoop(unittest.TestCase):
    """∞の下り: 戦略 → 実行ブリーフ。"""

    def test_hand_down_produces_brief(self):
        s = _strategy()
        c = Campaign.for_strategy(s, "春の事例特集", "オーガニック流入", [_X, _BLOG])
        brief = UpstreamLoop.hand_down(s, c)
        self.assertIsInstance(brief, PlanHandoff)
        self.assertEqual(brief.brand, s.brand)
        self.assertEqual(brief.goal_kpi, "オーガニック流入")
        self.assertEqual(brief.channels, [_X, _BLOG])
        # 目標KPIの配下にある葉＝この施策で実際に動かす手元の指標
        self.assertEqual(brief.driver_leaves, ["記事公開数"])

    def test_hand_down_rejects_campaign_of_other_brand(self):
        s = _strategy()
        c = Campaign("春の事例特集", BrandSlug("beta"), "オーガニック流入", [_X])
        with self.assertRaises(ValueError):
            UpstreamLoop.hand_down(s, c)

    def test_hand_down_rejects_goal_outside_the_tree(self):
        s = _strategy()
        c = Campaign("春の事例特集", BrandSlug("acme"), "フォロワー数", [_X])
        with self.assertRaises(ValueError):
            UpstreamLoop.hand_down(s, c)


class TestDownstreamLoop(unittest.TestCase):
    """∞の上り: 実測 → KPIツリーへ返す。"""

    def test_hand_up_accepts_readings_on_tree_nodes(self):
        s = _strategy()
        up = DownstreamLoop.hand_up(s, {"記事公開数": 4.0, "オーガニック流入": 1200.0})
        self.assertIsInstance(up, MeasurementHandoff)
        self.assertEqual(up.brand, s.brand)
        self.assertEqual(up.readings["記事公開数"], 4.0)

    def test_hand_up_rejects_unknown_node(self):
        """ツリーに無い指標は上流に返せない（計測が戦略に紐づかなくなる）。"""
        s = _strategy()
        with self.assertRaises(ValueError):
            DownstreamLoop.hand_up(s, {"フォロワー数": 8000.0})

    def test_stalled_nodes_flags_replanning(self):
        """前回比が閾値未満のノード＝ /戦略 の再立案フラグ。"""
        s = _strategy()
        previous = {"記事公開数": 4.0, "オーガニック流入": 1000.0, "エンゲージ率": 0.05}
        current = {"記事公開数": 4.0, "オーガニック流入": 1200.0, "エンゲージ率": 0.05}
        stalled = DownstreamLoop.stalled_nodes(s, previous, current, threshold=0.05)
        self.assertIn("記事公開数", stalled)     # 伸び 0%
        self.assertIn("エンゲージ率", stalled)   # 伸び 0%
        self.assertNotIn("オーガニック流入", stalled)  # 伸び 20%

    def test_stalled_nodes_rejects_unknown_node(self):
        s = _strategy()
        with self.assertRaises(ValueError):
            DownstreamLoop.stalled_nodes(s, {"フォロワー数": 1.0}, {"フォロワー数": 1.0})

    def test_unmeasured_leaves(self):
        """一度も測っていない葉を洗い出す（測る当てのない指標の検出）。"""
        s = _strategy()
        self.assertEqual(
            DownstreamLoop.unmeasured_leaves(s, {"記事公開数": 4.0}),
            ["エンゲージ率"],
        )


class TestLoopClosesTheInfinity(unittest.TestCase):
    def test_round_trip_down_then_up(self):
        """下って上る一周が、同じ KPIツリーのノードを経由して閉じる。"""
        s = _strategy()
        c = Campaign.for_strategy(s, "春の事例特集", "オーガニック流入", [_BLOG])
        brief = UpstreamLoop.hand_down(s, c)
        readings = {leaf: 1.0 for leaf in brief.driver_leaves}
        up = DownstreamLoop.hand_up(s, readings)
        self.assertEqual(set(up.readings), set(brief.driver_leaves))


if __name__ == "__main__":
    unittest.main()
