# /戦略 — 上流（戦略）ループ（takumi-strategy）

匠の∞ループの**上流**。アクティブブランドに統合的な施策戦略を立て、下流（実行）へ「計画」を流す。担い手は軍師 **cmo-strategist**。**ゼロ広告費のコンテンツドリブン**が絶対の制約。

> **前段**: アクティブブランドを確定する（未確定なら /ブランド）。以後の書き込みは `knowledge/brands/<slug>/strategy/` にスコープされる（Brand Isolation Guard 対象）。

## サイクル（リサーチ → 仮説 → 戦略 → 計画 → 改善）

1. **インプット収集**: `knowledge/brands/<slug>/brand.yaml`（プロフィール・ポジショニング・ICP・ブランドガイド）、**顧客の声**（`knowledge/brands/<slug>/knowledge/voc/`。無ければ **/顧客の声** を先に回す提案 — **顧客の言葉が無いままのポジショニングは推測**であり、そのことを立案の冒頭で明示する）、既存の競合/市場リサーチ（無ければ /リサーチ を先に回す提案）、**下流から返った計測**（`knowledge/brands/<slug>/analytics/` や outcome-verifier 集計があれば取り込む＝∞の上り。計測が無い・古い場合は **/計測**（procedures/takumi-analytics.md）で取りに行ってから立案する）。
2. **立案の委譲**: cmo-strategist に委譲する。委譲プロンプトには上記インプットの**絶対パス**を明記（相対は synced 環境で不達）。Agent ツールが無い環境ではメインループが agents/cmo-strategist.md を Read して自ら作法に従い立案し、その旨を1行記録（conventions §4）。
3. **成果物の永続化**（アクティブ区画内でのみ）:
   - `knowledge/brands/<slug>/strategy/strategy.md` … 3C・ポジショニング・ロードマップ
   - `knowledge/brands/<slug>/strategy/kpi-tree.yaml` … KPIツリー（**有料指標を持たない**＝ゼロ広告費の不変条件）。**形は docs/domain-model.md「ワークスペース検証」が正本** — `root:` の下に `name` / `kind`（先行 | 遅行）/ `children` を再帰させる。`python3 <プラグインルート>/scripts/lint.py --workspace .` で機械検証できる
   - `knowledge/brands/<slug>/strategy/roadmap.md` … 施策ロードマップ（集客/ブランディングを分け、7割計画）
4. **壁打ち**: strategy-advisor に持ち込み VERDICT（GO / GO-WITH-CHANGES / RETHINK）を得て確定する（長く効く判断のため必須）。
5. **戦略ドシエの出力**: docs/conventions.md 準拠の HTMLレポート（report-template 骨格）で戦略ドシエを生成し届ける（アーティファクト発行→不可ならファイル→保存パス明示）。deliverable-writer に委譲。
6. **計画を下流へ流す（∞の下り）**: ロードマップから最初の打ち手を **/キャンペーン**（複数媒体の統括）または **/カスタマイズ**（定常タスク登録）へ接続する。

## KPIツリーの組み方（ゼロ広告費）

**設計の正本は `skills/kpi-design-jp`。** ツリーを組む前に必ず読む。要点だけ再掲する:

- **目標 → 兆候 → 指標の順**に決める。取れるデータから KPI を決めない
- 北極星は**1つだけ**。「短期に測れて、長期を予測する」ものに限る。例: **指名検索のシェア（シェア・オブ・サーチ）**
- ドライバー（先行）例: オーガニック流入の構成比・読了率・モダリティ被覆率・表示回数と掲載順位・セッションのキーイベント率
- **葉は必ず実行できる手順書に紐づける。** 親子には「これが上がればあれが上がる」理由を1文で持つ
- **ガードレール指標を別に置く**（量を追うなら質、獲得を追うなら維持）。ガードレールは目標にしない
- **絶対値ではなく比率で持つ**（GA4 は推定値・しきい値で行が消える・referrer は落ちる）
- **禁止ノード**: CAC / LTV / ROAS / CPA / 広告費 / 出稿 等（有料指標）。置くと `KpiNode` が `ValueError`、lint も落ちる
- **ノードの新設は `docs/parts/pre-setup-council.md` の合議を通す**（定義を後から変えると過去と比較できない）

## 執筆リファレンス

kpi-design-jp（指標設計の正本）/ logical-writing（戦略提案の論理）/ seo-jp（検索起点の設計）/ cro-jp（転換の仮説）/ psych-nudge-jp（訴求フレーム）/ content-design（コンテンツ設計）を必要に応じて参照。
