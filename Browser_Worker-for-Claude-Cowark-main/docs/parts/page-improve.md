---
description: ページ改善提案 — 対象ページを計測・分析し、課題の診断と改善版レイアウトのモックアップHTMLを生成する。Use when ユーザーが「このページを改善して」「LPをもっと良くしたい」「レイアウトを見直して」「CVR上げる案がほしい」「リニューアル案を作って」等、既存ページの改善・リデザイン提案を求めたとき。Not for 現状調査のみ（→style-research 部品 / site-audit 部品）
argument-hint: <対象ページURL> [改善の目的（例: CVR向上 / 読みやすさ / 高速化）]
---

対象ページ（$ARGUMENTS）の改善提案を作成してください。

## 手順

1. **現状把握（既存ナレッジ優先）**: `knowledge/styles/` `knowledge/audits/` に対象サイトの計測データがあれば再利用。なければ style-research 部品 / site-audit 部品 の手順で必要最小限を計測する
2. **コンテンツ構造の把握**: read_page でセクション構成・訴求順・CTA配置を抽出
3. **課題の診断**: 以下の観点で問題点を列挙し、影響度順に整理する
   - 訴求順序（AIDMA/PASの流れになっているか、CTAまでの距離）
   - 視線設計（ファーストビューの情報量、階層の明確さ）
   - 速度・品質（audit結果の閾値超え項目）
   - 一貫性（色数過多、フォント混在、余白のリズム）
4. **成果物の生成（役割分担）**:
   - **改善提案レポート** → `deliverable-writer` に委譲（templates/report-template.html 準拠）: 課題→改善案→期待効果の対応表、Before/After の構成比較
   - **改善版モックアップHTML** → `design-artisan` に委譲（最上位モデル）: 対象サイトのデザイントークンを維持しつつ課題を解消したレイアウト案。実コンテンツ使用。委譲プロンプトにはトークンJSON・課題診断・抽出コンテンツの絶対パスと出力先を明記
   - design-artisan の fable 指定がこの環境で使えない場合は、**design-artisan をモデル sonnet で起動する**（エージェントの専門化された指示が品質の本体であり、モデルは代替可。deliverable-writer への代行はしない）

5. **修正ループ（生成 → 批評 → 修正）**: モックアップ生成後、必ず `design-critic` エージェントに (a)モックアップ (b)トークンJSON (c)課題診断 の絶対パスを渡してレビューさせる
   - `VERDICT: REVISE` なら FIX リストを design-artisan に渡して修正させ、再度 design-critic にかける
   - **最大2周**。2周後も REVISE なら、残った FIX を「人間レビュー事項」としてレポートに記載して先へ進む（無限ループ禁止）
   - PASS したらループ終了。レポートにループの経過（何周・何を直したか）を1行記録する

6. **目視検証（レンダリング確認）**: コードレビューPASS後、実際の見た目を確認する
   - モックアップをアーティファクト発行し、その URL をブラウザで開いてスクリーンショットを取得（デスクトップ幅と 375px 相当の2枚）
   - スクショ取得手段: Playwright の browser_take_screenshot、または In Chrome の computer（action=screenshot は v0.34 からゲート対象外）
   - スクショを design-critic に渡し「レンダリング上の問題（重なり・はみ出し・コントラスト・アニメの意図通り動作）」を審査。REVISE なら修正ループへ戻る（この目視周回も最大1回）
   - 取得したスクショは knowledge/mockups/ に保存し、改善提案レポートの Before/After 比較に使う

## 出力

- レポート: `knowledge/reports/improve-<site>-<date>.html`
- モックアップ: `knowledge/mockups/<site>-<date>.html`
- **アーティファクト発行**: create_artifact ツールが利用可能な環境では、モックアップとレポートをアーティファクトとして発行し、共有URLを報告する（レビュー・共有が容易になるため優先）
- **Claude Design 同期**: 手順の正本は docs/parts/design-sync.md（増分同期・finalize_plan 承認・素材パック規約）。メディア素材入りHTMLは同期を既定ルートとして提案する（2026-07-23 ユーザー決定）

### 動く演出部品（任意）

改善案に動きの演出を足す場合は docs/media-pipeline.md のアルファWebM ラインを使う（GIFより滑らか・軽量）。

## 注意

- 改善案は計測データと診断根拠に紐付けること（「なんとなく今風」は禁止）
- 元ページの文言・実績数値を勝手に変えない（構成・レイアウト・表現の改善に限定）
- 読み取り専用タスク（対象サイトへの変更は行わない）

## 転換率観点の改善

応募率・CV改善が目的の依頼では references/cro-jp/SKILL.md + references/psych-ux-jp/SKILL.md（心理判断表）+ references/design-evidence-jp/SKILL.md（実証数値: FV完結1.64倍・CTA位置・行長等）を Read し、仮説（現状→変更→期待指標）を明示してから改善案を作る。効果検証の集計は outcome-verifier。
