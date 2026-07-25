"""ドメインが宣言する媒体（ChannelKind）に、実行パックが存在することの突合テスト。

2026-07-25 の機能CHECK で検出: `ChannelKind.EMAIL` をドメインが宣言し、`/キャンペーン` が
参加媒体として選べ、`pre-send-verifier` が「メール配信は不可逆送出」と規定しているのに、
**実行する手順書が存在しなかった**。SNS・コンテンツ・Webサイト・オウンドメディアには
すべてパックがあり、メールだけが穴だった。

「ドメインに媒体を足したら実行パックも足す」を機械で強制する。
逆に「パックを消したのに ChannelKind が残る」も落とす。
"""
import re
import unittest
from pathlib import Path

from takumi.domain.channel import ChannelKind

ROOT = Path(__file__).resolve().parent.parent

# ChannelKind → その媒体を実行する手順書
CHANNEL_PACKS = {
    ChannelKind.SNS: "procedures/takumi-sns.md",
    ChannelKind.CONTENT: "procedures/takumi-content.md",
    ChannelKind.WEBSITE: "procedures/takumi-website.md",
    ChannelKind.OWNED_MEDIA: "procedures/takumi-ownedmedia.md",
    ChannelKind.EMAIL: "procedures/takumi-email.md",
    ChannelKind.EARNED: "procedures/takumi-pr.md",
}


class TestChannelPacks(unittest.TestCase):
    def test_every_channel_kind_has_a_pack(self):
        """媒体を宣言したら実行パックを持つ。"""
        for kind in ChannelKind:
            self.assertIn(
                kind, CHANNEL_PACKS,
                f"{kind.name} に対応する実行パックがこの表に無い（媒体を足したら表も更新する）",
            )
            path = ROOT / CHANNEL_PACKS[kind]
            self.assertTrue(
                path.is_file(),
                f"{kind.value}（{kind.name}）の実行パック {CHANNEL_PACKS[kind]} が存在しない。"
                f"ドメインが宣言した媒体に、実行する手段が無い状態になっている",
            )

    def test_table_has_no_stale_entries(self):
        """パック表に、ドメインに無い媒体が残っていない。"""
        for kind in CHANNEL_PACKS:
            self.assertIn(kind, set(ChannelKind), f"{kind} は ChannelKind に存在しない")

    def test_every_pack_is_reachable_from_a_command(self):
        """各パックに、いずれかのコマンドから辿り着ける（孤児でない）。

        2026-07-26 にコマンドを20本→9本へ束ねたため、**コマンドが直接パックを参照するとは
        限らない**（例: /匠発信 → takumi-publish → takumi-sns）。守りたいのは
        「文字列がコマンドファイルに載っていること」ではなく「**利用者から辿り着けること**」
        なので、玄関の手順書を経由して実際に辿る。
        """
        proc_text = {
            p.stem: p.read_text(encoding="utf-8")
            for p in (ROOT / "procedures").glob("takumi-*.md")
        }
        ref = re.compile(r"procedures/(takumi-[a-z-]+)\.md")
        reachable: set[str] = set()
        frontier: list[str] = []
        for c in (ROOT / "commands").glob("*.md"):
            for name in ref.findall(c.read_text(encoding="utf-8")):
                if name not in reachable:
                    reachable.add(name)
                    frontier.append(name)
        while frontier:
            for name in ref.findall(proc_text.get(frontier.pop(), "")):
                if name not in reachable and name in proc_text:
                    reachable.add(name)
                    frontier.append(name)

        for kind, rel in CHANNEL_PACKS.items():
            stem = Path(rel).stem
            self.assertIn(
                stem, reachable,
                f"{kind.value} のパック {Path(rel).name} にコマンドから辿り着けない"
                f"（束ねた玄関の手順書に振り分けを書く。"
                f"ファイルは在るので参照切れ検査には掛からない＝いちばん気づけない壊れ方）",
            )

    def test_campaign_lists_every_channel(self):
        """/キャンペーン の参加媒体の選択肢が ChannelKind と一致する。

        キャンペーンは複数媒体を束ねる統括単位なので、ここに載っていない媒体は
        実質的にキャンペーンへ組み込めない。
        """
        text = (ROOT / "procedures/takumi-campaign.md").read_text(encoding="utf-8")
        section = re.search(r"参加媒体の選定.*?\n", text, re.S)
        self.assertIsNotNone(section, "参加媒体の選定の記述が見つからない")
        for kind in ChannelKind:
            self.assertIn(
                kind.value, section.group(0),
                f"/キャンペーン の参加媒体に {kind.value} が載っていない",
            )


if __name__ == "__main__":
    unittest.main()
