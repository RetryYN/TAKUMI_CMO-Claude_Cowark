# 成果物規範（Conventions）— 正本

HTML成果物（レポート・モックアップ・ガイド・ダッシュボード）の作成・発行・記録の共通ルール。
各コマンドはここに書かれたことを繰り返さず、このファイルを正とする。コマンド側に書くのは
**そのコマンド固有の値**（保存ファイル名・固有セクション構成）だけ。

## 1. HTMLレポートの作成

- 骨格は `templates/report-template.html`、判断基準は `templates/design-principles.md`
- **プラグイン内パスの解決規則（全手順共通の正本）**: `templates/` `references/` `docs/` `agents/` への参照は、①`${CLAUDE_PLUGIN_ROOT}/<path>` → ②相対パス → ③Glob `**/<filename>` の順で解決する（synced 環境では相対が不達になるため。手順書に素の相対パスが書かれていてもこの規則で読む）
- CSS の改変は `--accent` のみ可。テーブルは `.tbl` コンテナで横スクロール封じ込め、画像は max-width 100%
- **執筆は deliverable-writer エージェントに委譲**する。委譲プロンプトには入力データと出力先の**絶対パス**を明記（相対パスは誤解決される）
- **Agent ツールが使えない環境**（Cowork チャット等でサブエージェント未供給の場合）では、委譲プロンプトをユーザーに手渡ししない。main ループが該当エージェント定義（agents/*.md）を Read して自分でその作法に従い執筆し、成果物に「委譲不可のため直執筆」と1行記録する
- 保存先: `knowledge/reports/`（モックアップは `knowledge/mockups/`）。自己完結HTML（外部読み込みなし）

## 2. アーティファクト発行

- create_artifact が使える環境では成果物を発行し、共有URLを報告する
- **固定URL物**（ダッシュボード・ガイド等の「同じページを更新し続ける」もの）は初回 create、以降は必ず update。ID/URL は `knowledge/media/<name>-artifact.md` に記録して次回参照
- create で「already exists」→ その ID で update に切替（一覧に出なくても存在しうる）。一過性の 502 は1回リトライで解消することが多い（2026-07-22 検証で観測）
- 発行のたびに `knowledge/artifacts-index.md` へ「日付 / 種別 / タイトル / URL」を1行追記（ダッシュボードの生成物ライブラリの正本）
- DBの推移データを載せる場合は JSON をページ内に焼き込む（アーティファクトは外部通信不可）

## 3. 成果物は必ず届ける

優先順: アーティファクト発行 → 不可ならファイル送信 → どちらも不可なら保存パスと開き方を明示。
「書いて終わり」を成果と数えない。

## 4. エージェント共通作法（3エージェントの共通部）

- **パス解決**: 指示されたプラグイン内ファイルが相対で見つからなければ Glob `**/<filename>` で探す
- **学習記録**: 成果物へのユーザー評価は `knowledge/feedback/lessons.md` に記録・参照する（NG再発は重大）
- design-artisan が fable で起動できない場合は sonnet で**同エージェントを再起動**（deliverable-writer への振替は禁止）

## 5. コマンド追加・変更時

`docs/command-registry.md`（コマンド台帳）のチェックリストに従う。バージョンは `scripts/bump-version.sh <ver>` で両ファイル同時更新。
