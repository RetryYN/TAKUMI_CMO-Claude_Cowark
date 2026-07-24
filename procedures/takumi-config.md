---
description: タスクPack設定 — プラグイン機能のON/OFF管理。Use when ユーザーが「◯◯の機能を切って/入れて」「SNS機能は使わない」「機能設定」「パック一覧」等、機能の有効/無効の変更・確認を求めたとき。
argument-hint: [list | on <pack> | off <pack>]（省略時は list）
---

タスクPackの設定を操作してください。サブコマンド: $ARGUMENTS

## Pack 定義（機能の束）

| pack | 含まれる機能 | 既定 |
|---|---|---|
| core | start / status / demo / dashboard / feedback / skillify / ゲート・Credential Guard | **常時ON（無効化不可）** |
| research | style（スタイル調査）/ audit（サイト診断）/ watch（競合ウォッチ） | ON |
| creative | improve（ページ改善）/ adlp（広告→LP）/ adscript（動画広告台本）+ design-artisan / design-critic | ON |
| sns | sns（SNS運用バッチ）+ sns-jp スキル | ON |
| media | media（媒体管理） | ON |
| deep | deep（徹底モード） | ON |
| writing-hr | 人材ライティング6スキル（recruit/copy/sales/logical/business/storytelling） | ON |
| compliance | ad-compliance-jp（広告法規チェック） | ON ※OFF時はその旨を成果物に明記 |
| slack | Slack通知・非同期承認キュー | ON（コネクタ無ければ自動フォールバック） |

## 設定ファイル（正本）

`knowledge/config/packs.conf` — 1行1パック、`<pack>=on|off`。**書かれていないパックは ON**（既定有効）。

```
sns=off
deep=off
```

## サブコマンド

- **list**: 全パックの状態表を表示（設定ファイルが無ければ「全て既定ON」と表示）
- **on/off <pack>**: packs.conf を編集（無ければ作成）し、変更後の一覧を表示。core の off は拒否する
- 変更後は「次のセッションから確実に反映。今セッションも即座に従う」と案内し、以後この会話でも無効パックの機能を使わない

## 無効パックの振る舞い（全エージェント共通）

- 無効パックのコマンド・スキルは**使わない・提案しない・自動発火させない**
- ユーザーが無効機能を明示的に呼んだ場合のみ「このパックはOFFです。有効化しますか？（『◯◯パックをONにして』）」と1行で案内する
