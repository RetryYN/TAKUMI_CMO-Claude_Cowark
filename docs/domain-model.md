# ドメインモデル（正本）— オブジェクト型 DDD

TAKUMI-CMO のドメインを集約・エンティティ・値オブジェクトで表す。**日本語のユビキタス言語**を一次言語とし、
コード（`takumi/domain/`）の英語クラス名はここと1対1で対応させる。手順書・コマンドはこの言葉で書く。

## ユビキタス言語 ↔ コードの対応

| 日本語（ユビキタス） | コード（英語） | 種別 | 意味 |
|---|---|---|---|
| ブランド | `Brand` | 集約ルート | 無双させる単位。すべての施策・記憶が1ブランドに閉じる |
| ブランドslug | `BrandSlug` | 値オブジェクト | ブランドの不変な識別子（`knowledge/brands/<slug>/` の名前） |
| ブランド台帳 | `BrandRegistry` | 集約 | 全ブランドの集合＋アクティブブランドの指し先 |
| ブランド区画 | `BrandPartition` | 値オブジェクト | `knowledge/brands/<slug>/` 配下。他区画から隔離される |
| 戦略 | `Strategy` | エンティティ | 3C・ポジショニング・施策ロードマップ（上流ループの産物） |
| KPIツリー | `KpiTree` | 集約 | 先行/遅行指標の階層。上流下流が共有する背骨。オーガニック指標のみ（有料広告のCAC/LTVは持たない） |
| キャンペーン | `Campaign` | エンティティ | 複数媒体を1つの目標の下に束ねる統括単位（下流のオーケストレーション） |
| 上流ループ | `UpstreamLoop` | ドメインサービス | 戦略ループ（リサーチ→仮説→戦略→計画→改善・トップダウン） |
| 下流ループ | `DownstreamLoop` | ドメインサービス | 実行ループ（計画→リサーチ→企画→実行→計測→改善・ボトムアップ） |
| タスク | `Task` | エンティティ | 単一の仕事。動詞型: 計画/リサーチ/収集/クリエイティブ/分析/掃き出し |
| 媒体 | `Channel` | 値オブジェクト | オーガニック媒体（SNS/コンテンツ/Webサイト/オウンドメディア/メール）。有料出稿媒体は持たない |
| ゲート | `Gate` | ドメインサービス（hook） | 不変条件の機械強制（Brand Isolation / ゼロ課金 / 送出監査 等） |

## 匠の∞ループ（中核のドメインサービス）

上流ループ `UpstreamLoop`（戦略）と下流ループ `DownstreamLoop`（実行）が **計画** と **計測** で結ばれた ∞ 字。

- 交差点の受け渡し: 下り = **計画**（`Strategy` → `Campaign` の実行ブリーフ）／上り = **計測・改善**（`DownstreamLoop` の実測 → `KpiTree` 更新 → 再 `Strategy`）。
- 両ループが共有する背骨 = `KpiTree`。戦略も実行も「改善」を持つ＝匠の技で磨き続ける。

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

| 対象 | 状態 | テスト |
|---|---|---|
| `BrandSlug` / `Brand` / `BrandRegistry` / `BrandPartition` | 土台フェーズで実装 | `tests/test_brand.py` |
| `KpiTree` | Phase 3 | `tests/test_kpi_tree.py` |
| `Strategy` / `Campaign` | Phase 3 | `tests/test_strategy.py` / `tests/test_campaign.py` |
| `Loop`（上流/下流の受け渡し規則） | Phase 4 | `tests/test_loop.py` |

各対象は「テストを先に書いて red → 実装 → green」（[開発ワークフロー.md](開発ワークフロー.md) §2）。
`scripts/lint.py` はワークスペースに `knowledge/brands/**` があればこのドメインモデルで妥当性検証する。
