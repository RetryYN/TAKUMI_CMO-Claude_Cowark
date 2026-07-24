# /Webサイト — 自社・対象サイトのカテゴリーパック（delve-website）

要望を受けて実行粒度（docs/parts/index.md の3段: タスク単体 / ワークフロー連結 / まるっと）を判定し、タスク5型に振り分ける。各タスクは docs/parts/ の部品を Read して従う。

| 要望の型 | タスク | 部品 |
|---|---|---|
| 「表示速度を測って」「SEO/リンク切れチェック」 | 分析 | docs/parts/site-audit.md |
| 「デザイン・配色・フォントを調べて」 | リサーチ | docs/parts/style-research.md |
| 「徹底的に洗い出して」 | リサーチ（深掘り） | docs/parts/deep-research.md |
| 「このページ/LPを改善して」「リニューアル案」 | クリエイティブ | docs/parts/page-improve.md |
| 「Designに反映して」「書き出して」 | 掃き出し | docs/parts/design-sync.md / docs/parts/canva-export.md |

- 連続依頼（例:「診断して改善案まで」）は 分析→クリエイティブ→掃き出し のワークフローとして連結する
- 実サイトへの変更操作は必ず /タスク開始（A〜K）経由。成果物は docs/conventions.md 準拠
