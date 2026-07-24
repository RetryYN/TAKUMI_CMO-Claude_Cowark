# /note運用 — note（delve-sns-note）

**共通手順の正本 `docs/sns-ops.md` を最初に Read** し、その運用フロー（実態照合→生成→予約/下書き→実績記録→ダッシュボード締め）に従う。以下はこの媒体固有の差分のみ。

## この媒体で見える範囲・制約（2026-07-23 Cowork実測）

- **最も相性が良い媒体（実質制約なし）**: 記事本文を丸ごと読める（get_page_text 全文抽出）
- 競合の記事構成・見出し・課金ライン（有料手前まで）・スキ数・コメントまで調査圏内
- ログイン済みなら自分のダッシュボード（PV・スキ推移）も読める

## 固有ルール

- 記事執筆は storytelling / logical-writing 規範を用途で使い分け、本格執筆は deliverable-writer へ委譲

- タスクの最小単位は tasks/*.yaml に登録（/カスタマイズ のタスク登録）。変更操作（投稿・予約・設定変更）は /タスク開始 のゲート下で実行
- 文面は references/ の該当規範（sns-jp / content-design、採用系は recruit-writing）を Read してから生成。公開前に ad-compliance-jp チェック
- ナレッジ置き場: knowledge/sns/note/（ネタ帳は queue.md）
