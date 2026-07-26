# Cowork 実行仕様（正本）

TAKUMI-CMO は **Claude Cowork** 上で動くプラグイン。ここは「Cowork がこのプラグインをどう実行するか」の正本。
検証コマンド（`/匠検証` = takumi-verify）と開発ワークフロー（[開発ワークフロー.md](開発ワークフロー.md)）はこの仕様を前提に設計する。
プラグインでは根治できない本体側の課題は [escalations.md](escalations.md)（上申台帳）が正本、本ファイルと重複記載しない。

すべて 2026-07-24 までの実機検証（TESTING.md）で確定した事実。推測は「未確認」と明示する。

## 1. 配布とインストール

- **配布 = git リポジトリの marketplace 同期**。このリポジトリがそのまま配布物（削除ビルドは無い）。
- Cowork 設定 →プラグイン→ marketplace としてリポジトリURL（`RetryYN/TAKUMI_CMO-Claude_Cowark`）を追加 → プラグインを有効化。
- **更新検知は `.claude-plugin/plugin.json` / `marketplace.json` の `version` フィールド**。bump しないと利用者に更新が反映されない（`scripts/bump-version.sh` で両ファイル同時更新。**繰り上げ漏れは lint #52 が git 履歴で見る**）。仕組みと復旧手順は §1b。

### 1b. 更新が届かないとき（**トラブルが最も多い箇所**）

**【一次情報・確認済み】** [plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) §Version resolution and release channels（2026-07-27 取得）:

> Plugin versions determine cache paths and update detection: if the resolved version matches what a user already has, `/plugin update` and auto-update skip the plugin.

**バージョンの解決順序**（先に見つかったものが勝つ）:

1. プラグインの `plugin.json` の `version`
2. marketplace エントリの `version`
3. **プラグインの source の git コミット SHA**

**【一次情報・確認済み — ローカル環境の実測】** キャッシュはバージョンごとのディレクトリに展開される。
本機に `~/.claude/plugins/cache/retryyn-takumi-cmo/takumi-cmo/5.5.0/` があり、
中身はリポジトリ全体の複製で `plugin.json` の version は `5.5.0` だった（2026-07-27 観測）。
**バージョン文字列が変わらなければパスも変わらないので、取りに行かずに既存ディレクトリを再利用する。**
「push したのに反映されない」の大半はこれ。

#### 更新は2段階（**片方だけでは届かない**）

| 段 | 何をする | コマンド |
|---|---|---|
| 1 | **marketplace の複製を最新にする**（カタログの git pull） | `/plugin marketplace update <name>` |
| 2 | **プラグイン本体を入れ直す**（version が変わっていれば取得） | `/plugin update <plugin>` |

**1 を飛ばすと 2 は古いカタログを見て「最新です」と言う。** 逆に 1 だけでは実体が入れ替わらない。

#### それでも直らないとき

1. `version` が本当に上がっているか（`plugin.json` が最優先。ここが据え置きだと**他をどう直しても届かない**）
2. キャッシュを消す — `rm -rf ~/.claude/plugins/cache` → 再起動 → 入れ直す
3. **Cowork では 1・2 をやっても古い版が残る報告がある**（→ escalations E9）

#### なぜ `version` を省略しないのか

**【一次情報・確認済み】** 同ドキュメントは、git 系 source なら `version` を**省略すれば全コミットが新バージョン扱い**になり、
「内部利用や活発に開発中のプラグインではこれが最も簡単」と書いている。
**本プロダクトは採らない** — [TESTING.md](../TESTING.md)「配布判断の4条件」が版を条件に含めており、
**版が「検証済みであること」の単位**になっているため。全コミットが新版になると、
**未検証の途中状態がそのまま利用者に流れる**。省略は「検証しないなら簡単」という選択であり、本プロダクトの前提と噛み合わない。

#### `version` を2箇所に書いていることについて

**【一次情報・確認済み】** 同ドキュメントは「`plugin.json` と marketplace エントリの**両方に `version` を書くのは避けよ**。
Claude Code は常に `plugin.json` の値を警告なしに使うので、古いマニフェストの版が
marketplace 側で設定した版を**覆い隠しうる**」と警告している。

**本プロダクトは意図的に両方へ書き、lint #1 が一致を機械強制している。** 警告が指す危険は「2つが食い違うこと」であり、
食い違いを機械で潰してあるなら覆い隠しは起きない。**なお公式バリデータはこれを検査できない** —
同ドキュメントによれば、エントリの version と `plugin.json` の照合が走るのは
**`source` がローカルパスのときだけ**で、本プロダクトは `source: github` である。**ここは自前の lint にしか守れない。**

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
| `skills/` | 執筆・計測の規範（`<name>/SKILL.md`） | **する**（→ §4b） |
| `templates/` `docs/` | 雛形・正本ドキュメント | しない（明示 Read） |
| `scripts/` | lint / bump / hooks テスト | しない（dev-side） |
| `takumi/` `tests/` | ドメインモデル（Python）と単体テスト | しない（dev-side。Tier 1 と `--workspace` 検証で使う。[domain-model.md](domain-model.md)） |
| `.github/` | CI（lint / unittest / shellcheck / hooks） | しない（dev-side） |
- 配布前のローカル検証に CLI `claude plugin validate` が使える。**必ず manifest のパスを直接渡す** —
  `claude plugin validate .`（ディレクトリ指定）は marketplace.json しか見ず**コンポーネントを歩かない**（2026-07-26 実測）。
  ただし CLI 検証が通っても Cowork で hook が発火する保証にはならない（§2）。

### 1b. プラグインの入れ方は3通りあり、**更新できるのは1つだけ**（2026-07-26 に実測して確定）

| 入れ方 | 更新 | 備考 |
|---|---|---|
| **GitHub から marketplace を追加**（`RetryYN/TAKUMI_CMO-Claude_Cowark`） | **できる** | **これが唯一の正しい配布経路**（2026-07-26 に add → install → update を実測。v5.5.0 / `displayName: 匠CMO` まで正しく入った） |
| marketplace.json への**直URL**を追加 | **install が落ちる**（プラグイン側では直せない） | 後述 |
| **ローカルアップロード**（フォルダ・zip を直接） | **できない** | 取得先が無いので「マーケットプレイスの更新に失敗しました」になる。**入れ直すには削除して marketplace から追加し直す** |

**直URL が落ちる件（2026-07-26 実測。プラグイン側では直せない）**

一次情報はこう書いている:

> 「URL ベースの marketplace は **marketplace.json 自体しかダウンロードしない**。
> サーバ上のプラグインファイルは落とさないので、相対パスは解決できない。
> URL 配布では GitHub・npm・git URL のソースを使うこと」

そこで `"source": "./"` を明示 github ソースへ変えた。**が、それでも直URL 追加の install は同じエラーで落ちた**
（`claude` CLI v2.1.219 で前後を実測）:

```
✘ Failed to install: ENOTDIR: not a directory,
  scandir '~/.claude/plugins/marketplaces/retryyn-takumi-cmo'
```

**エラーは marketplace のキャッシュ位置を scandir しようとして起きており、プラグインの source を見る前段で落ちている。**
URL 追加ではそのパスに marketplace.json が**ファイルとして**置かれるので、ディレクトリとして走査できない。
**つまり source の書き方では直らない。CLI 側の URL 経路の制約。**

**それでも明示 github ソースにしておく理由**は別にある:

1. 一次情報が URL 配布では外部ソースを使えと明記している（相対パスは仕様上サポート外の経路がある）
2. **Cowork の marketplace 同期はサーバ側で走り、各プラグインの `source.repo` を検証する**
   （上流 issue #61271 の実ログ: `[remoteMarketplaceOps] … "error": "Repository not found on github.com…"`）。
   `"./"` には `repo` が無いので、**この検証を通れない可能性がある** —
   利用者側で出た「マーケットプレイスの更新に失敗しました」の原因候補として最も有力だが、
   **サーバ側の挙動は手元から観測できないので断定しない**（Cowork のログで確認できたら本節を更新する）

`lint #38` が相対パスを機械的に禁じる。

> **「追加の仕方によって壊れる」種類なので、開発側の手元では再現しない。**
> 障害報告を受けたら、まず**どうやって入れたか**を訊く。

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

### 2b. hook 出力の契約（2026-07-26 に一次情報で確認）

**【一次情報・確認済み】** 出典: `code.claude.com/docs/en/hooks`（`docs.claude.com/en/docs/claude-code/hooks` は 301 でここへ移る）。

- `PreToolUse` の `hookSpecificOutput` が取るフィールド: **`permissionDecision`**（`allow` / `deny` / `ask` / `defer`）・**`permissionDecisionReason`**・**`updatedInput`**（ツール引数を実行前に差し替える）・**`additionalContext`**。
- **`additionalContext` は PreToolUse でも有効**（ツール結果の隣に差し込まれる）。対応イベントは `SessionStart` / `Setup` / `SubagentStart`、`UserPromptSubmit` / `UserPromptExpansion`、`PreToolUse` / `PostToolUse` / `PostToolUseFailure` / `PostToolBatch`、`Stop` / `SubagentStop`。
- **なぜ確認したか**: 匠CMO の警告系（`navigate-warn` と、各ゲートの `warn` モード）は PreToolUse で `additionalContext` を返す。もしこれが PreToolUse で未対応なら、**警告は黙って捨てられ、何も言わない hook が「動いている」ように見えていた**。仕様上は正しく届く。
- **未採用の選択肢**: `permissionDecision: "ask"`（人間に許可を求める）と `updatedInput`（引数の差し替え）は現在どのゲートも使っていない。匠CMO のゲートは **deny か warn の二択**で運用している。

## 3. ゲート機構（memory/.workflow/ フラグ + GATE_MODE）

- ゲートの実体は `memory/.workflow/` のフラグファイル（例: `bulk_send` / `k_done` / `ov_done` / `critic_pending` / `critic_pass` / `money_alert` / `verify_allowlist`）。hook スクリプトがフラグを読んで allow / warn / deny を返す。
- 各 hook 先頭の `GATE_MODE="${TAKUMI_GATE_MODE:-deny}"` が既定モード（2026-07-24 に warn→deny 昇格済み）。環境変数 `TAKUMI_GATE_MODE` はテスト時の両モード検証用。
- **hook 11本**（`hooks/scripts/`）: workflow-gate / ov-gate / rm-guard / brand-isolation-guard / critic-gate / url-guard（ゼロ課金ゲート）/ **agent-parallel-gate**（サブエージェント同時起動の上限4体。**既定は warn** — 昇格判断は V79）/ navigate-warn / injection-warn / money-watch / session-start。**11本すべてが `scripts/test-hooks.sh` で実行され CI で検査される**（登録と検査の突合は lint #23。2026-07-26 まで navigate-warn の1本だけが無検査で配布されていた）。
- **限界（自己規律で補う領域）**: hook はツール引数の文字列しか見えない。`ref_150` 等の参照IDの解決先（type=password か）は判定できない（escalations E1）。フラグは Bash から直接 touch/rm で技術的に迂回可能（意図的迂回ではなく手順飛ばしへの防御）。硬い防御は Money Watch・URL Guard・人間承認が担う。

## 4. commands / agents / MCP の供給

- **commands（スラッシュコマンド）**: `commands/*.md`（日本語名）がメニューに並ぶ。frontmatter の description（Use when）で自然文からの自動発火も効く。薄いラッパーで `procedures/takumi-*.md` を Read して実行。
- **agents（サブエージェント）**: `agents/*.md`。Cowork では Agent ツールが供給されるが、**未供給の場合は main ループが該当エージェント定義を Read して直接実行するフォールバック**（conventions §4）。委譲プロンプトにはプラグイン内ファイルの**絶対パス**を渡す（相対は synced 環境で不達）。
- **プラグイン実体パス**は `/root/.claude/plugins/synced/<plugin>`（相対 `templates/` 等が不達 → **Glob `**/<filename>` フォールバック必須**。パス解決規則は conventions §1）。
- **DesignSync（Claude Design 連携）は Cowork セッションに供給される**（実機確認済み）。素材パックを claude.ai/design プロジェクトへ同期可（finalize_plan の承認制）。なお Claude Design の公式ハンドオフ（handoff bundle）は「→ Claude Code」向けで、→ Cowork への受け渡し経路は未確認。本プラグインは DesignSync（claude.ai/design プロジェクトの読み書き）経路を使う。
- 出力提示は `mcp__cowork__present_files`（パスは outputs スクラッチパッド or プライマリ workspace に限る・非プライマリフォルダは拒否）、フォルダのマウントは `request_cowork_directory`。
- 同梱 MCP は「ローカルMCPサーバーを含む」承認後に供給される。ブラウザは Claude in Chrome が前提エンジン。

### 4b. skills の配置（2026-07-25 に一次情報で確認・配置を変更）

公式仕様（[plugins-reference](https://code.claude.com/docs/en/plugins-reference)）:

> **Location**: `skills/` or `commands/` directory in plugin root, or a single `SKILL.md` file at the plugin root

- **`skills/<name>/SKILL.md` が正しい配置**。`references/` はプラグインのコンポーネント・ディレクトリではなく、**自動探索の対象外**だった（frontmatter の `description: … Use when …` が一度も発火判定に使われていなかった）。
- 旧配置は「自動発火させない内部教科書」という**意図的な設計**だったが、その代償が **escalations E6**（委譲先エージェントがプラグイン同梱ファイルに到達できず、規範が適用されないまま審査・法規チェックが走る）。E6 の実害の方が大きいと判断して `skills/` へ移した（判断と緩和策は [command-registry.md](command-registry.md) のスキル台帳が正本）。
- **移設の代償**: 自動発火するため、業務の入口がコマンドを飛ばしてスキルに逸れうる。session-rules (3) で「業務の入口は必ずコマンド／手順書。変更操作の前に該当手順書へ合流する」を規定し、**V50 で実測する**。
- 移設しても**手順書からの明示 Read は従来どおり有効**（conventions §1 のパス解決規則）。二重の到達経路になる。

**移設の代償その2 — `/` の一覧が埋まる（2026-07-26 にユーザー報告で発覚・一次情報で対処）**

コマンドを9本に束ねても、**42本のスキルがスラッシュコマンドの一覧に並んでいた**。
公式は custom commands と skills を統合しており（"A file at `.claude/commands/deploy.md` and a skill at
`.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way"）、**スキルは既定で
利用者が `/名前` で叩ける**ためである。

**【一次情報・確認済み】** `code.claude.com/docs/en/skills` §Control who invokes a skill:

| frontmatter | 利用者が起動 | Claude が起動 | context への載り方 |
|---|---|---|---|
| （既定） | できる | できる | description は常時。本文は起動時 |
| `disable-model-invocation: true` | できる | **できない** | description も載らない |
| **`user-invocable: false`** | **できない** | できる | **description は常時。本文は起動時** |

> `user-invocable: false`: "Only Claude can invoke the skill. **Use this for background knowledge that
> isn't actionable as a command.** … Claude should know this when relevant, but `/legacy-system-context`
> isn't a meaningful action for users to take."

**匠CMO の42スキルはまさにこれ** — 規範・知識であって、利用者が打つ動作ではない（打つ動作は9本のコマンド）。
全スキルに **`user-invocable: false`** を付けた。**一覧から消えるだけで、description は context に残るため
自動発火は落ちない**。`lint #30` が新規スキルの付け忘れを止める。

**サブエージェントの `skills:` preload には影響しない** — 公式注記のとおり preload は起動時に本文を注入する
別経路（"Subagents with preloaded skills work differently: the full skill content is injected at startup"）。

### 4c. プラグイン同梱エージェントの frontmatter（2026-07-26 に一次情報で確認）

公式仕様（[plugins-reference](https://code.claude.com/docs/en/plugins-reference)）:

> Plugin agents support `name`, `description`, `model`, `effort`, `maxTurns`, `tools`,
> `disallowedTools`, `skills`, `memory`, `background`, and `isolation` frontmatter fields.
> **For security reasons, `hooks`, `mcpServers`, and `permissionMode` are not supported
> for plugin-shipped agents.**

- **`model`**: `sonnet` / `opus` / `haiku` / **`fable`** / フルモデルID / `inherit`（既定 `inherit`）
- **`effort`**: `low` / `medium` / `high` / `xhigh` / `max`。**セッションの effort を上書きする**。
  **使える段はモデルによる** — 公式の対応表に **Haiku は載っていない＝非対応**
  （[model-config](https://code.claude.com/docs/en/model-config)）。
  **「effort の尺度はモデルごとに較正されており、同じ段名がモデル間で同じ値を表さない」**
- **`skills`**: 起動時に**スキルの全文**をエージェントの文脈へ注入する（説明文だけではない）。
  載せなかったスキルも Skill ツールで実行中に呼べる。
  **→ E6（委譲先が `skills/**` を Read できない）に対して、ファイルを読まずに規範を届ける経路になる。**
- **ただし `skills:` の失敗は静か**: 「listed skill が見つからないか無効な場合、スキップして
  **デバッグログに警告を出す**」。**名前を1文字間違えると規範ゼロで走る。**
  `scripts/lint.py` #21 が実在確認をする＋エージェント本文の「正本を Read する」指示は残す（二重化）。

**級（戦略級／戦術級／職人級／作業者級）とモデル・エフォート・preload の割当は
[agent-tiers.md](agent-tiers.md) が正本。**

## 5. cloud / ローカルの分断（資産）

- クラウドセッションの作業場はコンテナ内のみ、ローカルは別ファイルシステム。**資産（knowledge/tasks/memory/コマンド）は自動同期されない**（escalations E3）。継続運用は「フォルダを追加」で業務フォルダを接続して永続化する。
- スキル/コマンドの登録タイミング: cloud=同一セッション内で即時登録されうる / ローカル=次セッションから（環境差あり）。
- ローカルスケジュール（このコンピュータで実行）は **AI/プラグインから登録できる**（2026-07-26 に一次情報で確認し escalations E2 は**解消**。運用の正本は `docs/unattended-ops.md` と `procedures/takumi-task.md`）。

## 6. 検証は「dev↔Cowork の往復」で完結する（→ 開発ワークフロー.md §二層検証）

- **Tier 1（機械・毎コミット・ローカル/CI）**: lint / 単体テスト / test-hooks / shellcheck。参照整合・ドメイン不変条件・hook スクリプトのロジックを保証する。**hook の"配線"は検証できない**（ローカルはフェイルオープン）。
- **Tier 2（実機・節目・Cowork）**: `/匠検証`（takumi-verify）を実機セッションで実行（**ローカルで可** — 配布判断は環境名ではなく**ゲートを全数実測できたか**で決める。正本は [TESTING.md](../TESTING.md) の「配布判断の4条件」）。hook の実配線・コマンド経路・エージェント起動・ブランド分離など**Tier 1 が構造的に検証できない項目**を実測する。ユーザーが実行 → PASS/FAIL 表を開発側に貼り戻す往復で確定。
- 検証の外部無害原則: ブラウザは example.com と the-internet.herokuapp.com（V5(b) 固定）のみ。`verify_allowlist` で機械強制し、リスト外 navigate は url-guard が deny する。
