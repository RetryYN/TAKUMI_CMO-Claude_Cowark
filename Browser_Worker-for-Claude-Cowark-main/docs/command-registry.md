# 台帳（Registry）── 4層アーキテクチャの正本

**このファイルがコマンド・部品・定常ループの一覧の正本。** 追加・改名・削除は必ずここを同時に更新する。
`/検証` はこの台帳と `commands/`・`procedures/`・`docs/parts/`・`references/` の実体の突合を検証項目に含める。

## 世界観 — Delvework をして、Forgecraft を返す（2026-07-23 ユーザー決定）

| コア | 意味 | 実体 |
|---|---|---|
| **Delvework** | 掘る — 探索・マッピング・収集・地図の蓄積 | A〜K ワークフロー / フェーズ①〜④ / knowledge/ / リサーチ・収集部品 |
| **Forgecraft** | 鍛える — 素材を実証基準で成果物に加工 | クリエイティブ部品群 / references 17本（実証判断基準）/ 職人エージェント（writer・artisan・critic）/ 監査（pre-send・outcome） |

## 構造の芯 — 4層アーキテクチャ（2026-07-23 ユーザー決定で確定）

| 層 | 概念 | 実体 |
|---|---|---|
| **コマンド** | カテゴリーレベル（媒体・対象のタスクパック）。要望は引数に自由に書かせる | `commands/`（登録10本・日本語名）+ `procedures/delve-*.md`（内部手順含め27本） |
| **ワークフロー** | 進め方 = タスクの連なり。A〜K 実行チェーン + タスク5型の連結 | `docs/steps-reference.md` + hooks のゲート + フェーズ①〜④ |
| **タスク** | 単一の仕事。動詞レベル: **リサーチ / 収集 / クリエイティブ / 分析 / 掃き出し** | `tasks/*.yaml`（/カスタマイズ のタスク登録 = delve-task が生成）+ `docs/parts/`（部品） |
| **サブエージェント** | 専門作業の職人。タスクから呼ばれる | `agents/`（6体: writer / artisan / critic / advisor / pre-send-verifier / outcome-verifier） |

**実行粒度の3段**（全パック共通）: ①タスク単体で完結 ②ワークフローで解決（タスク連結） ③まるっと（パックの定常ループ一式）。振り分け原則は `docs/parts/index.md`。

新しい媒体を増やす＝パック1個追加。できることを増やす＝部品（docs/parts/）の追加。**エンジン側（ワークフロー層）は一切変えない。**

**動的パック**: 媒体の個別コマンド（例: /ワンキャリア /doda）は **/ワーク追加** で生成する — 登録 + 初期マッピング（フェーズ①・読み取り専用）+ ワークスペース `.claude/commands/` への専用コマンド生成を1コマンドで実行（プラグイン本体は増やさない）。**/セットアップ の媒体選択でも自動生成**する — SNS=`/<媒体名>運用`（/X運用 等）、広告媒体=`/<媒体名>広告`（/Google広告 等・参照先 delve-ads で媒体固定）、求人媒体=/ワーク追加接続で `/<媒体名>`。以後の単一媒体依頼は専用コマンドが第一入口（/SNS運用 /広告 /媒体管理 は複数媒体・媒体不明時の受け皿に降格）。**既存パックに該当しない完全別ワークは非表示の親「その他ワーク」の配下**に生成する（親判定表の正本は procedures/delve-add-work.md §4 — registry.yaml に `parent:` を記録）。

## 命名ルール

1. **登録コマンド（`commands/`）は日本語名が本体** — メニューに並ぶのはこの10本のみ。description には自動発火用の「Use when」を日本語で書く
2. **手順の正本は `procedures/delve-*.md`（英語ケバブケース、登録対象外）** — 日本語コマンドは薄いラッパー（procedures を Read + Glob フォールバック）。1対1で、片方だけの追加は禁止
3. 部品（docs/parts/）はコマンド登録しない。パックのタスクが Read して使う
4. `/スキル化` が生成するワークスペーススキルも同ルール: name は英語ケバブ、description の発火例は日本語の言い方で書く

## コマンド台帳（登録10本）

| 手順書（procedures/） | コマンド名（登録） | カテゴリー | Pack | 代表的な言い方 |
|---|---|---|---|---|
| delve-sns | SNS運用 | SNS媒体 | sns | 「Xの投稿作って」「noteを書いて」（媒体不明なら「どの媒体？」を選択式で。setup.yaml の選択媒体のみ提示） |
| delve-research | リサーチ | 横断 | research | 「競合を分析して」「トレンド調べて」（対象不明なら「どの媒体・対象？」を選択式で） |
| delve-media | 媒体管理 | 求人媒体 | media | 「全媒体の状況見せて」「スカウト送って」 |
| delve-add-work | ワーク追加 | 基盤 | core | 「dodaを追加して」（登録+初期マッピング+専用コマンド生成） |
| delve-setup | セットアップ | 基盤 | core | 「初期設定」「使う機能を選びたい」（回答保存・済んだ質問は聞かない・未選択パックは発火停止） |
| delve-website | Webサイト | 自社・広告 | research | 「表示速度を測って」「このLP改善して」 |
| delve-ads | 広告 | 自社・広告 | creative | 「バナー作って」「競合広告を洗い出して」 |
| delve-customize | カスタマイズ | 基盤 | core | 「毎朝これやって」「これ覚えて」（タスク登録/スキル化/好み記憶/機能ON-OFF を選択式で） |
| delve-reporting | レポート | 記録 | core | 「今どうなってる？」「今日の作業まとめて」（トップ=ダッシュボード + 作業ログ/運用レポートを選択） |
| delve-verify | 検証 | 記録 | core | 「プラグインを検証して」※セルフテスト。品質保証機能として同梱（導入直後は quick、更新後・不調時は full） |

**計: 登録コマンド 10 / 内部手順 17 / 手順書 27（procedures/）**

## 内部手順台帳（メニュー非表示 — 自然文・ルール発火で動く。手順書は procedures/ に残す）

| 手順書 | 旧コマンド名 | 発火のさせ方 |
|---|---|---|
| delve-start | （内部）タスク開始 | 変更操作の前段として各パックが内部で通す関所（session-rules (1)） |
| delve-sns-x | （内部）X媒体手順 | /SNS運用 が媒体判定後に振り分け |
| delve-sns-instagram | （内部）Instagram媒体手順 | 同上 |
| delve-sns-tiktok | （内部）TikTok媒体手順 | 同上 |
| delve-sns-threads | （内部）Threads媒体手順 | 同上（Meta系: IGログイン連動・予約投稿不可の注意あり） |
| delve-sns-note | （内部）note媒体手順 | 同上 |
| delve-sns-youtube | （内部）YouTube媒体手順 | 同上 |
| delve-sns-line | （内部）LINE媒体手順 | 同上 |
| delve-task | （内部）定常タスク登録 | /カスタマイズ が振り分け（「毎朝◯◯して」） |
| delve-dashboard | （内部）ダッシュボード | /レポート のトップとして生成（定常ループの締めもここ） |
| delve-report | （内部）作業ログ | /レポート が振り分け |
| delve-status | （内部）状態確認 | 「今どうなってる？」等の自然文（session-rules (8)） |
| delve-demo | （内部）デモ | 「何ができるの？」→ ダッシュボードの説明書へ誘導 |
| delve-config | （内部）機能設定 | 「SNS機能を切って」等の自然文 |
| delve-skillify | （内部）スキル化 | 手順を教わった・同一パターン2回目の自動検知（session-rules (3c)） |
| delve-feedback | （内部）メモリ保存 | 成果物への評価・修正指示の自動検知（session-rules (3b)） |
| delve-memory | （内部）メモリ圧縮 | 「ログを整理して」/ session-log 肥大時に提案 |

※ procedures/ を持たない内部手順: **無人運用前チェック**（docs/unattended-ops.md 内 — 「無人運用前チェックして」の自然文、およびブラウザ操作タスクのローカル登録前に delve-task が必須で通す）

## 部品台帳（docs/parts/ — タスク5型。詳細は docs/parts/index.md が正本）

| タスク型 | 部品 |
|---|---|
| 計画 | content-calendar（カレンダー・送信/配信計画 → queue・定常タスクへ接続） |
| リサーチ | style-research / deep-research / sns-research |
| 収集 | asset-collect / video-asset-collect |
| クリエイティブ | jobpost-writing / scoutmail-writing / imagegen / videogen / image-edit / video-edit / page-improve / ad-to-lp / video-ad-script |
| 分析 | site-audit / sns-research（数値読み） |
| 掃き出し | design-sync / canva-export / design-handoff（成果物を Claude Design へ送って人間が編集→回収。critic PASS 後に「Design に送って手直ししますか？」） |

SNS 共通運用フローは `docs/sns-ops.md`、メディア技術地図は `docs/media-pipeline.md`、無人運用・承認キュー・クラウド→ローカル移行は `docs/unattended-ops.md`、プラットフォーム上申事項（プラグインで根治不可の課題と緩和策）は `docs/escalations.md` が正本。

## 執筆リファレンス台帳（references/ — スキル一覧には登録しない内部教科書）

> 登録方針: references/ は**全て Read 専用**（skills/ 規約に置かず自動発火させない）。ワークスペース側で同名スキルが Skill 登録されている場合も正本はプラグインの references/ とし、更新はこちらに行う（二重管理の乖離防止）。

| リファレンス | 主な使い手 | 用途 |
|---|---|---|
| logical-writing | Webサイト・全パックのレポート | 分析レポート・戦略提案 |
| sns-jp | SNS媒体パック | 日本のSNS文化・ハッシュタグ・投稿時間帯・LINE配信設計 |
| content-design | SNS媒体パック | 投稿コンテンツの設計・カレンダー |
| storytelling | SNS媒体・求人媒体 | 社員ストーリー・採用広報記事 |
| recruit-writing | 求人媒体（jobpost/scoutmail 部品） | 求人原稿・スカウト本文 |
| copywriting | 広告・求人媒体・SNS | キャッチコピー・件名13字 |
| video-ad | 広告 | 動画広告の構成・台本 |
| ad-compliance-jp | 広告・全公開物 | 日本の広告表現規制チェック |
| web-design | Webサイト・広告 | LP/ページのデザイン実装 |
| business-writing | 基盤 | 社内外メール・事務連絡・校正 |
| seo-jp | Webサイト・SNS媒体 | 日本語SEO/AEO — 記事設計・既存ページ診断・AI検索対応 |
| cro-jp | Webサイト・広告・求人媒体 | CRO/ABテスト — 転換率改善の仮説設計・文面ABテスト |
| psych-nudge-jp | 全パック（コピー・CTA設計） | 行動経済・ナッジの日本実証 — 訴求フレーム選択（損失/利得/規範/利他）とEASTチェック |
| psych-ux-jp | Webサイト・広告 | UI/UX・社会心理の日本実務 — 視線/密度/配色/フォーム/実績表示の判断基準 |
| psych-target-jp | 求人媒体・SNS媒体（文面の書き分け） | 読み手の心理プロファイル×CBT健全応用 — 3軸判定（不安の核/意思決定スタイル/関係段階） |
| design-evidence-jp | Webサイト・広告・全HTML成果物 | 実証デザイン数値基準 — タイポ/配色/LPレイアウト/グラフ選択の具体値（DADS・JIS・WACUL・NN/g・Cleveland-McGill） |
| sales-writing | 基盤 | 受注目的の提案書・テレアポ |

## 定常ループ台帳（標準セット。実運用の正本はワークスペースの `knowledge/config/loops.yaml` — /カスタマイズ のタスク登録が管理）

| カテゴリー | ループ | 標準周期 | 使うコマンド | 締め |
|---|---|---|---|---|
| 自社・広告 | 自社サイト診断 | 週次（月曜） | Webサイト | ダッシュボード更新 |
| SNS媒体 | 予約投稿・実績記録 | 毎朝 | SNS運用 | 同上 |
| SNS媒体 | ストック補充 | 週次 or 残量アラート時 | SNS運用 | 同上 |
| SNS媒体 | カレンダー消化率チェック・翌週計画 | 週次（金曜） | SNS運用（content-calendar 部品） | 同上 |
| 求人媒体 | 媒体ステータス巡回 | 毎朝 | 媒体管理 | 同上 |
| 求人媒体 | スカウト送信 | 平日（承認後のみ送信） | 媒体管理 + タスク開始 | 同上 |
| 広告 | 広告リサーチ・制作 | 依頼時（定常化も可） | 広告 | 同上 |

**原則1: 実行系（変更操作）は全カテゴリー共通で `delve-start` が担う**（A〜Kワークフロー + 変更前記録/承認の関所）。パック別の実行コマンドは新設しない。

**原則2: 各ループの締めに `delve-dashboard` を実行**し、司令塔を常に最新へ。

**原則3: 最適化（フェーズ④）は標準の裏側動作** — マッピングとタスク順序を記録し、成功の繰り返しで最短ルート整備・スクリプト化を自動で提案する（バックグラウンドエージェントへの委譲可）。ユーザーが頼まなくても走る。

## カテゴリー → knowledge/ フォルダ対応

| カテゴリー | 主な保存先 |
|---|---|
| SNS媒体 | knowledge/sns/<platform>/（ネタ帳は queue.md、調査は research/） |
| 求人媒体 | knowledge/media/・approvals/・drafts/ |
| 自社・広告 | knowledge/audits/・styles/・mockups/・assets/・drafts/ |
| 基盤・記録（横断） | knowledge/sites/・logs/・reports/・tacit/・feedback/・data/・config/・artifacts-index.md |

## 追加時のチェックリスト

- [ ] 新しい媒体 → 原則 **/ワーク追加**（ワークスペース側に動的生成。プラグインは変更しない）。プラグイン標準パックに昇格させる場合のみ `commands/<日本語名>.md` + `procedures/delve-<name>.md` を追加
- [ ] 新しいSNS標準媒体 → `procedures/delve-sns-<name>.md` 追加とセットで **4点配線**: ①delve-sns の振り分け表 ②delve-sns §0 の媒体名リスト ③delve-setup 質問1の選択肢 ④この台帳の内部手順一覧（2026-07-24 Threads 追加時に④が漏れた教訓）
- [ ] 新しい能力 → `docs/parts/<name>.md`（部品）+ parts/index.md に行追加。**コマンドは増やさない**
- [ ] 新しい執筆リファレンス（references/）→ session-rules(3) と **該当サブエージェント（deliverable-writer / design-artisan / design-critic / pre-send-verifier）の参照表にも配線**（エージェントは自分でルールを読まないため、定義ファイルに書かないと届かない）
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
