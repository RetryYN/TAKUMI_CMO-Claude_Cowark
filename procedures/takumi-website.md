# /匠発信 ▸ 自社サイト・LP の診断と改善（takumi-website）

> **前段**: アクティブブランドを先に確定する（未確定なら `/匠設定`）。区画外への書き込みは Brand Isolation Guard が deny する。
> **ループ上の位置**（→ `docs/parts/task-loop.md`）: **① 構える＝完了条件と対象ページの確定／② 作る＝`design-artisan`（モック）・`deliverable-writer`（文面）／③ 咎める＝`design-critic`／④ 確かめる＝`outcome-verifier`**。

要望を受けて実行粒度（docs/parts/index.md の3段: タスク単体 / ワークフロー連結 / まるっと）を判定し、タスク5型に振り分ける。各タスクは docs/parts/ の部品を Read して従う。

| 要望の型 | タスク | 部品 |
|---|---|---|
| 「表示速度を測って」「SEO/リンク切れチェック」 | 分析 | docs/parts/site-audit.md |
| 「デザイン・配色・フォントを調べて」 | リサーチ | docs/parts/style-research.md |
| 「徹底的に洗い出して」 | リサーチ（深掘り） | docs/parts/deep-research.md |
| 「このページ/LPを改善して」「リニューアル案」 | クリエイティブ | docs/parts/page-improve.md |
| 「申込・問い合わせが増えない」「料金ページを直したい」「無料お試し/返金保証をつけたい」 | **クリエイティブ（オファー）** | **`skills/offer-design-jp`**（設計の正本）+ docs/parts/page-improve.md |
| 「マップに出ない」「近くで検索されたときに出したい」「Googleビジネスプロフィール」「店舗情報を整えたい」「口コミを増やしたい（地図）」 | **分析＋クリエイティブ（ローカル）** | **`skills/local-seo-jp`**（設計の正本）。**商圏のある事業だけ**（§0 適用判定）。掲載内容の編集・口コミへの投稿は**人間が実行**、AI は下書きと機械検査まで |
| 「Designに反映して」「書き出して」 | 掃き出し | docs/parts/design-sync.md / docs/parts/canva-export.md |

- 連続依頼（例:「診断して改善案まで」）は 分析→クリエイティブ→掃き出し のワークフローとして連結する
- 実サイトへの変更操作は必ず takumi-start（A〜K）経由。成果物は docs/conventions.md 準拠
