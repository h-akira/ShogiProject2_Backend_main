# マイグレーション方針

## 概要

Aurora DSQL のテーブル・インデックスは CloudFormation（SAM）では管理できないため、DDL を別途実行する必要がある。本ドキュメントでは、DDL のコード管理と自動実行の方針を定める。

### 方式

CodeBuild の `post_build` フェーズで `sam deploy` 後にマイグレーションスクリプトを実行する。

| 項目 | 内容 |
|------|------|
| 実行タイミング | `sam deploy` 完了後（CodeBuild `post_build`） |
| 冪等性 | `IF NOT EXISTS` で担保。何度実行しても安全 |
| DDL 制約対応 | 1 DDL / トランザクションで実行（Aurora DSQL の制約に準拠） |
| ロールバック | DDL 失敗時もスタックに影響しない（Custom Resource と異なる利点） |

---

## ファイル構成

```
Backend/main/
├── migrations/
│   ├── migrate.py                # マイグレーション実行スクリプト
│   ├── requirements.txt          # マイグレーション用依存パッケージ
│   └── sql/
│       ├── 001_create_tables.sql
│       └── 002_create_indexes.sql
```

> `migrations/` は SAM の `CodeUri: src/` に含まれないため、Lambda のデプロイパッケージには影響しない。

---

## SQL ファイル規約

### ファイル命名

```
NNN_<説明>.sql
```

- `NNN`: 3 桁の連番（`001`, `002`, ...）
- ファイル名のアルファベット順で実行される

### ステートメント区切り

Aurora DSQL は 1 トランザクション内で 1 DDL 文のみ実行可能。SQL ファイル内では `-- STATEMENT` コメントで区切り、マイグレーションスクリプトがこれを分割して個別トランザクションで実行する。

### 冪等性

全ての DDL に `IF NOT EXISTS` を付与する。これにより、マイグレーションの再実行が安全になる。

### 001_create_tables.sql

```sql
-- STATEMENT
CREATE TABLE IF NOT EXISTS kifus (
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

-- STATEMENT
CREATE TABLE IF NOT EXISTS tags (
  tid         VARCHAR(12) PRIMARY KEY,
  username    VARCHAR(255) NOT NULL,
  name        VARCHAR(127) NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- STATEMENT
CREATE TABLE IF NOT EXISTS kifu_tags (
  kid         VARCHAR(12) NOT NULL,
  tid         VARCHAR(12) NOT NULL,
  PRIMARY KEY (kid, tid)
);
```

### 002_create_indexes.sql

```sql
-- STATEMENT
CREATE INDEX ASYNC IF NOT EXISTS idx_kifus_user_updated
  ON kifus (username, updated_at);

-- STATEMENT
CREATE UNIQUE INDEX ASYNC IF NOT EXISTS idx_kifus_user_slug
  ON kifus (username, slug);

-- STATEMENT
CREATE INDEX ASYNC IF NOT EXISTS idx_kifus_share_code
  ON kifus (share_code);

-- STATEMENT
CREATE UNIQUE INDEX ASYNC IF NOT EXISTS idx_tags_user_name
  ON tags (username, name);

-- STATEMENT
CREATE INDEX ASYNC IF NOT EXISTS idx_kifu_tags_tid
  ON kifu_tags (tid);
```

> **注意:** Aurora DSQL ではインデックスキーのソート順指定（`DESC`）および部分インデックス（`WHERE` 句付き）はサポートされていない。`share_code` インデックスは `NULL` を含む非ユニークインデックスに変更している。

---

## マイグレーション実行スクリプト

### `migrations/requirements.txt`

```
aurora-dsql-python-connector
psycopg[binary]
```

### `migrations/migrate.py`

| 引数 | 必須 | デフォルト | 説明 |
|------|------|---------|------|
| `--endpoint` | はい | — | DSQL クラスタエンドポイント |
| `--region` | いいえ | `ap-northeast-1` | AWS リージョン |
| `--sql-dir` | いいえ | `./sql` | SQL ファイルのディレクトリ |

### 処理フロー

```
1. aurora_dsql_psycopg で Aurora DSQL に接続（IAM 認証トークン自動生成）
2. sql/ ディレクトリ内の *.sql ファイルをファイル名順で取得
3. 各 SQL ファイルについて:
   a. `-- STATEMENT` でファイルを分割
   b. 各ステートメントを個別トランザクションで実行
   c. 失敗時はエラーを出力して即座に停止
4. 全ステートメント完了後、接続を閉じる
```

### コード概要

```python
import aurora_dsql_psycopg as dsql

def parse_sql_file(filepath: str) -> list[str]:
    """Parse a SQL file into individual statements, split by '-- STATEMENT'."""
    with open(filepath) as f:
        content = f.read()
    return [s.strip() for s in content.split("-- STATEMENT") if s.strip()]

def run_migrations(endpoint: str, region: str, sql_dir: str) -> None:
    conn = dsql.connect(host=endpoint, dbname="postgres", region=region)

    for filepath in sorted(glob.glob(os.path.join(sql_dir, "*.sql"))):
        statements = parse_sql_file(filepath)
        for stmt in statements:
            with conn.cursor() as cur:
                cur.execute(stmt)
            conn.commit()

    conn.close()
```

> **注意:** `aurora-dsql-python-connector` v0.2.x で API が変更された。旧 API（`from aurora_dsql_python_connector import DsqlConnector`）は使用不可。ドライバ別モジュール `aurora_dsql_psycopg` を使用する。

---

## CI/CD 統合

### SAM テンプレートの Outputs 追加

マイグレーションスクリプトがクラスタエンドポイントを取得できるよう、SAM テンプレートの Outputs に追加する。

```yaml
Outputs:
  # ... 既存の ApiGatewayId, ApiGatewayStageName ...
  DsqlClusterEndpoint:
    Description: Aurora DSQL cluster endpoint for migrations
    Value: !GetAtt DsqlCluster.Endpoint
```

### CodeBuild buildspec の変更

`Backend/main/buildspec.yml` の `post_build` フェーズで `sam deploy` 後にマイグレーションを実行する。

```yaml
phases:
  install:
    runtime-versions:
      python: 3.13
  build:
    commands:
      - sam build
      - >-
        sam deploy
        --stack-name stack-sgp-${ENV}-backend-main
        --no-confirm-changeset
        --no-fail-on-empty-changeset
        --resolve-s3
        --parameter-overrides Env=$ENV
        --capabilities CAPABILITY_NAMED_IAM
        --region ${REGION}
  post_build:
    commands:
      - echo "Running database migrations..."
      - SAM_STACK_NAME=stack-sgp-${ENV}-backend-main
      - >-
        DSQL_ENDPOINT=$(aws cloudformation describe-stacks
        --stack-name ${SAM_STACK_NAME}
        --query "Stacks[0].Outputs[?OutputKey=='DsqlClusterEndpoint'].OutputValue"
        --output text
        --region ${REGION})
      - python -m pip install -r migrations/requirements.txt
      - python migrations/migrate.py --endpoint ${DSQL_ENDPOINT} --region ${REGION} --sql-dir migrations/sql
```

### CodeBuild IAM ポリシーの追加

CodeBuild ロールに Aurora DSQL への接続権限を追加する。

```yaml
- Effect: Allow
  Action:
    - dsql:DbConnectAdmin
  Resource: !Sub "arn:aws:dsql:${AWS::Region}:${AWS::AccountId}:cluster/*"
```

> `cloudformation:DescribeStacks` は既存のポリシーで許可済み。

---

## ローカル実行

開発時やデバッグ時に手動でマイグレーションを実行する場合:

```bash
cd Backend/main
pip install -r migrations/requirements.txt
python migrations/migrate.py --endpoint <cluster-endpoint> --region ap-northeast-1 --sql-dir migrations/sql
```

---

## 将来のスキーマ変更への対応

現在の設計では `IF NOT EXISTS` による冪等性で十分だが、将来 `ALTER TABLE` が必要になった場合は以下のように拡張する。

### 1. マイグレーション管理テーブルの導入

```sql
-- migrations/sql/NNN_create_schema_migrations.sql
-- STATEMENT
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename    VARCHAR(255) PRIMARY KEY,
  executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2. migrate.py の拡張

- 実行済みファイル名を `schema_migrations` テーブルに記録する
- 起動時に `schema_migrations` を参照し、未実行のファイルのみを実行する
- `IF NOT EXISTS` がない DDL（`ALTER TABLE` 等）も安全に管理できるようになる

### 3. 新しい SQL ファイルの追加例

```sql
-- migrations/sql/NNN_add_column_to_kifus.sql
-- STATEMENT
ALTER TABLE kifus ADD COLUMN IF NOT EXISTS new_column TEXT;
```

> この拡張は必要になった時点で導入すればよい。初期段階では `IF NOT EXISTS` のみで十分。
