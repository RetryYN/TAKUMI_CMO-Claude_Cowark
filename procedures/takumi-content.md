# /コンテンツ — オウンド/オーガニックのコンテンツ制作パック（takumi-content）

要望を受けて実行粒度（docs/parts/index.md の3段）を判定し、タスク5型に振り分ける。各タスクは docs/parts/ の部品を Read して従う。

> TAKUMI-CMO は **ゼロ広告費**。有料出稿は一切行わない（ゼロ課金ゲートが機械遮断）。このパックは**オウンド/オーガニックのコンテンツ資産**（記事・SNSクリエイティブ・サムネ/OGP・図解・LP・動画コンテンツ）を制作し、集客とブランディングに効かせる＝金を使わずに無双する主戦場。

## 0. 対象の確認（曖昧なら最初に聞く）

「コンテンツ作って」だけでは対象が定まらない。以下が要望から読み取れないときは、質問ツール（選択式）で先に確認する（読み取れるなら聞かずに進む）:

1. **何のコンテンツか**（4択+その他で聞く）: 記事・ブログ（オウンドメディア/note）/ SNSクリエイティブ（画像・カルーセル・サムネ・OGP）/ ビジュアル制作（バナー・図解・インフォグラフィック）/ 動画コンテンツ / LP
2. **目的**: 集客（オーガニック流入）/ ブランディング（世界観・信頼の醸成）/ 転換（CV導線）
3. **どのブランドか**: アクティブブランドを確認する（マルチブランドのブランド解決・区画分離は Phase 3 で実装）

確認結果は knowledge/styles/ か該当媒体の調査記録に前提として書き残す（次回は聞かない）。

| 要望の型 | タスク | 部品 |
|---|---|---|
| 「競合コンテンツ/訴求を洗い出して」 | リサーチ | docs/parts/deep-research.md / docs/parts/sns-research.md |
| 「素材/動画素材を探して」 | 収集 | docs/parts/asset-collect.md / docs/parts/video-asset-collect.md |
| 「画像/動画を生成して」 | クリエイティブ | docs/parts/imagegen.md / docs/parts/videogen.md |
| 「バナー/サムネにして」「背景を消して」「WebM/透過動画に」 | クリエイティブ | docs/parts/image-edit.md / docs/parts/video-edit.md |
| 「このビジュアル/記事からLP作って」 | クリエイティブ | docs/parts/content-to-lp.md |
| 「動画コンテンツの構成」「フック案」 | クリエイティブ | docs/parts/video-content-script.md |
| 「Design/Canvaへ」「書き出し準備」 | 掃き出し | docs/parts/design-sync.md / docs/parts/canva-export.md |

- 公開向けコピー・クリエイティブは references/ad-compliance-jp/SKILL.md（景表法・ステマ規制・PR表記）のチェック必須
- **有料出稿・課金は AI 禁止（ゼロ課金ゲート＝URL Guard／Money Watch）**。TAKUMI-CMO は費用を1円も使わない。投稿など不可逆送出は pre-send-verifier 監査 + ユーザー承認
- 技術地図（形式・レシピ・素材パック）は docs/media-pipeline.md
