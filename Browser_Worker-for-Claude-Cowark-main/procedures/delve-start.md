---
description: ブラウザ操作タスクの開始手続き（ワークフローフラグ初期化 + フェーズ判定）。Use when ユーザーがサイトへの入力・クリック・投稿・設定変更などブラウザの変更操作を伴う作業を依頼したとき、変更操作の前に必ずこれを実行する（ゲートが変更操作をブロックするため）。閲覧・調査だけの依頼では不要
argument-hint: <タスク名>
---

Delvework のタスク「$ARGUMENTS」を開始してください。

手順の正本は `${CLAUDE_PLUGIN_ROOT}/docs/steps-reference.md`（見つからなければ Glob `**/docs/steps-reference.md`）。
**最初に必ず Read すること** — CP証跡定義（E-3）・レギュレーション検証（F-4）・ログ記録スキーマ（I-3）・ナレッジ構造（D-2）はそちらに従う。以下はフラグ操作の最短経路のみ。

0. `tasks/$ARGUMENTS.yaml`（登録済み定常タスク。/カスタマイズ のタスク登録が生成）があれば Read し、その steps を実行計画の正とする（destructive: true/auto のステップは Step H で人の承認を必ず取る）。なければ依頼文から計画を組む
1. ワークスペースに `memory/.workflow/` と `knowledge/sites/` がなければ作成する
2. フラグを初期化する:
   ```bash
   mkdir -p memory/.workflow knowledge/sites knowledge/logs
   rm -f memory/.workflow/{b4_done,e_done,k_done,bulk_send,psv_done,ov_done,critic_pending,critic_pass}
   echo "$ARGUMENTS" > memory/.workflow/active
   ```
   （`money_alert` は**意図的に消さない** — 前回の金銭停止は新タスクに持ち越し、解除は Money Watch 復帰手順のみ。手順8参照。`verify_allowlist` も**消さない** — 検証セッション中にタスク開始すると防壁が消える事故が 2026-07-24 に実測されたため、作成と削除は検証手順（delve-verify 後片付け）だけが行う）
3. `knowledge/sites/` を確認し、対象サイトのナレッジ有無でフェーズを判定する:
   - ナレッジなし → ① 初回 (First Delve)
   - ナレッジあり、成功ログなし → ② 再訪問 (Return)
   - 成功ログ（knowledge/logs/ のフロントマター status: success）+ shortcut_memo あり → ④ 最適化 (Optimize)
   - **実行中にナレッジと実ページの構造差異を検出したら → ③ 構造変更 (Remap)**: `rm -f memory/.workflow/e_done` して Step E からやり直し、`echo "3" > memory/.workflow/phase` に更新、ナレッジの差異箇所を修正してから再開する
4. フェーズを記録する:
   ```bash
   echo "<phase>" > memory/.workflow/phase && touch memory/.workflow/b4_done
   ```
   （`phase` は hook 非連動の状態メモ。ゲートに効くのは b4_done の方）
5. 変更操作の前（Step E）— 順に:
   - **変更前の状態をテキスト読取で記録**する（read_page / browser_snapshot。**スクリーンショットのみでの代替不可** — Money Watch の検知面のため）
   - **フェーズ②③④なら Step J（差分比較）**: 前回ログの after_state と今回の before_state を比較し、外部変更・リセットを検出したらユーザーに報告（steps-reference.md J）
   - **不可逆操作（送信・投稿・公開・削除・保存）があるなら CP（Critical Point）と成功証跡を宣言**（steps-reference.md E-3）
   - 済んだら:
   ```bash
   touch memory/.workflow/e_done
   ```
6. 実行後（Step I）— 順に:
   - **CP 証跡を照合**する（証跡なしで成功扱い禁止）
   - **不可逆送出（送信・投稿・公開・配信）があったタスクは outcome-verifier に after_state と CP 証跡を渡して独立検証させ、確定成功数で報告**（必須。steps-reference.md I）。判定を受領したら `echo "<VERIFIED n/m と1行要約>" > memory/.workflow/ov_done`（OV Gate: bulk_send 宣言タスクは ov_done なしで k_done 不可）
   - `knowledge/logs/<タスク名>_<日付>.md` に **YAMLフロントマター付き**でログを記録し、サイトナレッジを更新（steps-reference.md I-1.5〜I-5。フロントマター無しだと次回のフェーズ判定が壊れる）
7. タスク完了時は `memory/session-log.md`（正本はここ。`knowledge/logs/session-log.md` ではない — logs/ はタスク単位ログ専用）に学びを記録してから:
   ```bash
   touch memory/.workflow/k_done
   ```
   （Log Gate = 運用ルール: session-log を更新するまで k_done を作らない。hook の技術的強制はないため自己規律で守る）
8. タスク中に Money Watch 停止（money_alert）が立った場合の復帰手順は steps-reference.md 末尾に従う（strategy-advisor 助言 → ユーザー明示承認 → 解除。承認なしの解除は禁止）
