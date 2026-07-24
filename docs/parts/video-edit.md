# 部品: 動画加工（変換・透過・注釈・録画）

技術正本は docs/media-pipeline.md（ffmpeg 実測レシピ）。

- WebM 圧縮: ffmpeg -i in.mp4 -c:v libvpx-vp9 -b:v 0 -crf 40 out.webm
- アルファ付き WebM（LP演出）: 透過PNG連番 → -pix_fmt yuva420p -auto-alt-ref 0 必須
- フレーム分解（動画の精読・動画クロマキーの前処理）: ffmpeg -i in.mp4 f%04d.png
- 注釈アニメ（操作ガイド）: templates/guide-anim.py（スクショ+steps JSON → mp4/GIF）
- ブラウザ実録画: gif_creator 系（タブ内のみ・GIF最大50フレーム・専用DLフォルダ回収）
