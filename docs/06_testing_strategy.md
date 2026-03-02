# テスト方針

## 概要

pytest + pytest-postgresql を用いて、各レイヤーのテストを実施する。Aurora DSQL（PostgreSQL 互換）のテストはローカル PostgreSQL インスタンスでモックし、Cognito は moto でモックする。

---

## 依存パッケージ

### `requirements-dev.txt`

```
-r requirements.txt
pytest
pytest-postgresql
moto[cognitoidp]
```

---

## pytest 設定

### `pytest.ini`

```ini
[pytest]
pythonpath = src
testpaths = tests
```

---

## 共通フィクスチャ (`tests/conftest.py`)

### 環境変数の設定

テスト開始前に、モジュールのインポートより先に環境変数を設定する。

```python
import os

os.environ["DSQL_CLUSTER_ENDPOINT"] = "localhost"
os.environ["KIFU_MAX"] = "2000"
os.environ["TAG_MAX"] = "50"
os.environ["USER_POOL_ID"] = "ap-northeast-1_TestPool"
os.environ["CLIENT_ID"] = "test-client-id"
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
```

### `aws_mock` フィクスチャ

moto の `mock_aws()` で Cognito をモックする。

```python
@pytest.fixture
def aws_mock():
    with mock_aws():
        yield
```

### `db_connection` フィクスチャ

pytest-postgresql を使用してテスト用 PostgreSQL インスタンスに接続し、テーブルを作成する。テーブルスキーマは [01_database_design.md](01_database_design.md) に基づく。

```python
from pytest_postgresql import factories

postgresql_proc = factories.postgresql_proc()
postgresql = factories.postgresql("postgresql_proc")

TABLE_DDL = """
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

CREATE UNIQUE INDEX idx_kifus_user_slug
  ON kifus (username, slug);

CREATE INDEX idx_kifus_user_updated
  ON kifus (username, updated_at DESC);

CREATE UNIQUE INDEX idx_kifus_share_code
  ON kifus (share_code) WHERE share_code IS NOT NULL;

CREATE UNIQUE INDEX idx_tags_user_name
  ON tags (username, name);

CREATE INDEX idx_kifu_tags_tid
  ON kifu_tags (tid);
"""

@pytest.fixture
def db_connection(postgresql):
    cur = postgresql.cursor()
    cur.execute(TABLE_DDL)
    postgresql.commit()
    cur.close()

    # Reload modules to pick up test DB connection
    import importlib
    import repositories.db as db_mod
    import repositories.kifu_repository as kr
    import repositories.tag_repository as tr
    db_mod._conn = postgresql
    importlib.reload(kr)
    importlib.reload(tr)

    yield postgresql
```

### `cognito_resources` フィクスチャ

Cognito User Pool と App Client をモックで作成する。アカウント削除テスト用。

```python
@pytest.fixture
def cognito_resources(aws_mock):
    client = boto3.client("cognito-idp", region_name="ap-northeast-1")
    pool = client.create_user_pool(PoolName="test-pool")
    pool_id = pool["UserPool"]["Id"]
    app_client = client.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="test-client",
        ExplicitAuthFlows=["ADMIN_NO_SRP_AUTH"],
    )
    client_id = app_client["UserPoolClient"]["ClientId"]
    os.environ["USER_POOL_ID"] = pool_id
    os.environ["CLIENT_ID"] = client_id
    yield {"pool_id": pool_id, "client_id": client_id}
```

### `make_apigw_event` ヘルパー

Lambda Powertools の `APIGatewayRestResolver` が処理できる API Gateway プロキシイベントを生成する。

```python
def make_apigw_event(
    method: str,
    path: str,
    body: dict | None = None,
    username: str | None = None,
    query_params: dict | None = None,
    path_params: dict | None = None,
) -> dict:
    event = {
        "httpMethod": method,
        "path": path,
        "body": json.dumps(body) if body else None,
        "queryStringParameters": query_params,
        "pathParameters": path_params,
        "headers": {"Content-Type": "application/json"},
        "requestContext": {},
    }
    if username:
        event["requestContext"] = {
            "authorizer": {
                "claims": {
                    "cognito:username": username,
                    "email": f"{username}@example.com",
                    "email_verified": "true",
                },
            },
        }
    return event
```

---

## テスト対象一覧

### リポジトリ層テスト (`test_repositories.py`)

PostgreSQL への CRUD 操作を直接テストする。

#### kifu_repository

| テストケース | 検証内容 |
|------------|---------|
| `test_insert_and_get_kifu` | INSERT → SELECT で正しく取得できること |
| `test_get_kifu_not_found` | 存在しない kid で None が返ること |
| `test_list_kifus_by_latest_update` | updated_at 降順で取得できること |
| `test_list_kifus_with_limit` | LIMIT が正しく機能すること |
| `test_count_kifus` | 棋譜数カウントが正しいこと |
| `test_slug_unique_constraint` | 同一ユーザー内で slug 重複時にエラーとなること |
| `test_update_kifu` | UPDATE で属性が更新されること |
| `test_delete_kifu` | DELETE 後に SELECT で None が返ること |
| `test_query_by_slug_prefix` | LIKE による前方一致で正しくフィルタされること |
| `test_query_shared_kifu` | share_code から取得できること |
| `test_query_shared_kifu_not_found` | 存在しない share_code で None が返ること |
| `test_get_kifu_with_tags` | JOIN で棋譜とタグが同時に取得できること |
| `test_insert_tag_associations` | kifu_tags への INSERT が正しいこと |
| `test_delete_tag_associations` | kifu_tags からの DELETE が正しいこと |

#### tag_repository

| テストケース | 検証内容 |
|------------|---------|
| `test_insert_and_get_tag` | INSERT → SELECT で正しく取得できること |
| `test_get_tag_not_found` | 存在しない tid で None が返ること |
| `test_list_tags` | ユーザーの全タグが取得できること |
| `test_count_tags` | タグ数カウントが正しいこと |
| `test_tag_name_unique_constraint` | 同一ユーザー内でタグ名重複時にエラーとなること |
| `test_update_tag` | タグ名が更新されること |
| `test_delete_tag` | DELETE 後に SELECT で None が返ること |
| `test_get_kifus_by_tag` | JOIN での逆引きが正しいこと |

### サービス層テスト (`test_services.py`)

ビジネスロジックとバリデーションをテストする。`db_connection` フィクスチャを使用。

#### kifu_service

| テストケース | 検証内容 |
|------------|---------|
| `test_create_kifu_success` | 正常な作成で KifuDetail が返ること |
| `test_create_kifu_with_tags` | tag_ids 指定で kifu_tags が作成されること |
| `test_create_kifu_invalid_slug` | 不正な slug で ValidationError |
| `test_create_kifu_slug_conflict` | slug 重複で ConflictError |
| `test_create_kifu_limit_exceeded` | 上限超過で LimitExceededError |
| `test_create_kifu_invalid_side` | 不正な side で ValidationError |
| `test_get_kifu_success` | 正常取得で KifuDetail（タグ情報含む）が返ること |
| `test_get_kifu_not_found` | 存在しない kid で NotFoundError |
| `test_get_recent_kifus` | 最新 10 件と total_count が返ること |
| `test_update_kifu_success` | 正常更新で KifuDetail が返ること |
| `test_update_kifu_slug_change` | slug 変更時の一意性チェックが機能すること |
| `test_update_kifu_not_found` | 存在しない kid で NotFoundError |
| `test_delete_kifu_success` | 棋譜と関連 kifu_tags が削除されること |
| `test_delete_kifu_not_found` | 存在しない kid で NotFoundError |
| `test_get_explorer_root` | ルートのフォルダ/ファイル分類が正しいこと |
| `test_get_explorer_subfolder` | サブフォルダの内容が正しいこと |
| `test_get_shared_kifu_success` | 共有棋譜が取得できること |
| `test_get_shared_kifu_not_found` | 存在しない share_code で NotFoundError |
| `test_regenerate_share_code` | 新しい share_code が生成されること |

#### tag_service

| テストケース | 検証内容 |
|------------|---------|
| `test_create_tag_success` | 正常な作成で Tag が返ること |
| `test_create_tag_name_conflict` | タグ名重複で ConflictError |
| `test_create_tag_limit_exceeded` | 上限超過で LimitExceededError |
| `test_create_tag_invalid_name` | 空のタグ名で ValidationError |
| `test_get_tags` | 全タグのリストが返ること |
| `test_get_tag_with_kifus` | タグ詳細に関連棋譜が含まれること |
| `test_get_tag_not_found` | 存在しない tid で NotFoundError |
| `test_update_tag_success` | タグ名更新が正しいこと |
| `test_update_tag_name_conflict` | タグ名重複で ConflictError |
| `test_delete_tag_success` | タグと関連 kifu_tags が削除されること |
| `test_delete_tag_not_found` | 存在しない tid で NotFoundError |

#### user_service

| テストケース | 検証内容 |
|------------|---------|
| `test_get_me` | ユーザー情報が正しく返ること |
| `test_delete_account_success` | Cognito ユーザーと DB データが削除されること |
| `test_delete_account_wrong_password` | パスワード不正で 401 エラー |

### ルート層統合テスト (`test_routes.py`)

`make_apigw_event` + `app.lambda_handler` でエンドツーエンドのテストを行う。

| テストケース | 検証内容 |
|------------|---------|
| `test_get_me_200` | ステータス 200、User スキーマ準拠のレスポンス |
| `test_create_kifu_201` | ステータス 201、KifuDetail スキーマ準拠 |
| `test_get_recent_kifus_200` | ステータス 200、kifus 配列と total_count |
| `test_get_kifu_200` | ステータス 200、KifuDetail スキーマ準拠 |
| `test_get_kifu_404` | ステータス 404、Error スキーマ準拠 |
| `test_update_kifu_200` | ステータス 200、更新後の KifuDetail |
| `test_delete_kifu_204` | ステータス 204、ボディなし |
| `test_get_explorer_200` | ステータス 200、ExplorerResponse スキーマ準拠 |
| `test_regenerate_share_code_200` | ステータス 200、新しい share_code |
| `test_get_shared_kifu_200` | ステータス 200、SharedKifuDetail スキーマ準拠（認証なし） |
| `test_get_shared_kifu_404` | ステータス 404 |
| `test_create_tag_201` | ステータス 201、Tag スキーマ準拠 |
| `test_get_tags_200` | ステータス 200、tags 配列 |
| `test_get_tag_200` | ステータス 200、TagDetail スキーマ準拠 |
| `test_update_tag_200` | ステータス 200、更新後の Tag |
| `test_delete_tag_204` | ステータス 204、ボディなし |
| `test_create_kifu_400_invalid` | ステータス 400、バリデーションエラー |
| `test_create_kifu_409_conflict` | ステータス 409、slug 重複エラー |

---

## テスト命名規約

```
test_<対象>_<シナリオ>
```

例:
- `test_create_kifu_success`
- `test_create_kifu_slug_conflict`
- `test_delete_me_wrong_password`
- `test_get_shared_kifu_not_found`

---

## テスト実行

```bash
cd Backend/main
python -m pytest tests/ -v
```
