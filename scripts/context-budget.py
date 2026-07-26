#!/usr/bin/env python3
"""文脈予算の実測 — 「何にトークンを払っているか」を数える。

**なぜ要るか**: 効率は感覚では分からない。2026-07-27 のレビューまで、
`session-rules.txt` のルール(3) が1行 4,094字（ファイルの44%）まで育っていたのに
誰も気づかなかった。**毎セッション全文が載る場所が最も高い**のに、
そこが最も測られていなかった。

使い方:
    python3 scripts/context-budget.py          # 一覧
    python3 scripts/context-budget.py --top 5  # 上位件数を変える

**トークン数は概算**（日本語は約1字＝1トークンとして数える）。
正確な実測ではないので、**絶対値ではなく前回との差分を見る**こと。

数える3つの層:
  1. 常時ロード — ユーザーが一言も言う前に載る。ここが最も高い
  2. 委譲1回あたり — サブエージェント本文 + `skills:` preload の全文
  3. 都度ロード — 手順書・スキル・部品。使ったぶんだけ
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# lint #50 と同じ上限（片方だけ動かすと意味が無いので、値はここが正本ではなく lint 側を指す）
RULES_BUDGET = 7_400


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def frontmatter(p: pathlib.Path) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", read(p), re.S)
    return m.group(1) if m else ""


def description(p: pathlib.Path) -> str:
    m = re.search(r"^description:\s*(.*)$", frontmatter(p), re.M)
    return m.group(1) if m else ""


def preloaded(p: pathlib.Path) -> list[str]:
    return re.findall(r"^\s+-\s+(\S+)", frontmatter(p), re.M)


def fmt(n: int) -> str:
    return f"{n:,}字 (~{n // 1000}k tok)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    print("=" * 70)
    print("1. 常時ロード — ユーザーが一言も言う前に載る（ここが最も高い）")
    print("=" * 70)
    rules = ROOT / "hooks/scripts/session-rules.txt"
    layers = [
        ("session-rules.txt（SessionStart で注入）", len(read(rules)), 1),
        ("commands/*.md の frontmatter",
         sum(len(frontmatter(p)) for p in ROOT.glob("commands/*.md")),
         len(list(ROOT.glob("commands/*.md")))),
        ("skills/*/SKILL.md の description（Skill ツール一覧）",
         sum(len(description(p)) for p in ROOT.glob("skills/*/SKILL.md")),
         len(list(ROOT.glob("skills/*/SKILL.md")))),
        ("agents/*.md の description",
         sum(len(description(p)) for p in ROOT.glob("agents/*.md")),
         len(list(ROOT.glob("agents/*.md")))),
    ]
    always = 0
    for name, n, cnt in layers:
        always += n
        print(f"  {name:46s} {fmt(n):>22s}  ({cnt}本)")
    print(f"  {'合計':46s} {fmt(always):>22s}")
    print()
    print(f"  ※ session-rules.txt は lint #50 が {RULES_BUDGET:,}字 で上限を持つ。")
    print("     他の3つは**プラットフォームが載せる**ので削れない — 短く書くことでしか下がらない。")

    print()
    print("=" * 70)
    print("2. 委譲1回あたり — 本文 + skills: preload の全文")
    print("=" * 70)
    rows = []
    for a in sorted(ROOT.glob("agents/*.md")):
        body = len(read(a))
        pre = sum(len(read(ROOT / f"skills/{s}/SKILL.md"))
                  for s in preloaded(a) if (ROOT / f"skills/{s}/SKILL.md").is_file())
        rows.append((body + pre, a.stem, body, pre, len(preloaded(a))))
    for tot, name, body, pre, n in sorted(rows, reverse=True):
        print(f"  {name:22s} {fmt(tot):>22s}  = 本文 {body:,} + preload {pre:,}（{n}本）")
    heavy4 = sum(r[0] for r in sorted(rows, reverse=True)[:4])
    print(f"  {'（同時上限4体を最も重い4体で使うと）':22s} {fmt(heavy4):>22s}")
    print("     ※ 設計上どの組が並列になるかは docs/agent-tiers.md が正本。ここは上限の目安")
    print()
    print("  ※ preload は E6（委譲先が正本を Read できない環境がある）への対策で、")
    print("     **Read は当てにできない経路**という実測に基づく（escalations E6 / lint #34）。")
    print("     高いが買っているものがある。**削るなら E6 を再び開くことになる。**")

    print()
    print("=" * 70)
    print(f"3. 都度ロード — 使ったぶんだけ（上位 {args.top}）")
    print("=" * 70)
    for label, pattern, key in [
        ("procedures", "procedures/*.md", lambda p: p.name),
        ("skills", "skills/*/SKILL.md", lambda p: p.parent.name),
        ("docs/parts", "docs/parts/*.md", lambda p: p.name),
    ]:
        files = sorted(((len(read(p)), key(p)) for p in ROOT.glob(pattern)), reverse=True)
        total = sum(n for n, _ in files)
        print(f"  ■ {label}（{len(files)}本 / 計 {fmt(total)} / "
              f"中央値 {files[len(files) // 2][0]:,}字）")
        for n, name in files[:args.top]:
            print(f"      {name:34s} {n:7,d}字")
    return 0


if __name__ == "__main__":
    sys.exit(main())
