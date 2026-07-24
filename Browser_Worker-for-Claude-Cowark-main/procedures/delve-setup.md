# /セットアップ — 初期ヒアリングのチェックリスト（delve-setup）

プラグイン導入直後に1回だけ回す初期設定。回答は `knowledge/config/setup.yaml` に保存し、**回答済みの質問は二度と聞かない**（次回以降セッションのコンテキストにも入らない — session-start は未回答時のみ1行案内を出す）。

## 進め方

質問ツール（選択肢UI）で以下を順に確認。途中でやめても回答済み分は保存し、残りは次回 /セットアップ で続きから。

### チェックリスト

1. **運用するSNS媒体**（複数選択: X / Instagram / Threads / TikTok / note / YouTube / LINE公式 / どれもやらない。1媒体=1択で束ねず、1問4択に収まらないぶんは同じ呼び出し内の2問目に分割し、全問で複数選択可を維持）
   → 選ばなかった媒体は `knowledge/config/packs.conf` に `sns-<媒体>=off` を書く（例: `sns-tiktok=off`）。該当パックは以後、提案・自動発火の対象外（session-start が毎回注入）。後から「TikTokもやる」で on に戻せる
   → **選んだ各媒体にはワークスペース `.claude/commands/<媒体名>運用.md`（例: X運用.md / Instagram運用.md）を生成する**（テンプレは /ワーク追加 §4 が正本。参照先は該当媒体手順 `procedures/delve-sns-<媒体>.md`。ゲート・共通フローは delve-sns §2 と同じものをポインタで効かせる）。以後この媒体の依頼は専用コマンドが第一入口になり、**/SNS運用 は「複数媒体まとめて」と「媒体不明」の入口としてだけ残る**。コマンド有効化のタイミングは環境差あり（2026-07-24 実測: cloud=同一セッション内で即時登録 / ローカル=次セッションから）— ユーザーには「次のセッションから確実に使える」と一言添える
2. **画像・動画の生成AIアカウント**（Gemini / ChatGPT / 両方 / なし + 無料/有料プラン）
   → `knowledge/config/accounts.md` に記録（imagegen 部品の Step 0 が参照。以後この質問はしない）。有料なら商用利用条件・透かし（SynthID等）も確認して記録
3. **素材サイト**（有料アカウントの有無: Pngtree / Adobe Stock / PIXTA / その他 / 無料のみ）
   → setup.yaml に「素材として使ってよいサイト」リストとして記録（asset-collect 部品が参照。無料のみならクレジット表記necessity・商用可のCP確認を厳格運用）
4. **求人媒体**（使っている媒体名を聞く。あれば → その場で /ワーク追加 に接続して登録+初期マッピング+**専用コマンド生成（/doda 等）**まで。以後この媒体の依頼は専用コマンドが第一入口になり、/媒体管理 は「複数媒体まとめて」と「媒体不明」の入口として残る）
5. **広告媒体**（複数選択: Google広告 / Meta広告（Instagram・Facebook）/ TikTok広告 / X広告 / Yahoo!広告 / 出稿していない。SNSと同じく1媒体=1択・4択超は2問目に分割）
   → setup.yaml に `ad_media:` として記録。**選んだ各媒体にはワークスペース `.claude/commands/<媒体名>広告.md`（例: Google広告.md / Meta広告.md）を生成する**（テンプレは /ワーク追加 §4 が正本。参照先は procedures/delve-ads.md で、媒体を前提として固定＝§0 の媒体質問をスキップ）。以後この媒体の広告依頼は専用コマンドが第一入口になり、**/広告 は「複数媒体・媒体不明・出稿以外の全般（バナー・LP等）」の入口として残る**。※広告の**出稿・課金操作は引き続きAI禁止**（Money Watch / URL Guard）— 専用コマンドでも調査・制作・分析まで
6. **専用DLフォルダ**（CoworkDrop 等の設定・接続が済んでいるか）
   → 未設定なら README「メディア制作を使う場合」の3手順を案内し、setup.yaml に `dl_folder: pending` と記録（メディア加工の依頼時に再案内される）
7. **自社サイトURL**（あれば記録 — /Webサイト の定常診断ループ提案につなげる）

### 仕上げ（質問なし・自動）

- `knowledge/verification/verdict-log.md` が無ければヘッダ行だけ作成する（`# 送信監査 VERDICT ログ` + 列説明1行）。pre-send-verifier の較正資産の置き場を確定させるため

### 保存形式（knowledge/config/setup.yaml）

```yaml
completed: 2026-07-23        # 全問回答した日付。部分回答なら pending
sns: [x, note]               # 運用する媒体
genai: {gemini: 有料, chatgpt: なし}
stock_sites: [pngtree（無料枠）]
recruit_media: [onecareer]   # /ワーク追加 済みの id
ad_media: [google, meta]     # 専用コマンド生成済みの広告媒体
dl_folder: ok                # ok | pending
own_site: https://…
```

### 締め

- 有効化された構成を1枚のサマリーで提示（「この構成で運用を始めます。変更はいつでも /セットアップ か『TikTokもやる』の一言で」）
- packs.conf / accounts.md / setup.yaml の書き込み結果を報告し、session-log に1行記録

## 再実行・変更

- 「セットアップやり直して」または引数 `all` → 回答済みも含め全問再確認
- 個別変更（「Instagramも追加」）→ 該当キーだけ更新（全チェックリストは回さない）
