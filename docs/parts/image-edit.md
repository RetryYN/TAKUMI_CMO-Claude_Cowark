# 部品: 画像加工（バナー合成・背景除去・整形）

技術正本は docs/media-pipeline.md。前提: フル解像度素材は専用DLフォルダ経由（README「メディア制作を使う場合」）。

- バナー合成（16:9整形+グラデ+コピー焼き込み）: templates/banner-compose.py（--headline / --sub / --badge）。文言は copywriting、公開向けは ad-compliance-jp 済みで
- 背景除去: グリーンバック素材なら templates/chromakey.py（--bg で合成確認も出力）。GB無し素材は Canva / Claude Design 側の背景除去へ
- PPTX/PDF への掃き出し: python-pptx / headless Chromium --print-to-pdf（media-pipeline に確定コマンド）
