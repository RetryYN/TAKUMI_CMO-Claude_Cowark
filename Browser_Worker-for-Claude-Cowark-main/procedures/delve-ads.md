# /広告 — 広告制作・分析のカテゴリーパック（delve-ads）

要望を受けて実行粒度（docs/parts/index.md の3段）を判定し、タスク5型に振り分ける。各タスクは docs/parts/ の部品を Read して従う。

> **単一媒体の依頼は専用コマンドが第一入口**: セットアップで広告媒体を選ぶと `/<媒体名>広告`（/Google広告 等）が生成される。専用コマンド経由なら媒体は前提として固定し、§0 の質問2を聞かない。本パック（/広告）は複数媒体・媒体不明・出稿媒体に紐づかない全般（バナー・LP・素材）の入口。

## 0. 対象の確認（曖昧なら最初に聞く）

「広告を見て」「広告作って」だけでは対象が定まらない。以下が要望から読み取れないときは、質問ツール（選択式）で先に確認する（読み取れるなら聞かずに進む）:

1. **誰の広告か**: 自社 / 競合（社名・アカウント）
2. **どの媒体の広告か**（4択+その他で聞く）: SNS広告（Meta/TikTok/X/YouTube/LINE — 選択後に媒体を特定）/ 検索・ディスプレイ（Google等）/ 求人広告（Indeed・媒体内広告）/ バナー・LP全般 / その他
3. **目的**: 調査したい（何が伸びてるか）/ 作りたい（バナー・LP・台本）/ 改善したい（今の広告の直し）

確認結果は knowledge/styles/ か knowledge/sns/<媒体>/research/ の調査記録に前提として書き残す（次回は聞かない）。

| 要望の型 | タスク | 部品 |
|---|---|---|
| 「競合広告/訴求を洗い出して」 | リサーチ | docs/parts/deep-research.md / docs/parts/sns-research.md（TikTok Creative Center 含む） |
| 「バナー用の素材/動画素材を探して」 | 収集 | docs/parts/asset-collect.md / docs/parts/video-asset-collect.md |
| 「画像/動画を生成して」 | クリエイティブ | docs/parts/imagegen.md / docs/parts/videogen.md |
| 「バナーにして」「背景を消して」「WebM/透過動画に」 | クリエイティブ | docs/parts/image-edit.md / docs/parts/video-edit.md |
| 「このバナーからLP作って」 | クリエイティブ | docs/parts/ad-to-lp.md |
| 「TikTok広告の台本」「動画のフック案」 | クリエイティブ | docs/parts/video-ad-script.md |
| 「Design/Canvaへ」「入稿準備」 | 掃き出し | docs/parts/design-sync.md / docs/parts/canva-export.md |

- 公開向けコピー・クリエイティブは references/ad-compliance-jp/SKILL.md のチェック必須
- 広告出稿・課金は AI 禁止（Money Watch / URL Guard）。入稿など不可逆送出は pre-send-verifier 監査 + ユーザー承認
- 技術地図（形式・レシピ・素材パック）は docs/media-pipeline.md
