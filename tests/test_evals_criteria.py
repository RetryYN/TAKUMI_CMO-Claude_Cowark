"""golden タスクの PASS 基準が「対象が達成しうる内容」になっているかの突合テスト。

`scripts/lint.py` #17 は「全スキル・全エージェントに golden タスクがあるか」（網羅）を見るが、
**その基準を対象が満たせるか**は見ない。2026-07-25 に2件の欠陥が見つかった:

- G34 が `deliverable-writer` にアーティファクト発行を要求していた
  （同エージェントの tools は Read/Write/Edit/Glob/Grep。発行手段を持たない）
- G20 が `risk-forecaster` に「争点」という合議側の語彙で回答を求めていた
  （同エージェントの出力形式は FORECAST / 兆候 / 最も安い保険）

どちらも**永久に PASS しない golden タスク**であり、回しても「腕が落ちた」としか読めない。
基準が要求する具体語が対象の本文に実在することを、ここで機械的に固定する。

新しい golden タスクを追加したら、このテーブルにも1行足すこと。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# golden タスク → (対象ファイル, PASS 基準が依拠する具体語)
CRITERIA = {
    "G35 voc-research-jp": ("skills/voc-research-jp/SKILL.md",
                            ["未来と意見ではなく、過去と行動", "生存者バイアス"]),
    "G36 messaging-design-jp": ("skills/messaging-design-jp/SKILL.md",
                                ["最大3つ", "証拠のない柱", "形容詞でできている"]),
    "G10 seo-jp": ("skills/seo-jp/SKILL.md", ["検索ボリュームだけでテーマを選ばない", "一次情報"]),
    "G11 content-design": ("skills/content-design/SKILL.md", ["加工", "構成"]),
    "G12 storytelling": ("skills/storytelling/SKILL.md", ["葛藤", "転機", "一人称", "書き始めない"]),
    "G13 logical-writing": ("skills/logical-writing/SKILL.md", ["相関と因果", "要因未特定"]),
    "G14 business-writing": ("skills/business-writing/SKILL.md", ["断りやすさ", "督促"]),
    "G15 sales-writing": ("skills/sales-writing/SKILL.md", ["創作", "実在する事例のみ"]),
    "G16 sns-jp": ("skills/sns-jp/SKILL.md", ["プラットフォーム別"]),
    "G17 video-script": ("skills/video-script/SKILL.md", ["フック", "絵コンテ", "出稿"]),
    "G22 psych-ux-jp": ("skills/psych-ux-jp/SKILL.md", ["配色判断表", "視線"]),
    "G23 gtm-jp": ("skills/gtm-jp/SKILL.md",
                   ["Scroll Depth Threshold", "カンマ区切り", "ウィンドウの読み込み", "プレビュー"]),
    "G24 ga4-jp": ("skills/ga4-jp/SKILL.md", ["48", "(other)"]),
    "G25 kpi-design-jp": ("skills/kpi-design-jp/SKILL.md", ["虚栄", "ガードレール", "何を変える"]),
    "G26 search-console-jp": ("skills/search-console-jp/SKILL.md", ["削除ツール", "一時的"]),
    "G29 design-evidence-jp": ("skills/design-evidence-jp/SKILL.md",
                               ["16px以上", "12px未満禁止", "20〜35字"]),
    "G30 web-design": ("skills/web-design/SKILL.md", ["レイアウト", "タイポグラフィ", "カラー"]),
    "G33 cro-jp": ("skills/cro-jp/SKILL.md", ["ダークパターン", "偽のカウントダウン"]),
    "G27 cmo-strategist": ("agents/cmo-strategist.md", ["有料指標", "北極星", "未確認"]),
    "G18/G19 privacy-auditor": ("agents/privacy-auditor.md", ["取り消せない", "過剰な NO-GO"]),
    "G20 risk-forecaster": ("agents/risk-forecaster.md", ["FORECAST", "兆候", "最も安い保険"]),
    "G21 strategy-advisor": ("agents/strategy-advisor.md", ["RETHINK", "GO-WITH-CHANGES"]),
    "G34 deliverable-writer": ("agents/deliverable-writer.md", ["report-template", "捏造しない"]),
}


class TestEvalsCriteriaAreAchievable(unittest.TestCase):
    def test_criteria_terms_exist_in_target(self):
        """PASS 基準が依拠する語が、対象の本文に実在すること。"""
        missing = {}
        for name, (rel, terms) in CRITERIA.items():
            text = (ROOT / rel).read_text(encoding="utf-8")
            gaps = [t for t in terms if t not in text]
            if gaps:
                missing[name] = (rel, gaps)
        self.assertEqual(
            missing, {},
            f"golden タスクの PASS 基準が対象に存在しない内容を要求している: {missing}",
        )

    def test_every_listed_target_exists(self):
        for name, (rel, _) in CRITERIA.items():
            self.assertTrue((ROOT / rel).is_file(), f"{name}: 対象 {rel} が存在しない")

    def test_agent_criteria_do_not_require_absent_tools(self):
        """エージェント向けの基準が、そのエージェントの tools に無い能力を要求していないこと。

        G34 の再発防止。発行系（アーティファクト・ファイル送付）は tools に現れないため、
        エージェントの golden タスクの基準に発行の語を混ぜない。
        """
        import re
        evals = (ROOT / "docs/evals.md").read_text(encoding="utf-8")
        publish_words = ("アーティファクト発行", "ファイル送信", "present_files")
        for agent in sorted((ROOT / "agents").glob("*.md")):
            fm = agent.read_text(encoding="utf-8")[:600]
            m = re.search(r"^tools:\s*(.+)$", fm, re.M)
            tools = m.group(1) if m else ""
            if "SendUserFile" in tools or "Artifact" in tools:
                continue  # 発行手段を持つなら基準に含めてよい
            for row in re.findall(rf"^\|\s*G\d+\s*\|\s*{re.escape(agent.stem)}:.*$", evals, re.M):
                for w in publish_words:
                    self.assertNotIn(
                        w, row,
                        f"{agent.stem} は発行手段を持たない（tools: {tools}）のに "
                        f"golden タスクが『{w}』を求めている: {row[:80]}",
                    )


if __name__ == "__main__":
    unittest.main()
