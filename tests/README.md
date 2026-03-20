# テスト

## 概要

テストは実行環境に応じて 2 つのカテゴリに分離する。

| カテゴリ | ディレクトリ | 実行環境 | 依存 |
|---------|------------|---------|------|
| ローカルテスト | `local/` | ローカル（AWS 不要） | モック / ローカル PostgreSQL |
| DSQL テスト | `dsql/` | AWS 認証必須 | デプロイ済み Aurora DSQL |

### ディレクトリ構成

```
tests/
├── pytest.ini                       # pytest 設定
├── __init__.py
├── local/                           # ローカル実行可能（AWS 不要）
│   ├── __init__.py
│   ├── conftest.py                  # モック・ローカル PG フィクスチャ
│   ├── test_repositories.py         # リポジトリ層（ローカル PG）
│   ├── test_services.py             # サービス層（モック）
│   └── test_routes.py               # ルート層（モック）
└── dsql/                            # 実 DSQL 接続が必要
    ├── __init__.py
    ├── conftest.py                  # DSQL 接続フィクスチャ
    ├── test_00_connectivity.py      # 疎通テスト
    ├── test_01_schema.py            # スキーマ検証
    ├── test_02_kifu_crud.py         # 棋譜 CRUD
    ├── test_03_tag_crud.py          # タグ CRUD
    ├── test_04_dsql_specific.py     # DSQL 固有動作
    ├── README.md                    # テスト項目の詳細
    └── RESULTS.md                   # テスト実行結果
```

---

## 前提条件（PostgreSQL）

リポジトリ層テスト (`test_repositories.py`) はローカル PostgreSQL が必要。未インストールの場合は自動スキップされる。

```bash
# macOS (Homebrew)
brew install postgresql@16
```

> **Note:** Aurora DSQL は PostgreSQL 16 互換のため `postgresql@16` を推奨。常駐サービスの起動（`brew services start`）は不要 — `pytest-postgresql` がテスト実行時に一時インスタンスを自動で起動・終了する。

---

## pytest 設定

### `pytest.ini`

```ini
[pytest]
pythonpath = ../src
testpaths = local
```

> `testpaths` はローカルテストのみを指定。DSQL テストは明示的に `python -m pytest dsql/ -v` で実行する。

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

## 実行方法

```bash
cd Backend/main/tests

# ローカルテスト（デフォルト）
python -m pytest -v

# DSQL テスト（AWS 認証が必要）
AWS_PROFILE=shogi python -m pytest dsql/ -v

# 全テスト
AWS_PROFILE=shogi python -m pytest local/ dsql/ -v
```

---

## テスト構成

### ローカルテスト (`local/`)

| ファイル | 対象 | PostgreSQL |
|---------|------|-----------|
| `test_services.py` | サービス層（バリデーション、ビジネスロジック） | 不要（mock） |
| `test_routes.py` | ルート層（HTTP ステータス、レスポンス形式） | 不要（mock） |
| `test_repositories.py` | リポジトリ層（SQL クエリ） | **必要**（pytest-postgresql） |

リポジトリ層テストはローカルに PostgreSQL がインストールされていない場合は自動でスキップされる。

> **Aurora DSQL との差異:** OCC（楽観的同時実行制御）や `CREATE INDEX ASYNC` 等の DSQL 固有動作はローカル PostgreSQL では検証できない。通常の SQL（INSERT/SELECT/UPDATE/DELETE/JOIN）の正当性検証が目的。

### DSQL テスト (`dsql/`)

デプロイ済み Aurora DSQL クラスタに対する結合テスト。詳細は [dsql/README.md](dsql/README.md) を参照。

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
