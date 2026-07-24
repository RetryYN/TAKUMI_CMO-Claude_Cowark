# /リサーチ — 調査の横断入口（delve-research）

## 0. どの媒体・対象？（曖昧なときだけ聞く）

要望から対象が読み取れなければ、質問ツールで確認する:

1. **どの媒体・対象を調べる？** — SNS（X/Instagram/TikTok/note/YouTube）/ 広告 / Webサイト・LP / 求人媒体・求人市場 / その他のWeb情報
2. **何を知りたい？** — 競合の動き / トレンド・伸びてる型 / デザイン・見せ方 / 品質・数値 / 徹底的に全部 / その他

確認した対象・観点はそのセッション中は前提として保持し、同じ質問を繰り返さない（調査記録の冒頭にも書き残す）。

## 1. 振り分け

| 対象 | 手順 |
|---|---|
| SNS | docs/parts/sns-research.md + 該当媒体の procedures/delve-sns-*.md（見える範囲・制約） |
| 広告 | procedures/delve-ads.md のリサーチ行（TikTok Creative Center 等） |
| Webサイト・LP のデザイン | docs/parts/style-research.md |
| Webサイト・LP の品質・速度 | docs/parts/site-audit.md |
| 徹底的に全部 | docs/parts/deep-research.md |
| 求人媒体・市場 | knowledge/sites/<媒体>/ のナレッジ + 媒体内検索（読み取りのみ） |

## 2. 共通ルール

- 調査は読み取り専用（変更操作なし・ゲート不要）。bot検知・CAPTCHA・レート制限に遭遇したら即中断して報告
- 結果はレポート化するなら logical-writing + docs/conventions.md 準拠。記録先は knowledge/（styles/ audits/ sns/<媒体>/research/）
- 調査結果から制作に進む場合は該当パック（/SNS運用 /広告 /Webサイト）へ引き継ぐ
