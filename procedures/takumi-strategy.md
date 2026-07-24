# /戦略 — 上流（戦略）ループ（takumi-strategy）

匠の∞ループの**上流**。アクティブブランドに統合的な施策戦略を立て、下流（実行）へ「計画」を流す。担い手は軍師 **cmo-strategist**。**ゼロ広告費のコンテンツドリブン**が絶対の制約。

> **前段**: アクティブブランドを確定する（未確定なら /ブランド）。以後の書き込みは `knowledge/brands/<slug>/strategy/` にスコープされる（Brand Isolation Guard 対象）。

## サイクル（リサーチ → 仮説 → 戦略 → 計画 → 改善）

1. **インプット収集**: `knowledge/brands/<slug>/brand.yaml`（プロフィール・ポジショニング・ICP・ブランドガイド）、既存の競合/市場リサーチ（無ければ /リサーチ を先に回す提案）、**下流から返った計測**（`knowledge/brands/<slug>/…/analytics` や outcome-verifier 集計があれば取り込む＝∞の上り）。
2. **立案の委譲**: cmo-strategist に委譲する。委譲プロンプトには上記インプットの**絶対パス**を明記（相対は synced 環境で不達）。Agent ツールが無い環境ではメインループが agents/cmo-strategist.md を Read して自ら作法に従い立案し、その旨を1行記録（conventions §4）。
3. **成果物の永続化**（アクティブ区画内でのみ）:
   - `knowledge/brands/<slug>/strategy/strategy.md` … 3C・ポジショニング・ロードマップ
   - `knowledge/brands/<slug>/strategy/kpi-tree.yaml` … KPIツリー（**有料指標を持たない**＝ゼロ広告費の不変条件。ドメインは docs/domain-model.md の KpiTree。`scripts/lint.py` が検証）
   - `knowledge/brands/<slug>/strategy/roadmap.md` … 施策ロードマップ（集客/ブランディングを分け、7割計画）
4. **壁打ち**: strategy-advisor に持ち込み VERDICT（GO / GO-WITH-CHANGES / RETHINK）を得て確定する（長く効く判断のため必須）。
5. **戦略ドシエの出力**: docs/conventions.md 準拠の HTMLレポート（report-template 骨格）で戦略ドシエを生成し届ける（アーティファクト発行→不可ならファイル→保存パス明示）。deliverable-writer に委譲。
6. **計画を下流へ流す（∞の下り）**: ロードマップから最初の打ち手を **/キャンペーン**（複数媒体の統括）または **/カスタマイズ**（定常タスク登録）へ接続する。

## KPIツリーの組み方（ゼロ広告費）

- 北極星（遅行）例: 指名検索数 / オーガニックCV / ブランド想起。ドライバー（先行）例: オーガニック流入・エンゲージ率・保存率・被リンク・回遊。
- **禁止ノード**: CAC / LTV / ROAS / CPA / 広告費 / 出稿 等（有料指標）。置くと lint が落ちる。

## 執筆リファレンス

logical-writing（戦略提案の論理）/ seo-jp（検索起点の設計）/ cro-jp（転換の仮説）/ psych-nudge-jp（訴求フレーム）/ content-design（コンテンツ設計）を必要に応じて参照。
