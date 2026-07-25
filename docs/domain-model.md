# ドメインモデル（正本）— オブジェクト型 DDD

TAKUMI-CMO のドメインを集約・エンティティ・値オブジェクトで表す。**日本語のユビキタス言語**を一次言語とし、
コード（`takumi/domain/`）の英語クラス名はここと1対1で対応させる。手順書・コマンドはこの言葉で書く。

## ユビキタス言語 ↔ コードの対応

| 日本語（ユビキタス） | コード（英語） | 種別 | 意味 |
|---|---|---|---|
| ブランド | `Brand` | 集約ルート | 無双させる単位。すべての施策・記憶が1ブランドに閉じる |
| ブランドslug | `BrandSlug` | 値オブジェクト | ブランドの不変な識別子（`knowledge/brands/<slug>/` の名前） |
| ブランド状態 | `BrandStatus` | 値オブジェクト | `active` / `archived` |
| ブランド台帳 | `BrandRegistry` | 集約 | 全ブランドの集合＋アクティブブランドの指し先 |
| ブランド区画 | `BrandPartition` | 値オブジェクト | `knowledge/brands/<slug>/` 配下。他区画から隔離される |
| 戦略 | `Strategy` | エンティティ | 3C・ポジショニング・施策ロードマップ（上流ループの産物） |
| ロードマップ項目 | `RoadmapItem` | 値オブジェクト | 施策1件。媒体とドライバー（KPIノード名）を必ず持つ |
| KPIツリー | `KpiTree` | 集約 | 先行/遅行指標の階層。上流下流が共有する背骨。オーガニック指標のみ（有料広告のCAC/LTVは持たない） |
| 指標ノード | `KpiNode` | エンティティ | ツリーの1ノード。有料指標を名前に持てない |
| 指標の種別 | `KpiKind` | 値オブジェクト | 先行 / 遅行 |
| キャンペーン | `Campaign` | エンティティ | 複数媒体を1つの目標の下に束ねる統括単位（下流のオーケストレーション） |
| 上流ループ | `UpstreamLoop` | ドメインサービス | 戦略ループ（リサーチ→仮説→戦略→計画→改善・トップダウン） |
| 下流ループ | `DownstreamLoop` | ドメインサービス | 実行ループ（計画→リサーチ→企画→実行→計測→改善・ボトムアップ） |
| 計画の受け渡し | `PlanHandoff` | 値オブジェクト | ∞の下り。戦略→実行の実行ブリーフ（目標KPI・媒体・手元で動かす葉） |
| 計測の受け渡し | `MeasurementHandoff` | 値オブジェクト | ∞の上り。実測をKPIツリーのノードに紐づけて戻す |
| タスク | `Task` | エンティティ | 単一の仕事。動詞型: 計画/リサーチ/収集/クリエイティブ/分析/掃き出し |
| 媒体 | `Channel` | 値オブジェクト | オーガニック媒体。有料出稿媒体は持たない（Owned / Earned のみ、Paid は構造的に不在） |
| 媒体種別 | `ChannelKind` | 値オブジェクト | **Owned**: SNS / コンテンツ / Webサイト / オウンドメディア / メール ／ **Earned**: 広報・連携。**Paid は持たない**（ゼロ広告費） |
| ゲート | `Gate` | ドメインサービス（hook） | 不変条件の機械強制（Brand Isolation / ゼロ課金 / 送出監査 等） |

## 匠の∞ループ（中核のドメインサービス）

上流ループ `UpstreamLoop`（戦略）と下流ループ `DownstreamLoop`（実行）が **計画** と **計測** で結ばれた ∞ 字。

- 交差点の受け渡し: 下り = **計画**（`Strategy` → `Campaign` の実行ブリーフ = `PlanHandoff`）／上り = **計測・改善**（実測 = `MeasurementHandoff` → `KpiTree` 更新 → 再 `Strategy`）。
- 両ループが共有する背骨 = `KpiTree`。戦略も実行も「改善」を持つ＝匠の技で磨き続ける。

### ∞が閉じるための不変条件（コードで強制）

**受け渡しの両端は必ず KPIツリーのノードを経由する。** これが切れると、実行の結果が戦略に返らない。

1. **下り**: `Campaign.goal_kpi` は `Strategy.kpi_tree` に実在するノード名でなければならない（`Campaign.validate_against`）。背骨から浮いたキャンペーンは作れない。
2. **下り**: `Strategy.roadmap` の各施策は `RoadmapItem.driver`（KPIノード名）を必ず持ち、それがツリーに実在する。「どの指標を動かすのか言えない施策」を持てない。
3. **上り**: `DownstreamLoop.hand_up` はツリーに無い指標の実測を受け取らない。測るなら先にツリーへ置く（定義を後から変えると過去と比較できない）。
4. **区画**: キャンペーンと戦略のブランドが一致しない受け渡しは拒否する。

補助の観測点: `Strategy.undriven_leaves()`（施策の当てがない指標）/ `DownstreamLoop.unmeasured_leaves()`（測る当てがない指標）/ `DownstreamLoop.stalled_nodes()`（伸びが閾値未満＝ /戦略 の再立案フラグ）。

### ゼロ広告費は「指標」と「媒体」の両側で締める

`KpiNode` が有料**指標**を拒み、`Channel` が有料**媒体**を拒む（共通判定は `takumi/domain/paid_guard.py`）。
**過剰検知もガードの失敗**として扱う — ラテン文字の語は単語境界で照合する（部分一致だと実在の媒体 "Threads" が "ads" で弾かれる。2026-07-25 の回帰）。日本語の語だけ部分一致で見る。

## Brand 集約（中心）

**集約ルート = `Brand`。マルチブランドの分離単位。** 1インストールで複数ブランドを扱い、記憶は区画で隔離する。

- 同一性: `BrandSlug`（`^[a-z0-9][a-z0-9-]*$`、2〜40字。ブランド台帳内で一意）。
- 保持物: 表示名 / 状態（`active` / `archived`）/ 作成日 / ポジショニング / ICP / ブランドガイド（トーン・NG・配色）。
- 永続化: `knowledge/brands/<slug>/`（`brand.yaml` ほか）。台帳は `knowledge/brands.yaml`、アクティブ指し先は `knowledge/.active-brand`。

### 不変条件（invariants）— コードと hook で守る
1. **slug 一意**: ブランド台帳に同じ slug は2つ存在しない（`BrandRegistry`）。
2. **区画隔離**: 変更操作はアクティブブランドの `BrandPartition` 内だけを対象にできる。別区画への書き込みは禁止（**Brand Isolation Guard** hook が機械強制。escalations の cloud 限定に留意）。
3. **アクティブ確定前段**: すべての変更系タスクは、アクティブブランドが確定してから実行される（未確定なら停止）。
4. **ゼロ課金**: どのブランドの施策も有料出稿・課金導線を含まない（**URL Guard / Money Watch** が機械遮断）。KPIツリーは有料指標（広告費・CAC・LTV）をノードに持たない。

## 実装状況（TDD で段階実装）

**この表は `scripts/lint.py` が実体と突合する**（宣言だけが先行する負債を機械で止める）。実装したクラスは `takumi/domain/*.py` に `class` 定義が実在し、宣言したテストファイルも実在しなければ CI が落ちる。逆に、コードにあるクラスがこの正本に載っていなくても落ちる。

| 対象 | 状態 | テスト |
|---|---|---|
| `BrandSlug` / `BrandStatus` / `Brand` / `BrandRegistry` / `BrandPartition` | 実装済み | `tests/test_brand.py` |
| `KpiTree` / `KpiNode` / `KpiKind` | 実装済み | `tests/test_kpi_tree.py` |
| `Channel` / `ChannelKind` | 実装済み | `tests/test_channel.py` |
| `Strategy` / `RoadmapItem` | 実装済み | `tests/test_strategy.py` |
| `Campaign` | 実装済み | `tests/test_campaign.py` |
| `UpstreamLoop` / `DownstreamLoop` / `PlanHandoff` / `MeasurementHandoff` | 実装済み | `tests/test_loop.py` |
| `Task` | **コード化しない** — ランタイム側の表現（`tasks/*.yaml` + `docs/steps-reference.md` の A〜K）が正本。Python に写すと二重管理になる | — |
| `Gate` | **コード化しない** — 実体は `hooks/scripts/*.sh`。判定ロジックは `scripts/test-hooks.sh` が保証する | — |

各対象は「テストを先に書いて red → 実装 → green」（[開発ワークフロー.md](開発ワークフロー.md) §2）。

## ワークスペース検証（ドメインモデルを実データに適用する）

`scripts/lint.py --workspace <path>`（既定はカレントディレクトリ）が、利用者の `knowledge/` を
ドメインモデルで検証する。実装は `takumi/workspace.py`、テストは `tests/test_workspace.py`。
**`knowledge/` が無ければ何も起きない**ため、プラグインリポジトリ単体の lint（CI）には影響しない。

読み込みは呼び出し側から注入する（lint は PyYAML の `safe_load`、テストは `json.loads`）。
ドメイン層に YAML パーサへの依存を持ち込まないため。PyYAML が無い環境では WARN でスキップする。

### 検証するファイルと形（ランタイム ↔ ドメインの対応）

| ファイル | 対応するオブジェクト | 検証 |
|---|---|---|
| `knowledge/brands.yaml` | `BrandRegistry.from_dict` | slug の妥当性・一意性。台帳と `knowledge/brands/<slug>/` の**双方向一致**（片方だけの存在を検出） |
| `knowledge/.active-brand` | `BrandRegistry.active` | 台帳の `active:` と一致（食い違うとセッションを跨ぐ引き継ぎでブランドを取り違える） |
| `knowledge/brands/<slug>/strategy/kpi-tree.yaml` | `KpiTree.from_dict` | 有料指標を持たない。`root:` で包む形とノード直書きの両方を受ける |
| `knowledge/brands/<slug>/strategy/campaigns/*.yaml` | `Campaign` の一部 | `goal_kpi` がその区画の KPIツリーに実在。`channels` が有料媒体でない |

```yaml
# knowledge/brands/<slug>/strategy/kpi-tree.yaml — KpiTree.to_dict() と同じ形
root:
  name: 指名検索のシェア     # 北極星（遅行）
  kind: 遅行                # 先行 | 遅行
  children:
    - name: オーガニック流入
      kind: 先行
      children: []
```

```yaml
# knowledge/brands/<slug>/strategy/campaigns/<name>.yaml — 検証されるキーは2つだけ
goal_kpi: オーガニック流入   # KPIツリーに実在するノード名
channels: [X, 自社ブログ]    # 文字列 or {name, kind}。有料媒体は不可
# 以下は自由記述（検証しない）: schedule / modalities / owner / notes …
```

**寛容さの方針**: 実運用の YAML は自由記述を含む。**認識できるキーだけを検証し、知らないキーでは落とさない。**
逆に、認識したうえで不変条件に反するものは必ず落とす。
`scripts/lint.py` はワークスペースに `knowledge/brands/**` があればこのドメインモデルで妥当性検証する。
