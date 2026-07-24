---
description: スタイルリサーチ — 参考サイトのデザイン（色・フォント・レイアウト・構成）を実測してデザイントークンJSONと比較HTMLレポートを生成。Use when ユーザーが「このサイトのデザインを調べて」「参考サイトの色/フォントを分析して」「競合LPの構成を見て」「LP/サイトを作るから下調べして」「デザインの参考を集めて」等、サイトの見た目・スタイルの調査を依頼したとき。Not for 速度や品質の診断（→site-audit 部品（docs/parts/site-audit.md））
argument-hint: <URL...>（スペース区切りで複数可）
---

指定された参考サイト（$ARGUMENTS）のスタイルリサーチを実行してください。

## 手順（サイトごとに繰り返し）

1. ブラウザ（Claude in Chrome: navigate / computer、Playwright: browser_navigate 等、利用可能な方）で対象 URL に遷移し、スクリーンショットを取得
2. JS 実行ツール（Claude in Chrome: `javascript_tool`、Playwright: `browser_evaluate`）で computed style を計測する:
   - **カラー**: 全可視要素の background-color / color / border-color を集計し、使用面積・頻度の上位を抽出（rgba→hex 正規化、透明・白黒系はグループ化）
   - **タイポグラフィ**: body と h1〜h4 の font-family / font-size / font-weight / line-height / letter-spacing
   - **レイアウト**: メインコンテナの max-width、セクションの縦余白（padding/margin の代表値）、グリッド列数
   - **コンポーネント**: ボタン（`button, a[class*=btn], [role=button]`）の border-radius / box-shadow / padding / 色、カード要素の角丸と影
3. セクション構成を上から順に分類する（例: ヒーロー → 課題提起 → 特長 → 実績/ロゴ → 料金 → FAQ → CTA）

## 出力（2つ）

1. **デザイントークン JSON**: `knowledge/styles/<site-name>.json`
   ```json
   {
     "source": "<URL>", "date": "<日付>",
     "colors": {"primary": "#…", "accent": "#…", "background": "#…", "text": "#…", "palette": ["#…"]},
     "typography": {"body": {...}, "headings": {...}},
     "layout": {"maxWidth": "…", "sectionSpacing": "…", "sections": ["hero", "features", "cta"]},
     "components": {"button": {...}, "card": {...}}
   }
   ```
2. **スタイルリサーチ HTML レポート**: `knowledge/reports/style-research-<date>.html`（templates/report-template.html を骨格に使用・自己完結）
   - サイトごとに: スクショ + カラーパレットのスウォッチ表示 + タイポグラフィ見本 + セクション構成図
   - 複数サイト指定時は**横断比較セクション**を先頭に置く（共通パターン / 各サイトの差別化ポイント / LP制作への示唆3点）

### Claude Design 同期（任意・DesignSync ツールがある環境）

ユーザーが「Design に同期して」「デザインシステムに登録して」と求めたら、抽出トークン JSON（と生成済みコンポーネントがあればそれ）を DesignSync で claude.ai/design のプロジェクトに push する。list_projects で対象確認（なければ create_project）→ 計画提示とユーザー承認（finalize_plan）→ write_files。承認範囲外の書き込み・一括置き換えは禁止（増分同期）。同期先を knowledge/artifacts-index.md に記録。

## モデル最適化

巡回・計測（navigate / evaluate / screenshot）とトークン JSON の書き出しはメインループで行い、**比較 HTML レポートの執筆は `deliverable-writer` エージェント（Agent ツール）に委譲する**こと。委譲時はトークン JSON・スクショの絶対パスと出力先パスをプロンプトに明記する。

## 注意

- これは読み取り専用タスク（navigate / snapshot / evaluate / screenshot のみ）。変更操作は行わないため Delvework ゲートの対象外
- ログインが必要なサイトはスキップして報告する
- 生成後、トークン JSON は「このトークンで LP を作成」という次タスクの入力として使えることを伝える
