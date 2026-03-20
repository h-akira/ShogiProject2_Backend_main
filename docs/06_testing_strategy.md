# テスト方針

## 概要

テストは実行環境に応じて 2 つのカテゴリに分離する。

| カテゴリ | ディレクトリ | 実行環境 | 依存 |
|---------|------------|---------|------|
| ローカルテスト | `tests/local/` | ローカル（AWS 不要） | モック / ローカル PostgreSQL |
| DSQL テスト | `tests/dsql/` | AWS 認証必須 | デプロイ済み Aurora DSQL |

### ディレクトリ構成

```
Backend/main/
├── tests/
│   ├── pytest.ini                    # pytest 設定
│   ├── __init__.py
│   ├── local/                        # ローカル実行可能（AWS 不要）
│   │   ├── __init__.py
│   │   ├── conftest.py               # モック・ローカル PG フィクスチャ
│   │   ├── test_repositories.py      # リポジトリ層（ローカル PG）
│   │   ├── test_services.py          # サービス層（モック）
│   │   └── test_routes.py            # ルート層（モック）
│   └── dsql/                         # 実 DSQL 接続が必要
│       ├── __init__.py
│       ├── conftest.py               # DSQL 接続フィクスチャ
│       ├── test_00_connectivity.py   # 疎通テスト
│       ├── test_01_schema.py         # スキーマ検証
│       ├── test_02_kifu_crud.py      # 棋譜 CRUD
│       ├── test_03_tag_crud.py       # タグ CRUD
│       ├── test_04_dsql_specific.py  # DSQL 固有動作
│       ├── README.md                 # テスト項目の詳細
│       └── RESULTS.md               # テスト実行結果
```

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

### `tests/pytest.ini`

```ini
[pytest]
pythonpath = ../src
testpaths = local
```

> `pytest.ini` は `tests/` ディレクトリに配置。`testpaths` はローカルテストのみを指定。DSQL テストは明示的に `python -m pytest dsql/ -v` で実行する。

---

## ローカルテスト (`tests/local/`)

### 共通フィクスチャ (`tests/local/conftest.py`)

#### 環境変数の設定

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

#### `aws_mock` フィクスチャ

moto の `mock_aws()` で Cognito をモックする。

```python
@pytest.fixture
def aws_mock():
    with mock_aws():
        yield
```

#### `db_connection` フィクスチャ

pytest-postgresql を使用してテスト用 PostgreSQL インスタンスに接続し、テーブルを作成する。テーブルスキーマは [01_database_design.md](01_database_design.md) に基づく。ローカルに PostgreSQL がない環境ではスキップされる。

#### `cognito_resources` フィクスチャ

Cognito User Pool と App Client をモックで作成する。アカウント削除テスト用。

#### `make_apigw_event` ヘルパー

Lambda Powertools の `APIGatewayRestResolver` が処理できる API Gateway プロキシイベントを生成する。

### テスト対象一覧

#### リポジトリ層テスト (`test_repositories.py`)

PostgreSQL への CRUD 操作を直接テストする。ローカル PostgreSQL が必要（なければスキップ）。

#### サービス層テスト (`test_services.py`)

ビジネスロジックとバリデーションをテストする。リポジトリ層はモックする。

#### ルート層統合テスト (`test_routes.py`)

`make_apigw_event` + `app.lambda_handler` でリクエスト/レスポンスのフローをテストする。サービス層はモックする。

---

## DSQL テスト (`tests/dsql/`)

デプロイ済み Aurora DSQL クラスタに対する結合テスト。テスト方針は [08_dsql_testing.md](08_dsql_testing.md) を参照。テスト項目の詳細は [tests/dsql/README.md](../tests/dsql/README.md) を参照。

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
cd Backend/main/tests

# ローカルテスト（デフォルト）
python -m pytest -v

# DSQL テスト（AWS 認証が必要）
AWS_PROFILE=shogi python -m pytest dsql/ -v

# 全テスト
AWS_PROFILE=shogi python -m pytest local/ dsql/ -v
```
