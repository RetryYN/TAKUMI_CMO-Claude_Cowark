# エージェントの級（`agents/` 10体 — 配役とモデル割当の正本）

**サブエージェントを「何をする人か」ではなく「どれだけ深く考える必要があるか」で4級に分ける。**
級が **effort（推論の深さ）** を決め、**モデル家系**は仕事の当たり外れ（論理／審美／速度）で選ぶ。
この2軸を混ぜると、「戦略の壁打ちが速いモデルで浅く返る」「定型照合に最上位モデルを使う」が同時に起きる。

## 一次情報（Cowork/Claude Code の仕様・2026-07-26 確認）

- **プラグイン同梱エージェントが使えるフロントマター**:
  `name` / `description` / `model` / `effort` / `maxTurns` / `tools` / `disallowedTools` /
  **`skills`** / `memory` / `background` / `isolation`。
  **`hooks` / `mcpServers` / `permissionMode` はセキュリティ上サポートされない**
  （[plugins-reference](https://code.claude.com/docs/en/plugins-reference)）
- **`model`**: `sonnet` / `opus` / `haiku` / **`fable`** / フルモデルID / `inherit`（既定は `inherit`）
- **`effort`**: `low` / `medium` / `high` / `xhigh` / `max`。**セッションの effort を上書きする**。
  **利用できる段はモデルによる**（[sub-agents](https://code.claude.com/docs/en/sub-agents)）

| モデル | 使える effort |
|---|---|
| Fable 5 | `low` `medium` `high` `xhigh` `max` |
| Opus 5 / Sonnet 5 / Opus 4.8 / Opus 4.7 | `low` `medium` `high` `xhigh` `max` |
| Opus 4.6 / Sonnet 4.6 | `low` `medium` `high` `max` |
| **Haiku** | **表に載っていない＝effort 非対応** |

> **「表に無いモデルは effort をサポートしない」と公式に明記されている**（[model-config](https://code.claude.com/docs/en/model-config)）。
> **Haiku を使う級では `effort` を書かない。** 書いても効かず、「設定したつもり」の負債になる。
>
> もう1つ重要な一次情報: **「effort の尺度はモデルごとに較正されており、同じ段名が
> モデル間で同じ値を表さない」**。だから *Fable の medium* と *Opus の high* を同じ級に置く設計は正しい
> — 段名を横並びに比較していないため。

## 4つの級

| 級 | 深く考える側 | 速い側 | 何を任せるか | 外したときのコスト |
|---|---|---|---|---|
| **戦略級** | `fable` / `medium` | `opus` / `high` | 長く効く判断・前提の疑い・構造の破綻予測 | **後から直すのが最も高い**（土俵・指標・構成の選び直し） |
| **戦術級** | `fable` / `low` | `opus` / `medium` | ゲートと監査（送出前・個人データ・成果物審査） | 高い（**不可逆な送出が通る**／規約違反が世に出る） |
| **職人級** | `opus` / `low` | `sonnet` / `high`〜`medium` | 作る（執筆・デザイン生成） | やり直せる（作り直す時間） |
| **作業者級** | `sonnet` / `medium`〜`low` | `haiku`（**effort 指定なし**） | 定型の照合・抽出・整形 | 低い（ただし**見落とすと上の級が誤った前提で走る**） |

**級は effort を決める。モデル家系は仕事で選ぶ。**

- **`fable`** — 審美・生成の当たりが良い。**戦略級と戦術級の2段しか無い**（職人級以下に fable の段は置かない）
- **`opus`** — 論理・判断・反証。ゲートと壁打ちの既定
- **`sonnet`** — 実務の速度と量。書く・照合する
- **`haiku`** — 定型。**effort を持たない**

## 配役（10体）

| エージェント | 級 | model | effort | 役割 |
|---|---|---|---|---|
| `cmo-strategist` | **戦略級** | `opus` | `high` | 上流ループの立案（ポジショニング→KPIツリー→ロードマップ） |
| `growth-challenger` | **戦略級** | `opus` | `high` | 「無難すぎる」を疑う攻めの壁打ち（11の問い） |
| `strategy-advisor` | **戦略級** | `opus` | `high` | 長く効く判断のセカンドオピニオン（session-rules (11)(12)） |
| `risk-forecaster` | **戦略級** | `fable` | `medium` | 構造由来の破綻の先読み（実装前） |
| `pre-send-verifier` | **戦術級** | `opus` | `medium` | **不可逆送出の直前**の敵対的監査 |
| `privacy-auditor` | **戦術級** | `opus` | `medium` | 個人データ・同意・規約の監査 |
| `design-critic` | **戦術級** | `opus` | `medium` | ビジュアル成果物の審査（**PASS まで渡さない**ゲート） |
| `design-artisan` | **職人級** | `fable` | `high` | ビジュアル生成（**例外。下記**） |
| `deliverable-writer` | **職人級** | `sonnet` | `high` | 成果物の本格執筆 |
| `outcome-verifier` | **作業者級** | `sonnet` | `medium` | 証跡の突合（**確定数だけを成果に数える**） |

### 級の割り当てで迷ったときの原則

- **ゲートは戦術級**（`pre-send-verifier` / `privacy-auditor` / `design-critic`）。
  作るのではなく「通すか止めるか」を判定する仕事は、判断の質が要るが対象は1件で範囲が限られる
- **生成は職人級**（`design-artisan` / `deliverable-writer`）。やり直せるので最上位は要らないが、**腕が要る**
- **「後から直すのが高くつく」なら戦略級**。安ければ下げる

### 例外は1つだけ: `design-artisan`

**職人級だが `fable` を使い、effort も `high` のまま据え置く。**

理由: 見た目の生成は**審美の当たり外れ**で決まり、判断の深さ（＝級）で決まらない。
fable の段を下げると成果物の質が直接落ちる。**級の表はここに適用しない。**

fable が月次上限・不達で `Agent terminated early due to an API error` になったときは、
**`model: sonnet` を明示して同じプロンプトで再委譲する**（自動フォールバックは無い＝呼び出し側の責務。
正本は [media-pipeline.md](media-pipeline.md) 末尾）。

### `haiku` 帯は空いている

**作業者級の `haiku` 側に常設エージェントは今のところ無い。**
`outcome-verifier` は証跡の食い違いを見抜く必要があるので `sonnet` / `medium` に置いた。
定型の抽出・整形（ログの構造化、表の正規化など）が増えたらここに追加する。
**空いている段を埋めるためにエージェントを作らない。**

## スキルの合成（`skills:` によるルーティング）

`skills:` は**起動時にスキルの全文をエージェントの文脈へ注入する**（説明文だけではない）。
これが「どのエージェントがどの規範で動くか」の宣言になる。

| エージェント | preload するスキル | なぜ毎回要るか |
|---|---|---|
| `cmo-strategist` | `winning-position-jp` `stp-jp` `kpi-design-jp` `scale-strategy-jp` | 勝ち筋・誰に・何で測る・規模。**4点が揃わない戦略は出せない** |
| `growth-challenger` | `winning-position-jp` `offer-design-jp` `referral-advocacy-jp` `demand-timing-jp` | 11の問いのうち4つ（オファー・紹介・時期・規模）が**この4本に対応** |
| `strategy-advisor` | `kpi-design-jp` `hypothesis-design-jp` `channel-planning-jp` | 壁打ちの論点がほぼこの3本に落ちる |
| `risk-forecaster` | `kpi-design-jp` `hypothesis-design-jp` | 「時間が経つと壊れるもの」は指標定義と前提の話 |
| `pre-send-verifier` | `ad-compliance-jp` | **送出前の法規チェックが本務** |
| `privacy-auditor` | `ga4-jp` | PII 禁止・データ保持の一次情報がここ |
| `design-critic` | `web-design` `design-evidence-jp` `psych-ux-jp` `ad-compliance-jp` | 審査基準そのもの |
| `design-artisan` | `web-design` `design-evidence-jp` `psych-ux-jp` | 生成の規範（数値の正本を含む） |
| `deliverable-writer` | `ad-compliance-jp` `logical-writing` | 最終稿は必ず法規を通り、構成の型が要る |
| `outcome-verifier` | `kpi-design-jp` | 「ツリーに無い指標は返さない」を守るため |

**preload は「毎回必ず要るもの」だけにする。** 全文が注入されるので、
迷ったら入れないほうがよい。依頼ごとに変わる規範は **Skill ツールで実行中に取る**
（`skills:` は preload を決めるだけで、載せなかったスキルも呼べる）。

### escalations E6 への効き（重要）

**E6**（永続フォルダ未接続だと委譲先が `skills/**` を Read できず、規範が一切適用されない）に対し、
`skills:` は**ファイルを読まずに規範を届ける経路**になる。E6 の実害を最も直接に減らす手段。

**ただし解決とはしない。理由は「失敗が静かだから」:**

> 「listed skill が見つからないか無効な場合、Claude Code はそれをスキップし、
> **デバッグログに警告を出す**」（sub-agents 一次情報）

つまり**名前を1文字間違えても、誰も気づかないまま規範ゼロで走る**。したがって:

1. **エージェント本文の「正本を Read する」指示は消さない**（preload が落ちたときの二重化）
2. **「到達できなかったら応答冒頭で1行申告する」義務も残す**（E6 の既存緩和策）
3. **preload が実際に効いているかは Tier 2 の V78 で実測する**
   （preload したスキルにしか書いていない内容を答えられるかで判定する）

## 並列起動の上限 — 同時 **4体**

**本体の既定は同時20体**（超えると `Concurrent subagent limit reached` で失敗し、
再試行しないよう指示が出る）。**匠CMO はこれを4体に絞る。**

理由は3つ:

1. **費用とレート** — 戦略級（`opus`/`high`・`fable`/`medium`）が20体走ると跳ね上がる
2. **後始末が追えない** — 並列で失敗した委譲の切り分けは、体数が増えるほど指数的に難しくなる
3. **本プラグインの並列は元々2〜3体** — `docs/parts/pre-setup-council.md` の合議は常設2体、
   `/戦略` の壁打ちは2体。**4体あれば設計上の並列はすべて収まる**

### 強制の3枚

| 層 | 何が効くか | 限界 |
|---|---|---|
| **① 環境変数**（本命） | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=4` を利用者の設定に置くと**本体が弾く** | **プラグインからは設定できない**（利用者の環境。`settings.json` の `env` ブロック等で本人が置く） |
| **② hook**（`hooks/scripts/agent-parallel-gate.sh`） | PreToolUse(Agent) で数え、上限で止める | **E4/E5** — ローカル Cowork では hooks 未配線、cloud でも発火は保証されない |
| **③ session-rules** | メインループが「5体目を起動しない」判断をする | 規約なので破られうる |

**①がある人は①で終わり。無い人のために②③がある。**

### hook の設計（数え方と、なぜ warn から始めるか）

PreToolUse(Agent) で `memory/.workflow/agents_running` に1行 append、PostToolUse(Agent) で1行 pop。
**完了シグナルを取りこぼすと枠が残る**ので、TTL（既定30分）を過ぎた行は掃除する
（掃除が無いと、失敗した委譲1件で以後ずっと枠が減ったままになる）。

**既定は `warn`（注入のみ）。** 他のゲートと同じ段階導入（TESTING.md「GATE_MODE 昇格」）だが、
理由はこのゲート固有:

> **並列上限は「止めそこねても事故にならない」種類の規約である。**
> 不可逆送出やブランド汚染と違い、5体走っても壊れるものは無い（費用がかさむだけ）。
> 一方、**誤爆で正当な委譲を殺すと作業が止まる**。実害の非対称が逆向きなので、
> deny を急がない。**V79 で誤爆ゼロを実測してから昇格する。**

環境変数で調整できる（開発・検証用）:
`TAKUMI_MAX_PARALLEL_AGENTS`（既定4）/ `TAKUMI_AGENT_SLOT_TTL`（既定1800秒）/
`TAKUMI_PARALLEL_GATE_MODE`（`warn` | `deny`）

## モデル退役への追従（エイリアスだけを書く）

**`model:` にはエイリアス（`opus` / `sonnet` / `haiku` / `fable`）だけを書き、フルモデルIDを書かない。**

> **エイリアスはプロバイダごとの推奨バージョンを指し、時間とともに更新される。**
> 特定バージョンに固定したい場合はフルモデル名（例: `claude-opus-5`）を使う
> （[model-config](https://code.claude.com/docs/en/model-config)・一次情報）

つまり**エイリアスで書いておけば、モデルが退役しても自動で新しい世代に移る**。
逆に `claude-opus-5` のように書くと、**そのモデルが退役した日に該当エージェントが止まる**
（プラグインは配布物なので、こちらでは気づけない）。`scripts/lint.py` #21 が直書きを落とす。

### 自動で追従しないもの（2つ）

**① 上の effort 対応表**

新しい世代が別の段構成を持つ可能性がある（実際 Opus 4.6 / Sonnet 4.6 に `xhigh` は無い）。
**この表は 2026-07-26 時点の写しであり、モデル世代が変わったら一次情報で取り直す。**
本文中の判断（例: 「Haiku には effort を書かない」）も、そのときに再確認する。

**② プロバイダによるエイリアスの解決先**

| プロバイダ | `opus` | `sonnet` |
|---|---|---|
| Anthropic API（Cowork の既定） | Opus 5 | Sonnet 5 |
| Claude Platform on AWS | Opus 5 | Sonnet 4.6 |
| Amazon Bedrock / Google Cloud Agent Platform | Opus 5 | **Sonnet 4.5** |
| Microsoft Foundry | **Opus 4.6** | **Sonnet 4.5** |

**ここに級が静かに劣化する経路がある。**

- **Sonnet 4.5 は effort 対応表に載っていない＝effort 非対応。**
  Bedrock / GCP / Foundry では `sonnet` がここへ解決するため、
  **職人級（`sonnet`/`high`）と作業者級（`sonnet`/`medium`）の effort が効かなくなる**
- **Opus 4.6 に `xhigh` は無い**（`xhigh` を指定すると `high` に落ちる。
  本プラグインは `xhigh` を使っていないので現状は影響しない）

**エラーにならず、黙って段が消える。** 成果物の質が理由不明に落ちたら、まずここを疑う。
Anthropic API 以外で運用する場合は `ANTHROPIC_DEFAULT_SONNET_MODEL` 等で解決先を上げる
（環境変数はプラグイン側からは制御できない＝**利用者の環境の話**）。

## 不変条件（`scripts/lint.py` が機械で止める）

1. **すべてのエージェントに `model` がある**（`inherit` 任せにしない — 級が意味を失う）。
   **値はエイリアス（`opus`/`sonnet`/`haiku`/`fable`）のみ** — フルモデルIDの直書きは退役で止まる
2. **`haiku` 以外のエージェントに `effort` がある**（設定漏れを「既定でいい」と区別する）
3. **`haiku` のエージェントに `effort` を書かない**（効かない設定を置かない）
4. **`effort` の値は `low` `medium` `high` `xhigh` `max` のいずれか**
5. **この表と実体が一致する**（級・model・effort が agent-tiers.md の表と食い違ったら落ちる）
6. **`skills:` に書いた名前が実在するスキルを指す**（**静かに落ちる設定を機械で拾う**）
7. **`hooks` / `mcpServers` / `permissionMode` を書かない**（プラグイン同梱では効かない）

## エージェントを1体足すときの手順

1. **級を先に決める**（「外したら後から直すのが高いか」で決める。役割名から決めない）
2. `model` と `effort` を級の表から取る（`haiku` なら `effort` を書かない）
3. `skills:` に**毎回必ず要る規範だけ**を書く
4. 本文に「正本を Read する」指示と「到達できなかったら申告する」義務を書く（preload の二重化）
5. この表に行を足す（**lint が要求する**）
6. `docs/command-registry.md` の台帳と、呼び出し元の手順書・部品に配線する
7. golden（`docs/evals.md`）と Tier 2（`procedures/takumi-verify.md` + `templates/verify-task.yaml`）を足す
