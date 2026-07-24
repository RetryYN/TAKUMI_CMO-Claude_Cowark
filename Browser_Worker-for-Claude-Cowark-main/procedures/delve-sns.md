# /SNS運用 — SNS媒体の統合入口（delve-sns）

**媒体別の専用コマンドが優先**: /セットアップ（または /ワーク追加）で媒体を選ぶと、ワークスペースに `/<媒体名>運用`（例: /X運用 /Instagram運用）が生成される。生成済みの媒体への単一媒体依頼はそちらが第一入口。この /SNS運用 は (a) 複数媒体まとめての依頼（「全SNSのストック確認」等）、(b) 媒体不明の依頼、(c) 専用コマンド未生成（セットアップ未実施）時の受け皿。専用コマンドがまだ無い媒体を検知したら、生成を1行提案してよい（正本テンプレは /ワーク追加 §4）。

## 0. どの媒体？（曖昧なときだけ聞く）

要望に媒体名（X/Twitter・インスタ・Threads・TikTok・note・YouTube・LINE）が含まれていればそのまま該当手順へ（ただし packs.conf で `sns-<媒体>=off` の媒体は実行せず、「セットアップでOFFの媒体です。使うなら『◯◯もやる』と言ってください」と1行案内）。含まれていなければ質問ツールで「どの媒体？」を選択肢で確認する（**複数選択可** — 「全SNSのストック確認」のような依頼は複数選び、媒体ごとに順次実行）。**選択肢は knowledge/config/setup.yaml の sns リスト（使うと答えた媒体）だけを出す**（未設定なら全媒体を出し、回答を setup.yaml に反映）。**選択肢は1媒体=1択**（「YouTube/note」のように束ねない）。媒体が4つを超えて1問に収まらないときは、同じ質問ツール呼び出し内で2問に分割して同時に出し、両方の質問で複数選択可を維持する（例: 全7媒体なら1問目 X/Instagram/Threads/TikTok、2問目 note/YouTube/LINE）。

## 1. 媒体別手順へ振り分け

**媒体が要望から明らかな場合でも、実行前に該当媒体の手順書（下表）を必ず Read する**（見える範囲・制約・固有ルールの正本はそこにしかない。2026-07-24 実運用で媒体手順未参照のまま直接実行された事例あり — 結果が良好でも手順書スキップは再現性を壊す）。

| 媒体 | 手順書（見える範囲・制約・固有ルールの正本） |
|---|---|
| X | procedures/delve-sns-x.md |
| Instagram | procedures/delve-sns-instagram.md |
| TikTok | procedures/delve-sns-tiktok.md |
| Threads | procedures/delve-sns-threads.md |
| note | procedures/delve-sns-note.md |
| YouTube | procedures/delve-sns-youtube.md |
| LINE公式 | procedures/delve-sns-line.md |

複数媒体まとめて（「全SNSのストック確認」等）は媒体ごとに順に実行し、締めで outcome-verifier の集計とダッシュボード更新につなぐ。

## 1b. 計画依頼（「カレンダー作って」「投稿計画」「来月のスケジュール」）

docs/parts/content-calendar.md に従う（媒体別の制約はこのパックの各媒体手順を参照）。

## 2. 共通フロー

各媒体手順は docs/sns-ops.md（実態照合→生成→予約/下書き→実績記録）に従う。投稿・予約・配信の変更操作はタスク開始手順（procedures/delve-start.md）のゲート下。LINE の配信実行は pre-send-verifier 監査 + ユーザー承認 + 費用見積もりが必須。
