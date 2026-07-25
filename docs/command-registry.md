# 台帳（Registry）── 4層アーキテクチャの正本

**このファイルがコマンド・部品・定常ループの一覧の正本。** 追加・改名・削除は必ずここを同時に更新する。
`/検証` はこの台帳と `commands/`・`procedures/`・`docs/parts/`・`skills/` の実体の突合を検証項目に含める。

## 世界観 — 匠の∞（無限）ループ（2026-07-25 ユーザー決定でリブランド）

匠CMO は **上流（戦略）ループ**と**下流（実行）ループ**を、**計画**（下りブリーフ）と**計測**（上りの実測KPI）で結んだ ∞ 字の学習系。戦略も実行も匠の技で磨き続ける。1インストールで**複数ブランド**を扱い、メモリはブランドごとに分離する（`knowledge/brands/<brand>/`）。そして金は1円も使わない — **ゼロ広告費のコンテンツドリブン**で集客とブランディングを成立させる（有料出稿・課金は URL Guard / Money Watch が機械的に遮断＝ゼロ課金の保証）。

| ループ | 向き | サイクル | 担い手 | ∞ の受け渡し |
|---|---|---|---|---|
| **上流ループ（戦略）** | トップダウン | リサーチ→仮説→戦略→計画→改善 | cmo-strategist（軍師）/ 戦略・キャンペーンのパック | 下流へ **計画** を流す |
| **下流ループ（実行）** | ボトムアップ | 計画→リサーチ→企画→実行→計測→改善 | 実行パック / A〜K ワークフロー / フェーズ①〜④ / 職人エージェント（writer・artisan・critic）/ 監査（pre-send・outcome） | 上流へ **計測・改善** を返す |

両ループが共有する背骨は **KPIツリー**（`knowledge/brands/<brand>/strategy/`）。∞ の交差点で、下りは *計画*（戦略→実行ブリーフ）、上りは *計測・改善*（実測KPI＋学び→再戦略）が受け渡される。旧「Delvework（掘る）／Forgecraft（鍛える）」は廃止語ではなく、**下流ループの内部動作**（探索・収集＝掘る／実証基準での成果物化＝鍛える）として意味を保つ。

## 能力モデル — 匠の三徳「心・技・体」（2026-07-25 ユーザー決定）

∞ループが**回し方**の設計なら、三徳は**何を磨くか**の設計。前提は「マーケティングのプロは**仮説づくり**のプロである」— データは「何が起きたか」しか語らず背景を読み解かないため、リサーチで背景を掘って推論する能力が本体である。

| 徳 | 定義 | 実装（この徳を担う実体） |
|---|---|---|
| **心** | ユーザー行動を心理学から読み解き、市場を開拓する。手法は**心理プロファイリング**（意思決定スタイル・不安・関係段階の3軸判定）と**CBT の認知の歪み**（全か無か／破局視／べき思考を特定し、購買・応募のブレーキを文面で外す） | `skills/psych-target-jp`（プロファイリング3軸判定表・CBT応用・倫理境界）/ `psych-nudge-jp`（訴求フレーム選択・禁忌表・EAST自己審査）/ `psych-ux-jp`（視線・情報密度・配色・EFOの心理根拠）/ `takumi-research`（背景の掘り起こし）。**倫理境界**: 心理学は不安の解消に使い増幅（恐怖訴求・偽の希少性）は禁止（session-rules (3)）／読み手を「診断」する物言いをせずプロファイルは書き手側の内部判断に留める／判定基準は「事実を分かりやすく伝えた結果か、事実を歪めて作った感情か」／送信前は pre-send-verifier がこの基準への適合も監査する |
| **技** | ユーザーにも AI にも届く形に磨き上げ、伝わることを実現する。*ユーザーに届く*＝**品質**／*AI に届く*＝**面**（マルチメディアの包囲網） | **品質**: `skills/seo-jp`（検索意図）/ `cro-jp`（転換率）/ `design-evidence-jp`（可読性・コントラスト等の実証基準）/ `web-design` / 執筆スキル群 ＋ **design-artisan → design-critic の審査ループ**（Critic Gate が PASS 前の引き渡しを機械遮断）。**面**: テキスト（`takumi-ownedmedia`）× 画像・動画（`takumi-content` ＋ `docs/parts/imagegen`・`image-edit`・`video-content-script`、`templates/banner-compose.py`・`chromakey.py`・`guide-anim.py`）× SNS 7媒体（`takumi-sns`）を横断し、**`takumi-campaign` が複数媒体を1目標で束ねて包囲網を形成する** |
| **体** | データを取り、仮説を裏付け、AI の実行力で加速する。**指標を読むだけでなく計測基盤そのものを組む** | A〜K ワークフロー（実ブラウザでの計測・公開・変更前記録）/ `knowledge/data/takumi.db`（計測DB）/ `outcome-verifier`（証跡のある確定数だけを成果に数える）/ `knowledge/sites/`（攻略済みサイトの地図）／**計測基盤の構築＝ `takumi-analytics`（/計測）が入口**: `skills/gtm-jp`（タグ・トリガー・変数・データレイヤーの設定／SNS からの CV 計測）・`ga4-jp`（キーイベント・カスタムディメンション・探索・アトリビューション）・`search-console-jp`（AI検索での露出を一次情報で取得）。GTM の公開は人間承認（ロールバック可）、カスタムHTMLタグは AI 自律禁止。**指標の定義そのものを新設するときだけ** `docs/parts/pre-setup-council.md`（合議＝関所。顔ぶれは案件で選ぶ） |

**三徳をつなぐのがデータ**: 心が立てた仮説を技が形にし、体が実測する。実測は KPIツリー（∞の上り）へ返り、次の仮説の材料になる。データは目的ではなく三徳をつなぐ血流であり、**KPIツリーが三徳と∞ループの共通の背骨**になる。

**「AI に届く」の定義（2026-07-25 ユーザー決定）**: AI 向けの小手先の最適化ではなく、**マルチメディア領域での包囲網の形成**を指す。テキスト1本は点にすぎず、記事・SNS投稿・画像・動画を横断して同じ主張を立ち上げることで面になる。複数のモダリティと露出面から反復して現れるものを、AI は認知し推奨する。ゆえに「技」は品質（1本を磨く）と面（横断して張る）の二面を持ち、後者の司令塔が `takumi-campaign` である。

> 未実装（次フェーズ候補）: 包囲網の**効果測定** — AI 検索での言及・引用を観測して KPIツリーへ返す仕組み。形成する側（マルチメディア横断の制作・配信）は実装済みだが、AI にどう届いたかを測る手段がまだない。

## 構造の芯 — 4層アーキテクチャ（2026-07-23 ユーザー決定で確定）

| 層 | 概念 | 実体 |
|---|---|---|
| **コマンド** | カテゴリーレベル（媒体・対象のタスクパック）。要望は引数に自由に書かせる | `commands/`（登録13本・日本語名）+ `procedures/takumi-*.md`（内部手順含め30本） |
| **ワークフロー** | 進め方 = タスクの連なり。A〜K 実行チェーン + タスク5型の連結 | `docs/steps-reference.md` + hooks のゲート + フェーズ①〜④ |
| **タスク** | 単一の仕事。動詞レベル: **リサーチ / 収集 / クリエイティブ / 分析 / 掃き出し** | `tasks/*.yaml`（/カスタマイズ のタスク登録 = takumi-task が生成）+ `docs/parts/`（部品） |
| **サブエージェント** | 専門作業の職人。タスクから呼ばれる | `agents/`（9体: writer / artisan / critic / advisor / pre-send-verifier / outcome-verifier / **cmo-strategist**（上流ループの立案）/ **risk-forecaster**（設定前のトラブル予測。構造から破綻を特定）/ **privacy-auditor**（PII・同意の監査）） |

**実行粒度の3段**（全パック共通）: ①タスク単体で完結 ②ワークフローで解決（タスク連結） ③まるっと（パックの定常ループ一式）。振り分け原則は `docs/parts/index.md`。

**最上位スコープ = ブランド（2026-07-25 追加）**: 4層エンジンは常に**アクティブブランド**の区画（`knowledge/brands/<brand>/`）の中で回る。全タスクの前段でアクティブブランドを確定し（`/ブランド` または自然文で切替）、変更操作は **Brand Isolation Guard** がアクティブブランド区画のみに限定する（別ブランド区画への書き込み＝遮断。複数ブランド運用の相互汚染を機械強制で防ぐ）。この4層エンジンは **∞ループの下流（実行）** を担い、その上に **上流（戦略）** ＝ cmo-strategist と 戦略・キャンペーンのパックが載る（→ §世界観）。**上流→下流の受け渡し＝計画、下流→上流＝計測・改善**。

新しい媒体を増やす＝パック1個追加。できることを増やす＝部品（docs/parts/）の追加。**エンジン側（ワークフロー層）は一切変えない。**

**動的パック**: 媒体の個別コマンド（例: /note /ペライチ）は **/ワーク追加** で生成する — 登録 + 初期マッピング（フェーズ①・読み取り専用）+ ワークスペース `.claude/commands/` への専用コマンド生成を1コマンドで実行（プラグイン本体は増やさない）。**/セットアップ の媒体選択でも自動生成**する — SNS=`/<媒体名>運用`（/X運用 等）。以後の単一媒体依頼は専用コマンドが第一入口（/SNS運用 は複数媒体・媒体不明時の受け皿）。**有料広告媒体の動的パック（旧 /<媒体名>広告）は廃止**（ゼロ広告費）。**求人媒体パックも廃止**（オウンドメディア＝自社ブログに置換）。**既存パックに該当しない完全別ワークは非表示の親「その他ワーク」の配下**に生成する（親判定表の正本は procedures/takumi-add-work.md §4 — registry.yaml に `parent:` を記録）。

## 命名ルール

1. **登録コマンド（`commands/`）は日本語名が本体** — メニューに並ぶのはこの13本のみ。description には自動発火用の「Use when」を日本語で書く
2. **手順の正本は `procedures/takumi-*.md`（英語ケバブケース、登録対象外）** — 日本語コマンドは薄いラッパー（procedures を Read + Glob フォールバック）。1対1で、片方だけの追加は禁止
3. 部品（docs/parts/）はコマンド登録しない。パックのタスクが Read して使う
4. `/スキル化` が生成するワークスペーススキルも同ルール: name は英語ケバブ、description の発火例は日本語の言い方で書く

## コマンド台帳（登録13本）

| 手順書（procedures/） | コマンド名（登録） | カテゴリー | Pack | 代表的な言い方 |
|---|---|---|---|---|
| takumi-sns | SNS運用 | SNS媒体 | sns | 「Xの投稿作って」「noteを書いて」（媒体不明なら「どの媒体？」を選択式で。setup.yaml の選択媒体のみ提示） |
| takumi-research | リサーチ | 横断 | research | 「競合を分析して」「トレンド調べて」（対象不明なら「どの媒体・対象？」を選択式で） |
| takumi-ownedmedia | オウンドメディア | オウンド | ownedmedia | 「ブログ記事を公開」「WordPress更新」「記事のSEO見直し」（自社ブログ運営。WordPress既定） |
| takumi-add-work | ワーク追加 | 基盤 | core | 「noteを追加して」（登録+初期マッピング+専用コマンド生成） |
| takumi-brand | ブランド | 基盤 | core | 「ブランドを追加」「acme に切り替え」「ブランド一覧」（マルチブランドの登録・切替・一覧・アーカイブ。区画分離） |
| takumi-strategy | 戦略 | 戦略 | strategy | 「戦略立てて」「KPIツリー作って」「3C分析」（上流ループ＝cmo-strategist が立案。ゼロ広告費） |
| takumi-campaign | キャンペーン | 戦略 | strategy | 「キャンペーン組んで」「複数媒体を連動」（複数オーガニック媒体を1目標で統括） |
| takumi-setup | セットアップ | 基盤 | core | 「初期設定」「使う機能を選びたい」（回答保存・済んだ質問は聞かない・未選択パックは発火停止） |
| takumi-analytics | 計測 | 計測 | analytics | 「GA4を設定して」「コンバージョン計測したい」「GTMでイベント飛ばして」「検索順位を見て」「AI検索で引用されてる？」（計測基盤の構築 + データ取得 + KPIツリーへ返す＝∞の上り） |
| takumi-website | Webサイト | オウンド | research | 「表示速度を測って」「このLP改善して」 |
| takumi-email | メール | メール | email | 「メルマガ書いて」「配信リスト整理して」「開封率は？」（配信は不可逆送出＝pre-send-verifier 監査 + 人間承認のゲート下） |
| takumi-content | コンテンツ | オウンド | creative | 「サムネ作って」「記事のアイキャッチ」「このビジュアルからLP」 |
| takumi-customize | カスタマイズ | 基盤 | core | 「毎朝これやって」「これ覚えて」（タスク登録/スキル化/好み記憶/機能ON-OFF を選択式で） |
| takumi-reporting | レポート | 記録 | core | 「今どうなってる？」「今日の作業まとめて」（トップ=ダッシュボード + 作業ログ/運用レポートを選択） |
| takumi-verify | 検証 | 記録 | core | 「プラグインを検証して」※セルフテスト。品質保証機能として同梱（導入直後は quick、更新後・不調時は full） |

**計: 登録コマンド 13 / 内部手順 17 / 手順書 30（procedures/）**

## 内部手順台帳（メニュー非表示 — 自然文・ルール発火で動く。手順書は procedures/ に残す）

| 手順書 | 旧コマンド名 | 発火のさせ方 |
|---|---|---|
| takumi-start | （内部）タスク開始 | 変更操作の前段として各パックが内部で通す関所（session-rules (1)） |
| takumi-sns-x | （内部）X媒体手順 | /SNS運用 が媒体判定後に振り分け |
| takumi-sns-instagram | （内部）Instagram媒体手順 | 同上 |
| takumi-sns-tiktok | （内部）TikTok媒体手順 | 同上 |
| takumi-sns-threads | （内部）Threads媒体手順 | 同上（Meta系: IGログイン連動・予約投稿不可の注意あり） |
| takumi-sns-note | （内部）note媒体手順 | 同上 |
| takumi-sns-youtube | （内部）YouTube媒体手順 | 同上 |
| takumi-sns-line | （内部）LINE媒体手順 | 同上 |
| takumi-task | （内部）定常タスク登録 | /カスタマイズ が振り分け（「毎朝◯◯して」） |
| takumi-dashboard | （内部）ダッシュボード | /レポート のトップとして生成（定常ループの締めもここ） |
| takumi-report | （内部）作業ログ | /レポート が振り分け |
| takumi-status | （内部）状態確認 | 「今どうなってる？」等の自然文（session-rules (8)） |
| takumi-demo | （内部）デモ | 「何ができるの？」→ ダッシュボードの説明書へ誘導 |
| takumi-config | （内部）機能設定 | 「SNS機能を切って」等の自然文 |
| takumi-skillify | （内部）スキル化 | 手順を教わった・同一パターン2回目の自動検知（session-rules (3c)） |
| takumi-feedback | （内部）メモリ保存 | 成果物への評価・修正指示の自動検知（session-rules (3b)） |
| takumi-memory | （内部）メモリ圧縮 | 「ログを整理して」/ session-log 肥大時に提案 |

※ procedures/ を持たない内部手順: **無人運用前チェック**（docs/unattended-ops.md 内 — 「無人運用前チェックして」の自然文、およびブラウザ操作タスクのローカル登録前に takumi-task が必須で通す）

## 部品台帳（docs/parts/ — タスク5型。詳細は docs/parts/index.md が正本）

| タスク型 | 部品 |
|---|---|
| 計画 | content-calendar（カレンダー・送信/配信計画 → queue・定常タスクへ接続） |
| リサーチ | style-research / deep-research / sns-research |
| 収集 | asset-collect / video-asset-collect |
| クリエイティブ | imagegen / videogen / image-edit / video-edit / page-improve / content-to-lp / video-content-script |
| 分析 | site-audit / sns-research（数値読み） |
| 掃き出し | wp-publish（WordPress記事公開）/ design-sync / canva-export / design-handoff（成果物を Claude Design へ送って人間が編集→回収。critic PASS 後に「Design に送って手直ししますか？」） |

SNS 共通運用フローは `docs/sns-ops.md`、メディア技術地図は `docs/media-pipeline.md`、無人運用・承認キュー・クラウド→ローカル移行は `docs/unattended-ops.md`、プラットフォーム上申事項（プラグインで根治不可の課題と緩和策）は `docs/escalations.md` が正本。

## スキル台帳（`skills/` — 規範の正本）

> **配置方針（2026-07-25 変更）**: `skills/` に置く。**旧 `references/` は Cowork のプラグイン仕様上どのコンポーネントにも該当せず**、公式仕様は「skills は `skills/` または `commands/` 配下、あるいはルート直下の単一 `SKILL.md`」と定めている（[plugins-reference](https://code.claude.com/docs/en/plugins-reference)・一次情報）。
>
> 旧方針は「自動発火させない内部教科書」だった。これを覆した理由は **escalations E6** — 永続フォルダ未接続の環境で委譲先エージェントが `references/**` に到達できず、`outside this session's connected folders` で拒否される。規範がまったく適用されないまま design-critic の審査や法規チェックが走る状態は、自動発火を避ける利益より高くつく。
>
> **代償と緩和**: 自動発火するようになるため、業務の入口がコマンドを飛ばしてスキルに逸れる恐れがある。session-rules (3) に「**業務の入口は必ずコマンド／手順書。スキルが先に開いても、変更操作の前に該当手順書へ合流してブランド確定とゲートを通す**」を明記した。実際に逸れないかは Tier 2 の **V50** で実測する。
>
> ワークスペース側で同名スキルが登録されている場合も正本はプラグインの `skills/` とし、更新はこちらに行う（二重管理の乖離防止）。

| リファレンス | 主な使い手 | 用途 |
|---|---|---|
| logical-writing | Webサイト・全パックのレポート | 分析レポート・戦略提案 |
| sns-jp | SNS媒体パック | 日本のSNS文化・ハッシュタグ・投稿時間帯・LINE配信設計 |
| content-design | SNS媒体パック | 投稿コンテンツの設計・カレンダー |
| storytelling | SNS媒体・オウンドメディア | ブランドストーリー・オウンドメディア記事 |
| copywriting | コンテンツ・オウンドメディア・SNS | キャッチコピー・件名13字 |
| video-script | コンテンツ（動画） | 動画コンテンツの構成・台本（オーガニック動画。有料出稿はしない） |
| ad-compliance-jp | コンテンツ・全公開物 | 景表法・ステマ規制・PR表記チェック（オーガニック含む全公開物の表現規制） |
| web-design | Webサイト・広告 | LP/ページのデザイン実装 |
| business-writing | 基盤 | 社内外メール・事務連絡・校正 |
| seo-jp | Webサイト・SNS媒体 | 日本語SEO/AEO — 記事設計・既存ページ診断・AI検索対応 |
| cro-jp | Webサイト・コンテンツ・オウンドメディア | CRO/ABテスト — 転換率改善の仮説設計・文面ABテスト |
| psych-nudge-jp | 全パック（コピー・CTA設計） | 行動経済・ナッジの日本実証 — 訴求フレーム選択（損失/利得/規範/利他）とEASTチェック |
| psych-ux-jp | Webサイト・広告 | UI/UX・社会心理の日本実務 — 視線/密度/配色/フォーム/実績表示の判断基準 |
| psych-target-jp | オウンドメディア・SNS媒体（文面の書き分け） | 読み手の心理プロファイル×CBT健全応用 — 3軸判定（不安の核/意思決定スタイル/関係段階） |
| design-evidence-jp | Webサイト・広告・全HTML成果物 | 実証デザイン数値基準 — タイポ/配色/LPレイアウト/グラフ選択の具体値（DADS・JIS・WACUL・NN/g・Cleveland-McGill） |
| sales-writing | 基盤 | 受注目的の提案書・テレアポ |
| kpi-design-jp | 戦略・レポート・全パック（指標設計） | 何を測るかの設計 — 目標→兆候→指標の順序、北極星とOEC、先行/遅行、ガードレール指標、グッドハートの法則、シェア・オブ・サーチ、虚栄の指標の見分け方、指標定義書、KPIツリーの組み方 |
| gtm-jp | **計測**（/計測） | GTM の設定 — トリガー全種と発火順序、組み込み/ユーザー定義変数、データレイヤー、GA4 イベントタグ、SNS からの CV 計測、プレビュー、バージョンとロールバック、カスタムHTML禁止と `gtm.blocklist` |
| ga4-jp | **計測**（/計測）・戦略 | GA4 の設定と分析 — 拡張計測機能、キーイベント、カスタムディメンション（上限・24〜48h・カーディナリティ）、チャネルグループ、DebugView、探索7手法、アトリビューション、データのしきい値、PII禁止、データ保持は触らない |
| search-console-jp | **計測**（/計測）・オウンドメディア・戦略 | GSC / Bing WMT のブラウザ操作 — 生成AIパフォーマンスレポート（AI Overviews・AI Mode・Copilot引用）の取得、削除ツール禁止 |

## 定常ループ台帳（標準セット。実運用の正本はワークスペースの `knowledge/config/loops.yaml` — /カスタマイズ のタスク登録が管理）

| カテゴリー | ループ | 標準周期 | 使うコマンド | 締め |
|---|---|---|---|---|
| オウンド | 自社サイト診断 | 週次（月曜） | Webサイト | ダッシュボード更新 |
| SNS媒体 | 予約投稿・実績記録 | 毎朝 | SNS運用 | 同上 |
| SNS媒体 | ストック補充 | 週次 or 残量アラート時 | SNS運用 | 同上 |
| SNS媒体 | カレンダー消化率チェック・翌週計画 | 週次（金曜） | SNS運用（content-calendar 部品） | 同上 |
| オウンド | ブログ更新巡回・記事公開 | 週次 or 記事完成時 | オウンドメディア（+ タスク開始） | 同上 |
| コンテンツ | コンテンツ制作・競合コンテンツ調査 | 依頼時（定常化も可） | コンテンツ | 同上 |

**原則1: 実行系（変更操作）は全カテゴリー共通で `takumi-start` が担う**（A〜Kワークフロー + 変更前記録/承認の関所）。パック別の実行コマンドは新設しない。

**原則2: 各ループの締めに `takumi-dashboard` を実行**し、司令塔を常に最新へ。

**原則3: 最適化（フェーズ④）は標準の裏側動作** — マッピングとタスク順序を記録し、成功の繰り返しで最短ルート整備・スクリプト化を自動で提案する（バックグラウンドエージェントへの委譲可）。ユーザーが頼まなくても走る。

**原則4: ブランド区画スコープ** — 全パックの読み書きはアクティブブランドの区画 `knowledge/brands/<slug>/` に閉じる（上のフォルダ対応表が正本）。単一ブランド運用でも1つ登録して区画に閉じる。別ブランド区画への書き込みは Brand Isolation Guard が遮断し、相互汚染を防ぐ。

**原則5: ∞ループの自律フィードバック** — 下流（実行）の計測は outcome-verifier が集計し、`knowledge/brands/<slug>/analytics/` と KPIツリー（`strategy/kpi-tree.yaml`）の進捗へ反映する。KPIツリーが動いた/動かないは次の /戦略（上流）の再立案インプットになる（∞の上り）。ユーザーが頼まなくても、ループの締め（原則2 のダッシュボード）で「計測→KPI反映」を実行する — 戦略も実行も匠の技で磨き続ける。

## カテゴリー → knowledge/ フォルダ対応（ブランド区画スコープ）

**ブランド固有の記憶はすべてアクティブブランドの区画 `knowledge/brands/<slug>/` 配下に置く**（`<slug>` = アクティブブランド。Brand Isolation Guard が別区画書き込みを遮断）。横断（全ブランド共通）だけがトップレベルに残る。これにより1ブランドの戦略・媒体・計測が**1つの物語で統合**される。

**パス解決の正本（全手順共通）**: 手順書に `knowledge/sns/` 等の短縮形が書かれていても、**ブランド固有の記憶は必ずアクティブブランド区画 `knowledge/brands/<slug>/` 配下へ解決する**（この対応表が正本。conventions §1 のプラグイン内パス解決規則と同じ位置づけ）。

| カテゴリー | 主な保存先（`<slug>` = アクティブブランド） |
|---|---|
| 戦略（上流） | `knowledge/brands/<slug>/strategy/`（strategy.md・kpi-tree.yaml・roadmap.md・campaigns/） |
| SNS媒体 | `knowledge/brands/<slug>/channels/sns/<platform>/`（ネタ帳 queue.md・調査 research/） |
| コンテンツ（オウンド） | `knowledge/brands/<slug>/channels/content/`・styles/・mockups/・assets/・drafts/ |
| Webサイト（オウンド） | `knowledge/brands/<slug>/channels/website/`・audits/・sites/ |
| オウンドメディア | `knowledge/brands/<slug>/channels/ownedmedia/`・drafts/ |
| ブランド固有の記録 | `knowledge/brands/<slug>/logs/`・reports/・analytics/・feedback/・queue/・tacit/ |
| 横断（全ブランド共通） | `knowledge/brands.yaml`・`.active-brand` / `knowledge/config/`（allowlist等）/ `knowledge/verification/` / `artifacts-index.md` |

## 追加時のチェックリスト

- [ ] 新しい媒体 → 原則 **/ワーク追加**（ワークスペース側に動的生成。プラグインは変更しない）。プラグイン標準パックに昇格させる場合のみ `commands/<日本語名>.md` + `procedures/takumi-<name>.md` を追加
- [ ] 新しいSNS標準媒体 → `procedures/takumi-sns-<name>.md` 追加とセットで **4点配線**: ①takumi-sns の振り分け表 ②takumi-sns §0 の媒体名リスト ③takumi-setup 質問1の選択肢 ④この台帳の内部手順一覧（2026-07-24 Threads 追加時に④が漏れた教訓）
- [ ] 新しい能力 → `docs/parts/<name>.md`（部品）+ parts/index.md に行追加。**コマンドは増やさない**
- [ ] 新しい執筆リファレンス（skills/）→ session-rules(3) と **該当サブエージェント（deliverable-writer / design-artisan / design-critic / pre-send-verifier）の参照表にも配線**（エージェントは自分でルールを読まないため、定義ファイルに書かないと届かない）
- [ ] この台帳に1行追加（カテゴリー + Pack）
- [ ] 定常実行するものはループ台帳にも追加
- [ ] README のコマンド数を更新
- [ ] 両 version ファイルを bump

## 配布時チェックリスト（Cowork 配布の実態に合わせた品質ゲート）

Cowork の配布は marketplace 同期＝**このリポジトリがそのまま配布物**（削除ビルドは存在しない）。/検証・TESTING・scripts/・.github/ は**品質保証機能として同梱する**（利用者が「プラグインを検証して」でいつでもセルフテストでき、CI が push ごとに回帰を担保する設計）。配布＝以下がすべて緑であること:

- [ ] `python scripts/lint.py` → `lint: OK`（双方向突合）
- [ ] `bash scripts/test-hooks.sh` → `ALL PASS`（防御系回帰）
- [ ] CI（GitHub Actions）最新 run が success
- [ ] Cowork 実機での直近の `/検証 full` 結果が TESTING.md 末尾に記録され、FAIL 0（未解消 FAIL があれば配布延期）
- [ ] `.claude-plugin/` の version が配布告知と一致（bump 忘れは更新反映されない）
- [ ] docs/escalations.md の上申事項が最新（プラグインで根治不可の限界が README「既知の限界」と齟齬なく開示されている）
