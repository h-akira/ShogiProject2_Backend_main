# データベース設計

## 概要

メイン API のデータストアとして Aurora DSQL を採用する。PostgreSQL 互換の分散 SQL データベースであり、サーバーレス・IAM 認証・VPC 不要の特性を持つ。

### クラスタ基本情報

| 項目 | 値 |
|------|-----|
| クラスタ名 | `dsql-sgp-${env}-backend-main` |
| データベース名 | `postgres`（Aurora DSQL 固定） |
| 認証方式 | IAM 認証（パスワードレス） |
| 接続ドライバ | psycopg（aurora-dsql-python-connector 経由） |

---

## テーブル設計

### kifus テーブル

棋譜データを格納する。

| カラム名 | 型 | 制約 | 説明 |
|---------|-----|------|------|
| `kid` | VARCHAR(12) | PRIMARY KEY | 棋譜 ID (12 文字の英数字) |
| `username` | VARCHAR(255) | NOT NULL | Cognito ユーザー名 |
| `slug` | VARCHAR(1024) | NOT NULL | スラグ（階層パス。`.kif` 付き） |
| `side` | VARCHAR(20) | NOT NULL DEFAULT 'none' | 先後 (`none` / `sente` / `gote`) |
| `result` | VARCHAR(20) | NOT NULL DEFAULT 'none' | 勝敗 (`none` / `win` / `loss` / `sennichite` / `jishogi`) |
| `memo` | TEXT | NOT NULL DEFAULT '' | メモ（空文字列可） |
| `kif` | TEXT | NOT NULL DEFAULT '' | KIF 形式の棋譜データ |
| `shared` | BOOLEAN | NOT NULL DEFAULT FALSE | 共有が有効かどうか |
| `share_code` | VARCHAR(36) | NULL | 共有コード (36 文字の英数字)。`shared=true` の場合のみ設定 |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 作成日時 |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新日時 |

### tags テーブル

タグデータを格納する。

| カラム名 | 型 | 制約 | 説明 |
|---------|-----|------|------|
| `tid` | VARCHAR(12) | PRIMARY KEY | タグ ID (12 文字の英数字) |
| `username` | VARCHAR(255) | NOT NULL | Cognito ユーザー名 |
| `name` | VARCHAR(127) | NOT NULL | タグ名 (1〜127 文字) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 作成日時 |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新日時 |

### kifu_tags テーブル

棋譜とタグの多対多関連を管理する。

| カラム名 | 型 | 制約 | 説明 |
|---------|-----|------|------|
| `kid` | VARCHAR(12) | NOT NULL | 棋譜 ID |
| `tid` | VARCHAR(12) | NOT NULL | タグ ID |
| | | PRIMARY KEY (kid, tid) | 複合主キー |

> DynamoDB 設計で必要だったタグ名の非正規化コピー（`name`）は不要。JOIN で取得可能。

---

## DDL

### テーブル作成

```sql
CREATE TABLE kifus (
  kid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  slug        VARCHAR(1024) NOT NULL,
  side        VARCHAR(20) NOT NULL DEFAULT 'none',
  result      VARCHAR(20) NOT NULL DEFAULT 'none',
  memo        TEXT NOT NULL DEFAULT '',
  kif         TEXT NOT NULL DEFAULT '',
  shared      BOOLEAN NOT NULL DEFAULT FALSE,
  share_code  VARCHAR(36),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tags (
  tid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  name        VARCHAR(127) NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE kifu_tags (
  kid         VARCHAR(12) NOT NULL,
  tid         VARCHAR(12) NOT NULL,
  PRIMARY KEY (kid, tid)
);
```

### インデックス作成

Aurora DSQL では `CREATE INDEX ASYNC` を使用し、非ブロッキングでインデックスを作成する。

```sql
-- 棋譜: ユーザー別の更新日時降順（最近の棋譜一覧）
CREATE INDEX ASYNC idx_kifus_user_updated
  ON kifus (username, updated_at DESC);

-- 棋譜: ユーザー別の slug 一意制約（一意性チェック + エクスプローラー）
CREATE UNIQUE INDEX ASYNC idx_kifus_user_slug
  ON kifus (username, slug);

-- 棋譜: 共有コード検索
CREATE UNIQUE INDEX ASYNC idx_kifus_share_code
  ON kifus (share_code) WHERE share_code IS NOT NULL;

-- タグ: ユーザー別のタグ名一意制約
CREATE UNIQUE INDEX ASYNC idx_tags_user_name
  ON tags (username, name);

-- 棋譜-タグ関連: タグ側からの逆引き
CREATE INDEX ASYNC idx_kifu_tags_tid
  ON kifu_tags (tid);
```

---

## アクセスパターン一覧

| # | パターン | 対応 API | クエリ |
|---|---------|---------|-------|
| 1 | 最近の棋譜一覧 | `GET /kifus/recent` | `SELECT *, COUNT(*) OVER() AS total_count FROM kifus WHERE username = $1 ORDER BY updated_at DESC LIMIT 10` |
| 2 | 棋譜詳細取得 | `GET /kifus/{kid}` | `SELECT k.*, array_agg(json_build_object('tid', t.tid, 'name', t.name)) AS tags FROM kifus k LEFT JOIN kifu_tags kt ON k.kid = kt.kid LEFT JOIN tags t ON kt.tid = t.tid WHERE k.username = $1 AND k.kid = $2 GROUP BY k.kid` |
| 3 | slug 一意性チェック | `POST /kifus`, `PUT /kifus/{kid}` | UNIQUE インデックス `idx_kifus_user_slug` による制約。`INSERT`/`UPDATE` 時に DB レベルで重複排除 |
| 4 | エクスプローラー | `GET /kifus/explorer` | `SELECT slug FROM kifus WHERE username = $1 AND slug LIKE $2 \|\| '%' ORDER BY slug` |
| 5 | 共有棋譜取得 | `GET /shared/{share_code}` | `SELECT * FROM kifus WHERE share_code = $1 AND shared = TRUE` |
| 6 | タグ一覧 | `GET /tags` | `SELECT * FROM tags WHERE username = $1 ORDER BY name` |
| 7 | 棋譜のタグ取得 | 内部処理 | パターン #2 の JOIN で同時取得 |
| 8 | タグの棋譜逆引き | `GET /tags/{tid}` | `SELECT k.kid, k.slug, k.side, k.result, k.updated_at FROM kifus k JOIN kifu_tags kt ON k.kid = kt.kid WHERE kt.tid = $1 AND k.username = $2 ORDER BY k.updated_at DESC` |
| 9 | タグ名一意性チェック | `POST /tags`, `PUT /tags/{tid}` | UNIQUE インデックス `idx_tags_user_name` による制約 |
| 10 | 棋譜数カウント | `POST /kifus` | `SELECT COUNT(*) FROM kifus WHERE username = $1` |
| 11 | タグ数カウント | `POST /tags` | `SELECT COUNT(*) FROM tags WHERE username = $1` |
| 12 | 棋譜数 (total_count) | `GET /kifus/recent` | パターン #1 の `COUNT(*) OVER()` で同時取得 |

---

## データライフサイクル

### 棋譜の削除

1 トランザクション内で実行する:

1. 関連する kifu_tags レコードを削除: `DELETE FROM kifu_tags WHERE kid = $1`
2. kifus レコードを削除: `DELETE FROM kifus WHERE kid = $1 AND username = $2`

### タグの削除

1 トランザクション内で実行する:

1. 関連する kifu_tags レコードを削除: `DELETE FROM kifu_tags WHERE tid = $1`
2. tags レコードを削除: `DELETE FROM tags WHERE tid = $1 AND username = $2`

### アカウントの削除

1 トランザクション内で実行する:

1. ユーザーの全 kifu_tags を削除: `DELETE FROM kifu_tags WHERE kid IN (SELECT kid FROM kifus WHERE username = $1)`
2. ユーザーの全 kifus を削除: `DELETE FROM kifus WHERE username = $1`
3. ユーザーの全 tags を削除: `DELETE FROM tags WHERE username = $1`
4. Cognito ユーザーを削除（`AdminDeleteUser`）

> Aurora DSQL のトランザクション行数制限は 3,000 行。個人利用の棋譜管理アプリではこの上限に達する可能性は低いが、大量データの場合はバッチ分割を検討する。

### タグ名の更新時

tags テーブルの `name` を更新するだけで完了する。kifu_tags にタグ名の非正規化コピーがないため、伝播更新は不要。

```sql
UPDATE tags SET name = $1, updated_at = NOW() WHERE tid = $2 AND username = $3
```

### 棋譜のタグ関連同期（作成・更新時）

棋譜作成・更新時に `tag_ids` が指定された場合:

1. 現在の kifu_tags を取得: `SELECT tid FROM kifu_tags WHERE kid = $1`
2. 差分を計算:
   - 追加すべき関連: `INSERT INTO kifu_tags (kid, tid) VALUES ($1, $2)` を複数実行
   - 削除すべき関連: `DELETE FROM kifu_tags WHERE kid = $1 AND tid = $2` を複数実行

---

## Aurora DSQL 固有の考慮事項

### 楽観的同時実行制御（OCC）

Aurora DSQL はロックを取得せず、コミット時に競合を検出する。競合発生時はシリアライゼーションエラーが返るため、アプリケーション層でリトライロジックを実装する。個人利用のアプリでは同時書き込み競合は稀。

### トランザクション分離レベル

Repeatable Read 固定。

### DDL 制約

- DDL と DML は別トランザクションで実行する
- 1 トランザクション内の DDL は 1 文のみ

### 接続タイムアウト

データベース接続は 1 時間でタイムアウトする。Lambda のコネクション再利用時に接続切断を検知してリコネクトする必要がある。
