# Aurora DSQL Python 接続リファレンス

本プロジェクトの実装に必要な Python 接続周りの技術仕様をまとめる。

---

## 依存パッケージ

### `requirements.txt`

```
aurora-dsql-python-connector
psycopg[binary,pool]
```

- `aurora-dsql-python-connector`: IAM 認証トークンの自動生成
- `psycopg[binary,pool]`: PostgreSQL ドライバ（v3 系）

---

## 接続の基本

### aurora_dsql_psycopg

`aurora-dsql-python-connector` パッケージが提供するドライバ別モジュール。IAM 認証トークンの生成を透過的に行う。

```python
import aurora_dsql_psycopg as dsql

conn = dsql.connect(
    host="<cluster-endpoint>",
    dbname="postgres",     # Aurora DSQL は固定
    region="ap-northeast-1"
)
```

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `host` | クラスタエンドポイント | `!GetAtt DsqlCluster.Endpoint` で取得 |
| `dbname` | `postgres` | クラスタあたり 1 つ、固定 |
| `region` | AWS リージョン | ホスト名から自動検出も可能 |

> **注意:** v0.2.x で API が変更された。旧 API（`from aurora_dsql_python_connector import DsqlConnector`）は使用不可。ドライバ別モジュール（`aurora_dsql_psycopg`, `aurora_dsql_psycopg2`, `aurora_dsql_asyncpg`）を使用する。

### 基本的なクエリ実行

```python
with conn.cursor() as cur:
    cur.execute("SELECT * FROM kifus WHERE username = %s", (username,))
    rows = cur.fetchall()

conn.commit()
```

- psycopg v3 はデフォルトで `autocommit=False`
- 変更を反映するには明示的に `conn.commit()` が必要
- 読み取り専用でも `conn.commit()` または `conn.rollback()` でトランザクションを終了するのが推奨

---

## Lambda でのコネクション管理

### `repositories/db.py` の設計

Lambda のハンドラ外（モジュールレベル）でコネクションを初期化し、ウォームスタート時に再利用する。

```python
import os
import aurora_dsql_psycopg as dsql

CLUSTER_ENDPOINT = os.environ["DSQL_CLUSTER_ENDPOINT"]
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")

_conn = None

def get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = dsql.connect(
            host=CLUSTER_ENDPOINT,
            dbname="postgres",
            region=REGION
        )
    return _conn
```

### コネクションのライフサイクル

```
コールドスタート
  → DsqlConnector() 初期化
  → get_connection() で接続確立（IAM トークン自動生成）
  → クエリ実行

ウォームスタート
  → get_connection() で既存接続を再利用（_conn.closed でなければ）
  → クエリ実行
```

### 接続の確認

IAM 認証トークンは有効期限がある。コネクションが切断された場合は `_conn.closed` が `True` になるため、`get_connection()` で自動的に再接続される。

---

## psycopg v3 の使い方

### パラメータバインディング

```python
# 位置パラメータ（%s）
cur.execute("SELECT * FROM kifus WHERE kid = %s", (kid,))

# 複数パラメータ
cur.execute(
    "SELECT * FROM kifus WHERE username = %s AND kid = %s",
    (username, kid)
)
```

> psycopg v3 は `%s` プレースホルダを使用する。`$1` 形式ではない。

### 結果の取得

```python
# 単一行
cur.execute("SELECT * FROM kifus WHERE kid = %s", (kid,))
row = cur.fetchone()  # None if not found

# 複数行
cur.execute("SELECT * FROM kifus WHERE username = %s", (username,))
rows = cur.fetchall()  # List of tuples
```

### dict 形式での取得

```python
from psycopg.rows import dict_row

with conn.cursor(row_factory=dict_row) as cur:
    cur.execute("SELECT * FROM kifus WHERE kid = %s", (kid,))
    row = cur.fetchone()
    # {"kid": "abc123", "username": "user1", "slug": "game.kif", ...}
```

### INSERT と RETURNING

```python
cur.execute(
    """
    INSERT INTO kifus (kid, username, slug, side, result, memo, kif, shared, share_code)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING *
    """,
    (kid, username, slug, side, result, memo, kif, shared, share_code)
)
row = cur.fetchone()
conn.commit()
```

### UPDATE

```python
cur.execute(
    """
    UPDATE kifus
    SET slug = %s, side = %s, result = %s, memo = %s, kif = %s, updated_at = NOW()
    WHERE kid = %s AND username = %s
    """,
    (slug, side, result, memo, kif, kid, username)
)
conn.commit()
```

### DELETE

```python
# kifu_tags → kifus の順に削除（1 トランザクション内）
cur.execute("DELETE FROM kifu_tags WHERE kid = %s", (kid,))
cur.execute("DELETE FROM kifus WHERE kid = %s AND username = %s", (kid, username))
conn.commit()
```

---

## 一意制約違反のハンドリング

UNIQUE インデックス違反時に `psycopg.errors.UniqueViolation` が発生する。これを `ConflictError` に変換する。

```python
import psycopg.errors

try:
    cur.execute("INSERT INTO kifus ...", params)
    conn.commit()
except psycopg.errors.UniqueViolation:
    conn.rollback()
    raise ConflictError("slug already exists")
```

---

## OCC リトライ

Aurora DSQL の楽観的同時実行制御による競合時は `SerializationFailure`（SQLState `40001`）が発生する。

```python
import psycopg.errors

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

> 本プロジェクトは個人利用の棋譜管理アプリであり、同一リソースへの同時書き込み競合は稀。リポジトリ層にリトライロジックを組み込むかはプロジェクトの判断による。

---

## テスト時のモック

テストでは pytest-postgresql を使い、ローカル PostgreSQL で Aurora DSQL を代替する。`repositories/db.py` の接続をテスト用接続で差し替える。

```python
import repositories.db as db_mod

@pytest.fixture
def db_connection(postgresql):
    cur = postgresql.cursor()
    cur.execute(TABLE_DDL)
    postgresql.commit()
    cur.close()
    db_mod._conn = postgresql
    yield postgresql
```

詳細は [06_testing_strategy.md](../06_testing_strategy.md) を参照。

---

## 参考リンク

- [Aurora DSQL Connector for Python](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/SECTION_program-with-dsql-connector-for-python.html)
- [psycopg 3 Documentation](https://www.psycopg.org/psycopg3/docs/)
- [aurora-dsql-connectors (GitHub)](https://github.com/awslabs/aurora-dsql-connectors/tree/main/python/connector)
