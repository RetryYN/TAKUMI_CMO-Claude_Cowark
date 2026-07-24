-- Delvework 計測データベース スキーマ v1
-- 場所: ワークスペースの knowledge/data/delvework.db
-- 初期化: python -c "import sqlite3,pathlib; pathlib.Path('knowledge/data').mkdir(parents=True,exist_ok=True); sqlite3.connect('knowledge/data/delvework.db').executescript(open('<このファイル>').read())"
-- 方針: 設定・知識・手順は Markdown/YAML（人間が読み書きする）、時系列の計測値だけ SQLite（前回比・推移・集計用）
-- 書き込みは常に INSERT（追記型）。UPDATE で履歴を消さない。最新値は MAX(measured_at) で取る

PRAGMA journal_mode = WAL;

-- スキーマバージョン管理
CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT OR IGNORE INTO schema_meta VALUES ('version', '1');

-- 媒体ステータス履歴（/delve-media status が追記）
CREATE TABLE IF NOT EXISTS media_status (
  id INTEGER PRIMARY KEY,
  measured_at TEXT NOT NULL,          -- ISO8601
  media_id TEXT NOT NULL,             -- registry.yaml の id
  metric TEXT NOT NULL,               -- 例: 'スカウトチケット残数'
  value REAL,
  value_text TEXT,                    -- 数値化できない値（'2026-12-31' 等）
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_media_status ON media_status(media_id, metric, measured_at);

-- SNS投稿と成果（/delve-sns が管理。1投稿1行 + メトリクスは別テーブルに追記）
CREATE TABLE IF NOT EXISTS sns_posts (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL,             -- x / note / ...
  post_ref TEXT,                      -- 投稿ID or URL（判明後に埋める）
  scheduled_at TEXT,                  -- 予約日時
  posted_at TEXT,
  status TEXT NOT NULL DEFAULT 'draft',  -- draft / approved / scheduled / posted / dropped
  content_type TEXT,                  -- content-design の C
  pattern TEXT,                       -- 同 P
  treatment TEXT,                     -- 同 T
  hook_type TEXT,
  body TEXT,                          -- 本文（PIIを含めない）
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sns_metrics (
  id INTEGER PRIMARY KEY,
  post_id INTEGER NOT NULL REFERENCES sns_posts(id),
  measured_at TEXT NOT NULL,
  impressions INTEGER, engagements INTEGER, likes INTEGER,
  reposts INTEGER, replies INTEGER, bookmarks INTEGER, views INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sns_metrics ON sns_metrics(post_id, measured_at);

-- サイト診断履歴（/Webサイト の診断タスクが追記。ページ×計測日）
CREATE TABLE IF NOT EXISTS audit_pages (
  id INTEGER PRIMARY KEY,
  measured_at TEXT NOT NULL,
  site TEXT NOT NULL,
  url TEXT NOT NULL,
  ttfb_ms REAL, lcp_ms REAL, cls REAL,
  transfer_kb REAL, requests INTEGER,
  quality_issues INTEGER,             -- 品質チェックの指摘数
  broken_links INTEGER,
  detail_json TEXT                    -- 全計測値のJSON（リソース内訳等）
);
CREATE INDEX IF NOT EXISTS idx_audit ON audit_pages(site, url, measured_at);

-- 競合ウォッチ差分履歴（競合定点観測タスクが変更検知時のみ追記）
CREATE TABLE IF NOT EXISTS watch_changes (
  id INTEGER PRIMARY KEY,
  detected_at TEXT NOT NULL,
  site TEXT NOT NULL,
  severity TEXT NOT NULL,             -- important / medium / minor
  category TEXT,                      -- 料金 / コピー / 構成 / キャンペーン
  before_text TEXT, after_text TEXT,
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_watch ON watch_changes(site, detected_at);

-- アーティファクト発行台帳（artifacts-index.md と同内容の構造化版。正本はDB、mdは人間用ビュー）
CREATE TABLE IF NOT EXISTS artifacts (
  id INTEGER PRIMARY KEY,
  published_at TEXT NOT NULL,
  kind TEXT NOT NULL,                 -- report / mockup / dashboard / guide
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source_path TEXT                    -- 元ファイルのワークスペースパス
);

-- 承認キュー（Slack非同期承認の正本）
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY,
  approval_code TEXT UNIQUE NOT NULL, -- 'A-12' 形式
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL,                 -- scout / sns_post / ...
  summary TEXT NOT NULL,
  payload_path TEXT,                  -- 本文の保存先（mdファイル）
  status TEXT NOT NULL DEFAULT 'pending', -- pending / approved / revised / rejected / sent / expired
  decided_at TEXT,
  sent_at TEXT
);

-- 定常タスク実行ログ（各コマンドが完了時に1行）
CREATE TABLE IF NOT EXISTS task_runs (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  command TEXT NOT NULL,              -- 実行したコマンド/タスク名（例: Webサイト / SNS運用）
  result TEXT NOT NULL,               -- ok / partial / failed / skipped
  summary TEXT                        -- 1行サマリー
);
