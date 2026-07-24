#!/usr/bin/env python3
"""Delvework 操作ガイドアニメーション テンプレート — 2026-07-23 Cowork 実機検証済みの型。
スクリーンショット + ステップ定義(JSON) から、対象を暗幕+パルスリングでハイライトする
ガイド動画（mp4 / GIF）を生成する。ffmpeg 必須（Cowork サンドボックスは標準搭載）。

  python3 guide-anim.py <スクショ.png> <steps.json> <出力ベース名>

steps.json の形式（1ステップ = 対象矩形 + ラベル）:
  [
    {"rect": [x, y, w, h], "label": "① ここにプロンプトを入力"},
    {"rect": [x, y, w, h], "label": "② モデルを切り替え"}
  ]

出力: <ベース名>.mp4 と <ベース名>.gif（ffmpeg 不在時はフレームPNGを残しコマンドを表示）
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FPS = 12
FRAMES_PER_STEP = 24  # 2秒/ステップ
ACCENT = (255, 140, 40)
DIM_ALPHA = 150

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/YuGothB.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_frame(base: Image.Image, rect, label: str, step_no: int, total: int,
                 t: float) -> Image.Image:
    """t: 0..1 ステップ内の進行度。パルスリング + 暗幕 + 吹き出し + ステップ表示。"""
    W, H = base.size
    x, y, w, h = rect
    img = base.convert("RGBA")

    # 対象以外を暗幕で落とす
    dim = Image.new("RGBA", (W, H), (0, 0, 0, DIM_ALPHA))
    d = ImageDraw.Draw(dim)
    d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=(0, 0, 0, 0))
    img = Image.alpha_composite(img, dim)

    d = ImageDraw.Draw(img)
    # パルスリング（sin で拡縮）
    pulse = 6 + 5 * math.sin(t * math.pi * 4)
    d.rounded_rectangle([x - pulse, y - pulse, x + w + pulse, y + h + pulse],
                        radius=12, outline=ACCENT, width=5)

    # 吹き出し（対象の下、はみ出すなら上）
    f = load_font(28)
    bb = d.textbbox((0, 0), label, font=f)
    pad = 14
    bw, bh = bb[2] + pad * 2, bb[3] + pad * 2
    bx = max(10, min(x + w // 2 - bw // 2, W - bw - 10))
    by = y + h + 24 if y + h + 24 + bh < H else y - bh - 24
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10,
                        fill=(255, 255, 255, 235), outline=ACCENT, width=3)
    d.text((bx + pad, by + pad - bb[1]), label, font=f, fill=(20, 20, 20))

    # ステップ表示（左下）
    f2 = load_font(22)
    tag = f"Step {step_no} / {total}"
    d.rounded_rectangle([10, H - 48, 10 + d.textbbox((0, 0), tag, font=f2)[2] + 24, H - 10],
                        radius=8, fill=(0, 0, 0, 200))
    d.text((22, H - 42), tag, font=f2, fill=(255, 255, 255))
    return img.convert("RGB")


def main(shot: str, steps_json: str, out_base: str) -> None:
    base = Image.open(shot)
    if base.width % 2:  # ffmpeg の yuv420p は偶数サイズ必須
        base = base.crop((0, 0, base.width - 1, base.height))
    if base.height % 2:
        base = base.crop((0, 0, base.width, base.height - 1))
    steps = json.loads(Path(steps_json).read_text(encoding="utf-8"))
    if not isinstance(steps, list):
        raise SystemExit(
            f"steps.json はステップの配列である必要があります（{type(steps).__name__} が渡されました）。\n"
            '正しい形式: [{"rect": [x, y, w, h], "label": "説明文"}, ...]'
        )
    for idx, st in enumerate(steps, 1):
        if not isinstance(st, dict) or "rect" not in st or "label" not in st:
            raise SystemExit(
                f"steps.json の {idx} 番目のステップに rect / label がありません。\n"
                '正しい形式: {"rect": [x, y, w, h], "label": "説明文"}'
            )

    tmp = Path(tempfile.mkdtemp(prefix="guideanim-"))
    n = 0
    for i, st in enumerate(steps, 1):
        for f_i in range(FRAMES_PER_STEP):
            frame = render_frame(base, st["rect"], st["label"], i, len(steps),
                                 f_i / FRAMES_PER_STEP)
            frame.save(tmp / f"f{n:04d}.png")
            n += 1
    print(f"frames: {n} → {tmp}")

    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", str(tmp / "f%04d.png"), "-pix_fmt", "yuv420p",
                        f"{out_base}.mp4"], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", str(tmp / "f%04d.png"),
                        "-vf", "fps=10,scale=800:-1:flags=lanczos", f"{out_base}.gif"],
                       check=True)
        shutil.rmtree(tmp)
        print(f"saved: {out_base}.mp4 / {out_base}.gif")
    else:
        print(f"WARN: ffmpeg 不在。フレームは {tmp} に残置。手動生成:")
        print(f"  ffmpeg -framerate {FPS} -i {tmp}/f%04d.png -pix_fmt yuv420p {out_base}.mp4")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
