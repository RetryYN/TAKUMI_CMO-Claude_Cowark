# /Instagram運用 — Instagram（delve-sns-instagram）

**共通手順の正本 `docs/sns-ops.md` を最初に Read** し、その運用フロー（実態照合→生成→予約/下書き→実績記録→ダッシュボード締め）に従う。以下はこの媒体固有の差分のみ。

## この媒体で見える範囲・制約（2026-07-23 Cowork実測）

- キャプション・ハッシュタグ・いいね/コメント・プロフィール・投稿一覧・リールのサムネイルは読める
- 音声は不可・映像はフレーム抜き取り
- bot 検知に注意 — スクロール巡回は控えめに。CAPTCHA遭遇時は即中断して報告（突破しない）

## 固有ルール

- リール企画はサムネイル+冒頭フックの静止画分析を基本にする

- タスクの最小単位は tasks/*.yaml に登録（/カスタマイズ のタスク登録）。変更操作（投稿・予約・設定変更）は /タスク開始 のゲート下で実行
- 文面は references/ の該当規範（sns-jp / content-design、採用系は recruit-writing）を Read してから生成。公開前に ad-compliance-jp チェック
- ナレッジ置き場: knowledge/sns/instagram/（ネタ帳は queue.md）
