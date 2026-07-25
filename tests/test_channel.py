"""Channel 値オブジェクトの単体テスト（TDD: 実装より先に書く）。

ドメイン不変条件（docs/domain-model.md）: 媒体はオーガニックのみ。
有料出稿媒体は値オブジェクトの段階で作れない＝ゼロ広告費をコードで強制する。
"""
import unittest

from takumi.domain.channel import Channel, ChannelKind


class TestChannel(unittest.TestCase):
    def test_organic_channels_allowed(self):
        for name, kind in (
            ("X", ChannelKind.SNS),
            ("自社ブログ", ChannelKind.OWNED_MEDIA),
            ("コーポレートサイト", ChannelKind.WEBSITE),
            ("メールマガジン", ChannelKind.EMAIL),
            ("導入事例記事", ChannelKind.CONTENT),
        ):
            self.assertEqual(Channel(name, kind).name, name)

    def test_paid_channels_rejected(self):
        for bad in (
            "Google広告",
            "リスティング広告",
            "Meta広告",
            "Google Ads",
            "PPC",
            "純広告",
            "アフィリエイト",
            "インフルエンサー案件",
            "タイアップ記事",
        ):
            with self.assertRaises(ValueError, msg=f"{bad!r} は有料媒体として拒否されるべき"):
                Channel(bad, ChannelKind.SNS)

    def test_no_false_positive_on_substrings(self):
        """過剰検知もガードの失敗。実在のオーガニック媒体を弾かない。

        2026-07-25 の回帰: "Threads" が "ads" の部分一致で有料媒体と誤判定された。
        """
        for ok in ("Threads", "Roadside Diary", "ヘッドライン特集"):
            self.assertEqual(Channel(ok, ChannelKind.SNS).name, ok)

    def test_blank_name_rejected(self):
        for bad in ("", "   ", "　"):
            with self.assertRaises(ValueError):
                Channel(bad, ChannelKind.SNS)

    def test_value_object_equality(self):
        self.assertEqual(Channel("X", ChannelKind.SNS), Channel("X", ChannelKind.SNS))
        self.assertNotEqual(Channel("X", ChannelKind.SNS), Channel("Threads", ChannelKind.SNS))
        # 値オブジェクトなので集合・辞書のキーにできる
        self.assertEqual(len({Channel("X", ChannelKind.SNS), Channel("X", ChannelKind.SNS)}), 1)

    def test_roundtrip(self):
        c = Channel("自社ブログ", ChannelKind.OWNED_MEDIA)
        self.assertEqual(Channel.from_dict(c.to_dict()), c)


if __name__ == "__main__":
    unittest.main()
