---
description: Delvework の現在状態（進行中タスク・フェーズ・蓄積ナレッジ）を確認して報告する。Use when ユーザーが「今どういう状態？」「タスク進んでる？」「前回の続きどこから？」「ナレッジ何が溜まってる？」等、作業状態や引き継ぎ状況を尋ねたとき、またはブラウザ操作がゲートにブロックされて原因を確認したいとき
---

Delvework の現在状態を確認して報告してください。

0. プラグインのバージョンを報告する（配布・同期ズレの検知用）: `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` の `version` を読む。環境変数が使えない場合は Glob で `**/plugins/**/browser-worker/.claude-plugin/plugin.json` を探す
1. `memory/.workflow/` ディレクトリの各フラグ（active / phase / b4_done / e_done / k_done）の有無を Bash で確認する:
   ```bash
   ls -la memory/.workflow/ 2>/dev/null && cat memory/.workflow/active memory/.workflow/phase 2>/dev/null
   ```
2. `knowledge/sites/` にサイトナレッジがあるか確認する:
   ```bash
   ls knowledge/sites/ 2>/dev/null
   ```
3. 結果を表にまとめて報告する:
   - ワークフロー状態（未初期化 / 進行中タスク名 / フェーズ / 各フラグ）
   - サイトナレッジ一覧
   - hook ゲートの想定挙動（現在のフラグ状態で変更操作がブロックされるか）

このコマンドが動けば、プラグインのコマンド読み込みが機能している証拠になります。
