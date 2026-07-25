# /戦略 — 上流（戦略）ループ（takumi-strategy）

匠の∞ループの**上流**。アクティブブランドに統合的な施策戦略を立て、下流（実行）へ「計画」を流す。担い手は軍師 **cmo-strategist**。**ゼロ広告費のコンテンツドリブン**が絶対の制約。

> **前段**: アクティブブランドを確定する（未確定なら /ブランド）。以後の書き込みは `knowledge/brands/<slug>/strategy/` にスコープされる（Brand Isolation Guard 対象）。

## サイクル（リサーチ → 仮説 → 戦略 → 計画 → 改善）

1. **インプット収集**: `knowledge/brands/<slug>/brand.yaml`（プロフィール・ポジショニング・ICP・ブランドガイド）、**顧客の声**（`knowledge/brands/<slug>/knowledge/voc/`。無ければ **/顧客の声** を先に回す提案 — **顧客の言葉が無いままのポジショニングは推測**であり、そのことを立案の冒頭で明示する）、既存の競合/市場リサーチ（無ければ /リサーチ を先に回す提案）、**下流から返った計測**（`knowledge/brands/<slug>/analytics/` や outcome-verifier 集計があれば取り込む＝∞の上り。計測が無い・古い場合は **/計測**（procedures/takumi-analytics.md）で取りに行ってから立案する）。
1b. **基礎分析の確認**: `knowledge/brands/<slug>/knowledge/analysis/` に基礎分析があるか見る。無い・古いなら **`docs/parts/foundation-analysis.md`（/リサーチ）を先に回す**。**特に③（ビジネスモデルとキャッシュフロー）が無いまま施策の立案に進まない** — 構造的に儲からないモデルに集客を足せば赤字が速く増え、CCC が正の事業で成長計画を立てれば**成功したときに資金が尽きる**（→ `skills/business-model-jp`）。
2. **立案の委譲**: cmo-strategist に委譲する。委譲プロンプトには上記インプットの**絶対パス**を明記（相対は synced 環境で不達）。Agent ツールが無い環境ではメインループが agents/cmo-strategist.md を Read して自ら作法に従い立案し、その旨を1行記録（conventions §4）。
2b. **勝ち筋の確定（最上流）**: `skills/winning-position-jp` に従い「**なぜ我々が勝てるのか**」を一文で確定する。広告費が効きにくい場所を選び、**非対称な強み**（競合が真似するには何かを失うもの）を特定し、**やらないこと**を決める。**ここが KPIツリーとメッセージングの上流** — 勝ち筋が無いまま指標と主張を作らない。
2c. **オファーの設計（勝ち筋の直下）**: `skills/offer-design-jp` に従い「**来ている人に何を差し出しているか**」を1枚にする。**集客を増やす話より先にここを見る** — 流入を増やすのは難しいが、オファーを変えれば**今の流入のまま**成果が変わる。順番は ①摩擦を減らす → ②束を組み直す → ③入口を作る → ④リスクを引き取る → **⑤値付けは最後**。**値付けから始めると値下げ競争に落ちる**（値下げは誰でも真似でき、非対称ではない）。
3. **成果物の永続化**（アクティブ区画内でのみ）:
   - `knowledge/brands/<slug>/strategy/strategy.md` … 3C・ポジショニング・ロードマップ
   - `knowledge/brands/<slug>/strategy/kpi-tree.yaml` … KPIツリー（**有料指標を持たない**＝ゼロ広告費の不変条件）。**形は docs/domain-model.md「ワークスペース検証」が正本** — `root:` の下に `name` / `kind`（先行 | 遅行）/ `children` を再帰させる。`python3 <プラグインルート>/scripts/lint.py --workspace .` で機械検証できる
   - `knowledge/brands/<slug>/strategy/winning-position.md` … **勝ち筋**（戦う場所・勝てる理由・カテゴリの括り・積み上げる資産・やらないこと・**外れたと分かる条件**）。正本は `skills/winning-position-jp`
   - `knowledge/brands/<slug>/strategy/messaging.md` … **メッセージングハウス**（ポジショニング1文 + 言い続ける柱1〜3 + 各柱の証拠 + 言わないこと）。**作法の正本は `skills/messaging-design-jp`。** 面を張るには張るべき主張が要る — 媒体ごとに違うことを言えば包囲網は点の集合に戻る。柱は**最大3つ**、各柱に**検証可能な証拠**を持たせ、証拠が用意できない柱は降ろす
   - `knowledge/brands/<slug>/strategy/offer.md` … **オファー**（得られる結果・含まれるもの・価格と支払い方・必要な条件・申込の手間・やめるときどうなるか・**断る理由になっているもの**）。正本は `skills/offer-design-jp`。最後の1行は推測で埋めず **/顧客の声** で確かめる
   - `knowledge/brands/<slug>/strategy/demand-calendar.md` … **需要カレンダー**（暦の山・業界の山・逆算した着手日・取りにいかない山）。正本は `skills/demand-timing-jp`。**祝日を固定日で書かない**（春分・秋分は年で動く）
   - `knowledge/brands/<slug>/strategy/roadmap.md` … 施策ロードマップ（集客/ブランディングを分け、**7割計画**）。**7割計画は数字にする** — 各施策に見積時間とドライバー（KPIノード）を持たせ、`docs/parts/capacity-plan.md` で埋まり具合（計画合計 ÷ 実働×0.7）を出す。**100%を超えたら足す前に落とす**
4. **壁打ち（守りと攻めの両方・1ターンで並列委譲）**:
   - **strategy-advisor** … VERDICT（GO / GO-WITH-CHANGES / RETHINK）。**破綻していないか**
   - **growth-challenger** … CHALLENGE（SHARPEN / PARTIAL / BOLD-ENOUGH）。**無難すぎないか**
   **どちらか片方だけで確定しない。** 守りだけを回すと、減点されないが誰の記憶にも残らない計画に収束する。両者が衝突したら、ユーザーに**どちらの側に倒すか**を選ばせる（AI が勝手に無難な方へ倒さない）。
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

kpi-design-jp（指標設計の正本）/ **offer-design-jp（オファー設計 — 何を差し出すか。集客より先に見る）** / **demand-timing-jp（需要の山 — いつ出すか）** / logical-writing（戦略提案の論理）/ seo-jp（検索起点の設計）/ cro-jp（転換の仮説）/ psych-nudge-jp（訴求フレーム）/ content-design（コンテンツ設計）を必要に応じて参照。
