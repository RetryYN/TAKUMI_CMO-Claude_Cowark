# メディア制作パイプライン — 正本

画像・動画系の内蔵部品の全体地図（2026-07-23 Cowork 実機検証済み）。各手順書はここを参照する（複製しない）。

## 部品一覧

| 部品 | 実体 | 用途 |
|---|---|---|
| 画像生成 | 部品 docs/parts/imagegen.md（/広告 等のパックから） | Gemini/ChatGPT の UI 操作で生成。グリーンバック指定可 |
| 動画生成 | 部品 docs/parts/videogen.md（本体は imagegen.md §2b） | **Gemini 経由で実機検証済み（2026-07-23）**。生成AI動画→取り込みは画像と同じルート（専用DLフォルダ / blob fetch） |
| 素材調達 | 部品 docs/parts/asset-collect.md / video-asset-collect.md | ストックサイトからライセンス証跡つき取り込み |
| 切り抜き | `templates/chromakey.py` | GB生成画像 → 透過PNG（緑優勢度→連続アルファ+スピル抑制） |
| バナー合成 | `templates/banner-compose.py` | 16:9整形+グラデ+コピー焼き込み（copywriting→ad-compliance 済み文言） |
| ガイドアニメ | `templates/guide-anim.py`（部品 video-edit.md） | スクショ+ステップJSON → 注釈アニメ mp4/GIF |
| ブラウザ録画 | gif_creator 系ツール | タブ内操作の GIF 記録（最大50フレーム・Downloads 保存→専用DLフォルダ原則） |
| 動画変換・透過動画 | ffmpeg（下記レシピ） | WebM 圧縮 / **アルファ付き WebM**（LP埋め込み用） |
| 組版・共有 | 部品 docs/parts/design-sync.md / canva-export.md | Canva 流し込み / claude.ai/design 同期。**HTML への組み込み（LP・モックアップに素材を配置して仕上げる工程）は DesignSync で claude.ai/design に流すのが正**（2026-07-23 ユーザー決定） |

## ffmpeg レシピ（実測値つき）

ffmpeg は Cowork サンドボックス標準搭載。ローカル Windows に無い場合はフレーム残置+コマンド提示（guide-anim.py の挙動）。

```bash
# mp4 → WebM (VP9)。実測: 88KB → 67KB。さらに詰めるなら AV1（libaom-av1）も搭載済み
ffmpeg -i in.mp4 -c:v libvpx-vp9 -b:v 0 -crf 40 out.webm

# 透過PNGフレーク列 → アルファ付き WebM（VP9 は透明度を保持。実測: 人物浮遊ループ 13KB）
# 必須: -pix_fmt yuva420p と -auto-alt-ref 0（これが無いとアルファが落ちる）
ffmpeg -framerate 24 -i f%04d.png -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 40 -auto-alt-ref 0 out.webm
```

浮遊ループのフレームは透過PNGを sin オフセットで数十枚描画すれば足りる（Pillow で `img.paste(fg, (0, int(8*sin(2πt))), fg)` の型）。

## 定番ライン

1. **バナー量産**: 生成（GB不要）→ banner-compose（コピー案リスト×画像ループ）→ /カスタマイズ でタスク化
2. **LPの動く人物/オブジェクト**（2026-07-23 動画生成起点でもフルライン実証済み: Gemini動画→背景除去→WebM）: GB指定生成 → chromakey → 浮遊フレーム → アルファWebM → `<video autoplay loop muted playsinline>` で任意背景の上に重ねる（GIFより滑らかで軽い。page-improve / ad-to-lp 部品の演出部品）。**HTML への組み込みは DesignSync で claude.ai/design のプロジェクトへ流す**（増分同期・承認フローは docs/parts/design-sync.md に従う）。ローカル HTML 直書きはプレビュー用途のみ
3. **操作教材**: gif_creator で実録画 → 専用DLフォルダ回収 → guide-anim / ffmpeg で注釈焼き込み → ガイド/レポートに添付

## ファイル形式カバレッジ（線引きの正本）

| 形式 | 扱い |
|---|---|
| PNG / JPG / WebP | 本プラグインで加工（Pillow テンプレ3本） |
| mp4 / GIF / WebM / アルファWebM | 本プラグインで変換（ffmpeg レシピ） |
| PPTX / DOCX / XLSX / PDF | **Cowork 本体の文書生成スキルに委ねる（プラグインで複製しない）**。プラグインの役割は橋渡しのみ — **2026-07-23 実機検証済み**: (a) PNG→PPTX は python-pptx（サンドボックスにプリインストール、内蔵 pptx スキルと同系）で 16:9 スライドに配置 (b) HTML→PDF は headless Chromium: `chromium --headless --disable-gpu --no-sandbox --print-to-pdf=out.pdf --no-pdf-header-footer file:///path/to/report.html` |
| SVG | **既知の穴（ベクター生成ライン不在）**。テキスト形式なので DesignSync に直接流せる唯一の画像形式であり、将来の優先候補。当面ロゴ・アイコンは収集部品（asset-collect）か Canva/Claude Design 側で |
| PSD / AI | 対象外（開けるツールなし）。Canva / Claude Design に寄せる |

## 素材パック規約（Claude Design へ渡すときの型）

素材を DesignSync で claude.ai/design に流すときは、素材単品でなく**パック**にする:

- 置き場: `knowledge/assets/packs/<パック名>/` に素材一式 + **DESIGN.md（マニフェスト・必須）**
- DESIGN.md の中身: 各素材の用途 / 寸法 / カラーコード（GB の緑等）/ 埋め込みスニペット（アルファWebM なら `<video autoplay loop muted playsinline>`）/ 出典・ライセンス（sources.md から転記）。Design 側の AI がこれを読めば使い方を誤らない（CLAUDE.md 相当。名前は衝突事故防止のため **DESIGN.md 固定**）
- 同期: DESIGN.md を最初に write_files し、続けて素材本体。**PNG バイナリ・data URI とも write_files を通る（2026-07-23 実機検証: written:1、get_file で contentType:image/png / isBase64:true の全量読み戻し一致）** — フォールバック不要。注意: get_file の読み戻しは 256KiB 上限の兆候あり（巨大バイナリの読み戻し・書き込み上限は未検証）。パック構造は `packs/<名>/{DESIGN.md, 素材…}` が list_files にそのまま出る
- ZIP は DesignSync には使わない（受け口がない）。**ZIP は人間・他ツール（Canva 等）向けの配布形態**としてのみ作る

## 共通ルール

- 公開向けコピーは ad-compliance-jp を通す / 人物素材はモデルリリース（asset-collect 部品）または生成でも実在人物風は禁止
- 取り込み・生成物はすべて `knowledge/assets/` + 出典台帳（sources.md）に記録
- Downloads 本体は接続しない（専用DLフォルダ原則）
- **前提: フル解像度素材の加工には専用DLフォルダ接続が必須**（README「メディア制作を使う場合」の3手順）。未接続で加工依頼が来たら、Downloads→手動アップロードで代替せず（**レンダリング失敗の実測あり 2026-07-23**）、先にセットアップを依頼して止まる。blob fetch が使える場面（URL露出）のみ例外
