# /ブランド — マルチブランドの登録・切替・一覧・アーカイブ（takumi-brand）

TAKUMI-CMO は1インストールで**複数ブランド**を無双させる。各ブランドの記憶は `knowledge/brands/<slug>/` に**区画分離**され、戦略・KPI・媒体状態・ナレッジ・ログが1ブランドに閉じる。ドメインモデルの正本は docs/domain-model.md（Brand 集約）。

> **アクティブブランドは全変更操作の前段**。変更系タスクはまずアクティブブランドを確定してから走る（未確定なら **Brand Isolation Guard** が区画書き込みを止める）。別ブランド区画への書き込み＝相互汚染は機械遮断される。

## 台帳とポインタ（正本）

- `knowledge/brands.yaml` … ブランド台帳（全ブランドの集合＋アクティブ）
- `memory/.workflow/active_brand` … アクティブブランドの slug（hook が読む。切替時に必ず更新）
- `knowledge/.active-brand` … アクティブの永続コピー（セッションを跨ぐ引き継ぎ用）

```yaml
# knowledge/brands.yaml
active: acme
brands:
  - slug: acme          # ^[a-z0-9][a-z0-9-]*$ ・2〜40字・台帳内で一意
    name: Acme Inc
    status: active       # active | archived
    created: 2026-07-25
```

## 操作の振り分け（要望から判定）

### 1. 登録（「ブランドを追加」「新規ブランド」）
1. ブランド名を聞く（未指定なら質問）。slug を提案（英小文字化・空白→ハイフン）。**不変条件**: `^[a-z0-9][a-z0-9-]*$`・2〜40字・先頭末尾ハイフン不可・`knowledge/brands.yaml` 内で一意。重複・不正なら理由を示して再提案。
2. `knowledge/brands.yaml` に1エントリ追記（無ければヘッダごと作成）。
3. **区画スケルトンを作成**（アクティブ確定後に、アクティブ区画内でのみ — Brand Isolation Guard 対象）: `knowledge/brands/<slug>/` 配下に `brand.yaml`（プロフィール雛形）・`strategy/`・`channels/`・`knowledge/`・`queue/`・`logs/`・`drafts/`・`approvals/`・`assets/`。
4. 登録直後は**そのブランドをアクティブにする**（下記「切替」を実行）。「このブランドで /セットアップ しますか？」を案内。

### 2. 切替（「A に切り替えて」「A で作業」）
1. slug が `knowledge/brands.yaml` に存在し `archived` でないことを確認（無ければ一覧を出して選ばせる）。
2. `memory/.workflow/active_brand` に slug を書く（`printf '%s' <slug> > memory/.workflow/active_brand`）＋ `knowledge/.active-brand` に同じ値を書く＋ `brands.yaml` の `active:` を更新。
3. 「アクティブブランドを『<name>』に切り替えました」と報告。以後の全タスクはこの区画にスコープされる。

### 3. 一覧（「ブランド一覧」「どんなブランドがある？」）
- `knowledge/brands.yaml` を読み、表（slug / 名称 / 状態 / アクティブ印）で提示。ポートフォリオ視点の要約（/レポート のポートフォリオ表示へ誘導）。

### 4. 現在（「今どのブランド？」）
- `memory/.workflow/active_brand`（無ければ `knowledge/.active-brand`）を読んで報告。未確定なら「まずブランドを登録/切替してください」と案内。

### 5. アーカイブ（「A をアーカイブ」「A は一旦停止」）
- `brands.yaml` の当該 `status:` を `archived` に更新。**削除はしない**（区画＝資産は残す）。アクティブだった場合はアクティブを解除し、別ブランドへの切替を促す。

## 注意

- 区画スケルトン作成・brand.yaml 書き込みは、**アクティブ確定後にアクティブ区画内でのみ**行う（Brand Isolation Guard が別区画書き込みを deny する）。
- 未接続（フォルダ未追加）だと `knowledge/` はセッション終了で消える → 継続運用は「フォルダを追加」を案内（README）。
- ブランド台帳の妥当性は `scripts/lint.py` がワークスペースに `knowledge/brands/**` があるとき Brand 集約（takumi/domain）で検証する。
