# Cowork 実行仕様（正本）

TAKUMI-CMO は **Claude Cowork** 上で動くプラグイン。ここは「Cowork がこのプラグインをどう実行するか」の正本。
検証コマンド（`/検証` = takumi-verify）と開発ワークフロー（[開発ワークフロー.md](開発ワークフロー.md)）はこの仕様を前提に設計する。
プラグインでは根治できない本体側の課題は [escalations.md](escalations.md)（上申台帳 E1〜E4）が正本、本ファイルと重複記載しない。

すべて 2026-07-24 までの実機検証（TESTING.md）で確定した事実。推測は「未確認」と明示する。

## 1. 配布とインストール

- **配布 = git リポジトリの marketplace 同期**。このリポジトリがそのまま配布物（削除ビルドは無い）。
- Cowork 設定 →プラグイン→ marketplace としてリポジトリURL（`RetryYN/TAKUMI_CMO-Claude_Cowark`）を追加 → プラグインを有効化。
- **更新検知は `.claude-plugin/plugin.json` / `marketplace.json` の `version` フィールド**。bump しないと利用者に更新が反映されない（`scripts/bump-version.sh` で両ファイル同時更新）。
- **`name` は必ず kebab-case（小文字・数字・ハイフンのみ）**。非 kebab-case の名前は **claude.ai marketplace 同期が拒否**する（Cowork 配布では致命的）。現状 plugin=`takumi-cmo` / marketplace=`retryyn-takumi-cmo` は適合。
- **`.claude-plugin/` に入るのはマニフェストだけ**、他は各トップレベルディレクトリに置く。プラグイン実体は cache へコピーされるため `../` 外部参照は不可（相対不達 → Glob フォールバック。§4）。
- ルート直下の構成（**リポジトリ全体がそのまま配布物**なので、dev-side のファイルも利用者の cache にコピーされる。害はないが「配布されない」と誤解しないこと）:

| ディレクトリ | 役割 | Cowork が自動探索するか |
|---|---|---|
| `.claude-plugin/` | マニフェスト（plugin.json / marketplace.json） | する |
| `commands/` | スラッシュコマンド（日本語名） | **する** |
| `agents/` | サブエージェント定義 | **する** |
| `hooks/` | hooks.json + スクリプト | **する**（cloud。§2） |
| `procedures/` | コマンドが Read する手順書の実体 | しない（commands から明示 Read） |
| `references/` | 執筆・計測リファレンス（SKILL.md 形式） | **しない**（→ §4b） |
| `templates/` `docs/` | 雛形・正本ドキュメント | しない（明示 Read） |
| `scripts/` | lint / bump / hooks テスト | しない（dev-side） |
| `takumi/` `tests/` | ドメインモデル（Python）と単体テスト | しない（dev-side。Tier 1 と `--workspace` 検証で使う。[domain-model.md](domain-model.md)） |
| `.github/` | CI（lint / unittest / shellcheck / hooks） | しない（dev-side） |
- 配布前のローカル検証に CLI `claude plugin validate .` が使える（marketplace/plugin.json スキーマ・frontmatter・hooks.json の JSON 妥当性）。ただし CLI 検証が通っても Cowork で hook が発火する保証にはならない（§2）。

## 2. hooks の配線挙動（最重要）

- イベント: `SessionStart` / `PreToolUse` / `PostToolUse`（`hooks/hooks.json`）。`${CLAUDE_PLUGIN_ROOT}` は実行時にプラグインルートへ解決される。
- **cloud セッション（claude.ai 上のクラウド実行）でのみ hooks が配線される**。matcher に一致したツール呼び出しの前後で hook スクリプトが発火する。
- **ローカル/デスクトップ Cowork では hooks が未配線（フェイルオープン。escalations E4）**。matcher 完全一致のツール（`mcp__claude-in-chrome__navigate` 等）でも hook が不発。全ゲートが素通りになる。
  - → **ゲート前提の運用（一括送出・金銭近傍・無人運用・ブランド分離）は必ず cloud セッションで行う。**
- **「Cowork なら hooks が動く」は保証ではない（配布リスク）**。本プロジェクトの cloud 実機（2026-07-24, TESTING.md）では plugin hooks が発火しゲートが deny した実績があるが、上流には **Cowork が CLI を `--setting-sources user` で起動し plugin スコープの hooks を黙って除外する**という未解決報告（anthropics/claude-code #27398 / #40495）がある。バージョン・構成依存で発火しないことがありうる。
  - **設計原則: hooks を唯一の防御にしない（自己規律＋人間承認との多層防御）**。ゲート依存運用の前に、Tier 2 検証で**その環境で実際に hook が発火するか**を必ず実測する（V3/V35 等）。
  - **SessionStart hook 依存は特に避ける**（発火しない報告あり）。引き継ぎ通知・ルール注入のような初期化は commands/skills 側でも成立するよう二重化する。
- **ツール名が cloud / ローカルで異なる**（matcher には両方を先回り登録済み）:
  | 用途 | cloud | ローカル |
  |---|---|---|
  | シェル実行 | `Bash` | `mcp__workspace__bash` |
  | ファイル送付 | `SendUserFile` / `mcp__remote-devices__*` | `mcp__cowork__present_files` |
  | ブラウザ操作 | `mcp__claude-in-chrome__*`（`computer`/`navigate`/`form_input`/`read_page`/`file_upload` 等） | 同左 |

## 3. ゲート機構（memory/.workflow/ フラグ + GATE_MODE）

- ゲートの実体は `memory/.workflow/` のフラグファイル（例: `bulk_send` / `k_done` / `ov_done` / `critic_pending` / `critic_pass` / `money_alert` / `verify_allowlist`）。hook スクリプトがフラグを読んで allow / warn / deny を返す。
- 各 hook 先頭の `GATE_MODE="${TAKUMI_GATE_MODE:-deny}"` が既定モード（2026-07-24 に warn→deny 昇格済み）。環境変数 `TAKUMI_GATE_MODE` はテスト時の両モード検証用。
- **hook 10本**（`hooks/scripts/`）: workflow-gate / ov-gate / rm-guard / brand-isolation-guard / critic-gate / url-guard（ゼロ課金ゲート）/ navigate-warn / injection-warn / money-watch / session-start。
- **限界（自己規律で補う領域）**: hook はツール引数の文字列しか見えない。`ref_150` 等の参照IDの解決先（type=password か）は判定できない（escalations E1）。フラグは Bash から直接 touch/rm で技術的に迂回可能（意図的迂回ではなく手順飛ばしへの防御）。硬い防御は Money Watch・URL Guard・人間承認が担う。

## 4. commands / agents / MCP の供給

- **commands（スラッシュコマンド）**: `commands/*.md`（日本語名）がメニューに並ぶ。frontmatter の description（Use when）で自然文からの自動発火も効く。薄いラッパーで `procedures/takumi-*.md` を Read して実行。
- **agents（サブエージェント）**: `agents/*.md`。Cowork では Agent ツールが供給されるが、**未供給の場合は main ループが該当エージェント定義を Read して直接実行するフォールバック**（conventions §4）。委譲プロンプトにはプラグイン内ファイルの**絶対パス**を渡す（相対は synced 環境で不達）。
- **プラグイン実体パス**は `/root/.claude/plugins/synced/<plugin>`（相対 `templates/` 等が不達 → **Glob `**/<filename>` フォールバック必須**。パス解決規則は conventions §1）。
- **DesignSync（Claude Design 連携）は Cowork セッションに供給される**（実機確認済み）。素材パックを claude.ai/design プロジェクトへ同期可（finalize_plan の承認制）。なお Claude Design の公式ハンドオフ（handoff bundle）は「→ Claude Code」向けで、→ Cowork への受け渡し経路は未確認。本プラグインは DesignSync（claude.ai/design プロジェクトの読み書き）経路を使う。
- 出力提示は `mcp__cowork__present_files`（パスは outputs スクラッチパッド or プライマリ workspace に限る・非プライマリフォルダは拒否）、フォルダのマウントは `request_cowork_directory`。
- 同梱 MCP は「ローカルMCPサーバーを含む」承認後に供給される。ブラウザは Claude in Chrome が前提エンジン。

## 5. cloud / ローカルの分断（資産）

- クラウドセッションの作業場はコンテナ内のみ、ローカルは別ファイルシステム。**資産（knowledge/tasks/memory/コマンド）は自動同期されない**（escalations E3）。継続運用は「フォルダを追加」で業務フォルダを接続して永続化する。
- スキル/コマンドの登録タイミング: cloud=同一セッション内で即時登録されうる / ローカル=次セッションから（環境差あり）。
- ローカルスケジュール（このコンピュータで実行）はデスクトップUI操作でのみ登録可。AI/プラグインからは登録できない（escalations E2）。

## 6. 検証は「dev↔Cowork の往復」で完結する（→ 開発ワークフロー.md §二層検証）

- **Tier 1（機械・毎コミット・ローカル/CI）**: lint / 単体テスト / test-hooks / shellcheck。参照整合・ドメイン不変条件・hook スクリプトのロジックを保証する。**hook の"配線"は検証できない**（ローカルはフェイルオープン）。
- **Tier 2（実機・節目・cloud Cowork）**: `/検証`（takumi-verify）を cloud セッションで実行。hook の実配線・コマンド経路・エージェント起動・ブランド分離など**Tier 1 が構造的に検証できない項目**を実測する。ユーザーが cloud Cowork で実行 → PASS/FAIL 表を開発側に貼り戻す往復で確定。
- 検証の外部無害原則: ブラウザは example.com と the-internet.herokuapp.com（V5(b) 固定）のみ。`verify_allowlist` で機械強制し、リスト外 navigate は url-guard が deny する。
