# 部品: Claude Design 連携（DesignSync — 掃き出しの既定ルート）

メディア素材入り HTML / デザインシステムへの反映は claude.ai/design へ流すのが正（2026-07-23 ユーザー決定）。ローカルHTML直書きはプレビュー用途のみ。

**DesignSync ツールの認可が無い環境（Cowork cloud で実測 2026-07-24）**では、この API ルートは使えない → **docs/parts/design-handoff.md（UIルート — ブラウザで claude.ai/design に添付して人間編集へハンドオフ）** に切り替える。

## 手順
1. list_projects で対象確認（なければ create_project）
2. 書き込むパスの計画を提示してユーザー承認（finalize_plan）— 削除も同承認制
3. write_files で増分同期（承認範囲外の書き込み・一括置き換え禁止。1コンポーネントずつ）
4. 素材は素材パック規約（docs/media-pipeline.md）: packs/<名>/ + DESIGN.md マニフェスト必須、DESIGN.md 先行同期
5. 同期先URLを knowledge/artifacts-index.md に記録

実測（2026-07-23）: PNGバイナリ・data URI とも write_files 可（get_file 読み戻し 256KiB 上限の兆候のみ注意）。プロジェクト削除メソッドは無い（不要プロジェクトはユーザーが UI から削除）。
