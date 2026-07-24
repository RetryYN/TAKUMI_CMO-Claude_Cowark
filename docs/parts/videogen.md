# 部品: 動画生成（Gemini 経由 — 2026-07-23 実機検証済み）

手順の本体は imagegen.md の §2b（動画生成）。要点:
- 生成は分単位 — wait 系で完了待機。生成枠が重いので本数を先に合意（原則1〜2本）
- 採用本体のみ専用DLフォルダ / blob fetch で取り込み（Downloads→手動アップロードはレンダリング失敗の実測あり）
- 後段の圧縮・アルファ化・フレーム分解は video-edit.md / docs/media-pipeline.md へ
- 実在人物風の生成は禁止（imagegen.md の注意と同じ）
