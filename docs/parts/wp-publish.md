---
description: WordPress 記事公開 — 完成した記事コンテンツを WordPress に下書き投稿し、SEOメタ・スラッグ・カテゴリ/タグ・アイキャッチ・内部リンクを整え、ユーザー承認後に公開する。Use when 「WordPressに公開/投稿して」「記事を下書きに入れて」「この記事を公開して」等。Not for 記事本文の執筆（→/コンテンツ）、有料広告（対象外・ゼロ広告費）。
argument-hint: <記事ファイル/URL> [公開 or 下書き（既定は下書き）]
---

完成記事を WordPress に載せてください。既定は**下書き保存**（公開はユーザー承認後）。入力: $ARGUMENTS

## 手順

1. **前提確認**: アクティブブランドのブログ管理画面URL（brand.yaml / `knowledge/config`）。ログイン済みか（未ログインは人間に依頼・Credential Guard）。プラットフォームが WordPress でなければ該当媒体手順へ切り替える。
2. **タスク開始**: 変更操作のため takumi-start を通す（変更前記録）。
3. **入稿（下書き）**: 新規投稿 → タイトル・本文（見出し構造を保持）・アイキャッチ（`knowledge/brands/<slug>/channels/content/` の画像）を設定。
4. **SEO 整備**: references/seo-jp/SKILL.md に従い、タイトルタグ・メタディスクリプション・スラッグ（英数）・カテゴリ/タグ・OGP（SEOプラグインがあれば）。関連する既存記事へ内部リンクを2〜3本。
5. **表現チェック**: 公開前に references/ad-compliance-jp/SKILL.md（景表法・ステマ規制・PR表記・体験談の打消し表示）を通す。
6. **承認と公開**: 公開は**不可逆送出** → pre-send-verifier 監査 + ユーザー承認を得てから publish。承認が無ければ下書きのまま「公開はご確認後に」と報告する。
7. **記録**: 公開URL・スラッグ・公開日を `knowledge/brands/<slug>/channels/ownedmedia/` に控える。完了後 outcome-verifier で初動（インデックス・オーガニック流入）を追う導線に接続。

## 注意

- 有料プランのアップグレード・課金ページには触らない（ゼロ課金ゲート／Money Watch）。
- 一括公開はしない（1記事ずつ承認）。予約投稿を使う場合もユーザー承認後。
