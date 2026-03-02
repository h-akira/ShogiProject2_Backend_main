# Aurora DSQL 技術リファレンス

本プロジェクトの実装に必要な Aurora DSQL の技術仕様をまとめる。

---

## サービス概要

| 項目 | 値 |
|------|-----|
| PostgreSQL 互換バージョン | 16 |
| データベース名 | `postgres`（クラスタあたり 1 つ、固定） |
| 認証方式 | IAM 認証（パスワードレス） |
| エンドポイント | パブリック（VPC 不要） |
| 同時実行制御 | 楽観的同時実行制御（OCC） |
| トランザクション分離レベル | Repeatable Read 固定 |

---

## SQL 互換性

### 使用可能

- DDL: `CREATE TABLE`, `CREATE INDEX ASYNC`, `DROP TABLE`, `ALTER TABLE`
- DML: `SELECT`, `INSERT`, `UPDATE`, `DELETE`
- JOIN: `INNER JOIN`, `LEFT JOIN`, サブクエリ
- 集約: `COUNT()`, `array_agg()`, `json_build_object()` 等
- Window 関数: `COUNT(*) OVER()`
- CTE: `WITH` 句
- UNIQUE インデックス（一意制約として利用）
- 部分インデックス（`WHERE` 句付き）
- ビュー

### 使用不可

| 機能 | 代替手段 |
|------|---------|
| トリガー | アプリケーション層で実装 |
| PL/pgSQL（ストアドプロシージャ） | SQL 関数 or アプリケーション層 |
| 一時テーブル | CTE / サブクエリ |
| `TRUNCATE` | `DELETE FROM table_name` |
| 悲観的ロック（`SELECT ... FOR UPDATE`） | OCC + リトライ |
| 外部キー CASCADE | アプリケーション層で削除順序を管理 |

---

## トランザクション制約

| 制約 | 値 |
|------|-----|
| 1 トランザクションの最大変更行数 | 3,000 行 |
| DDL と DML の混在 | 不可（別トランザクション） |
| 1 トランザクション内の DDL | 1 文のみ |
| 接続タイムアウト | 1 時間 |
| コレーション | `C` のみ |

---

## 楽観的同時実行制御（OCC）

Aurora DSQL はロックを取得しない。トランザクションは並行して実行され、コミット時に競合が検出される。

### 競合時の挙動

- PostgreSQL のシリアライゼーションエラー（`40001`）が返る
- アプリケーション側でリトライが必要

### リトライパターン

```python
import psycopg

MAX_RETRIES = 3

def execute_with_retry(conn, query, params=None):
    for attempt in range(MAX_RETRIES):
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()
            return
        except psycopg.errors.SerializationFailure:
            conn.rollback()
            if attempt == MAX_RETRIES - 1:
                raise
```

> 本プロジェクトは個人利用の棋譜管理アプリであり、同一リソースへの同時書き込み競合は稀。

---

## インデックス作成

Aurora DSQL では `CREATE INDEX ASYNC` を使用する。通常の `CREATE INDEX` と異なり非ブロッキングで、テーブルへの書き込みを妨げない。

```sql
-- 通常の PostgreSQL
CREATE INDEX idx_name ON table_name (column);

-- Aurora DSQL
CREATE INDEX ASYNC idx_name ON table_name (column);
```

UNIQUE インデックスも同様:

```sql
CREATE UNIQUE INDEX ASYNC idx_name ON table_name (column1, column2);
```

---

## 参考リンク

- [What is Amazon Aurora DSQL?](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html)
- [SQL feature compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [Migrating from PostgreSQL to Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility-unsupported-features.html)
- [Concurrency control in Aurora DSQL](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-concurrency-control.html)
