# テスト

## 概要

テストは DDD のレイヤー構造に沿って分類される。
内側の層ほどテストが厚く・高速になるように設計する（テストピラミッド）。

| カテゴリ | ディレクトリ | 実行環境 | 依存 | 目的 |
|---------|------------|---------|------|------|
| ドメインテスト | `domain/` | ローカル（AWS 不要） | なし（純粋 Python） | VO・エンティティ・ドメインサービスの検証 |
| アプリケーションテスト | `application/` | ローカル（AWS 不要） | InMemoryRepository | ユースケースフローの検証 |
| DSQL テスト | `dsql/` | AWS 認証必須 | デプロイ済み Aurora DSQL | DB レベルの SQL 動作・DSQL 固有挙動の検証 |

### ディレクトリ構成

```
tests/
├── pytest.ini                       # pytest 設定
├── __init__.py
├── domain/                          # ドメイン層テスト（純粋 Python、IO なし）
│   ├── __init__.py
│   ├── test_value_objects.py        # Value Object の生成・検証・等価性
│   ├── test_kifu.py                 # Kifu エンティティの振る舞い
│   ├── test_tag.py                  # Tag エンティティの振る舞い
│   └── test_services.py             # KifuExplorerService のロジック
├── application/                     # アプリケーション層テスト（InMemoryRepo 使用）
│   ├── __init__.py
│   ├── helpers/
│   │   ├── __init__.py
│   │   └── in_memory_repositories.py  # Repository ABC の dict 実装
│   ├── test_kifu_use_cases.py       # 棋譜関連 8 ユースケース
│   ├── test_tag_use_cases.py        # タグ関連 5 ユースケース
│   └── test_user_use_cases.py       # ユーザー関連 2 ユースケース
└── dsql/                            # 実 DSQL 接続が必要（生 SQL テスト）
    ├── __init__.py
    ├── conftest.py                  # DSQL 接続フィクスチャ
    ├── test_00_connectivity.py      # 疎通テスト
    ├── test_01_schema.py            # スキーマ検証
    ├── test_02_kifu_crud.py         # 棋譜 CRUD（生 SQL）
    ├── test_03_tag_crud.py          # タグ CRUD（生 SQL）
    ├── test_04_dsql_specific.py     # DSQL 固有動作（OCC, collation 等）
    ├── README.md                    # テスト項目の詳細
    └── RESULTS.md                   # テスト実行結果
```

---

## テストピラミッド

```
         /‾‾‾‾‾‾‾\
        / DSQL 統合 \         — 実 AWS 環境（Aurora DSQL）
       /‾‾‾‾‾‾‾‾‾‾‾‾‾\
      /   Application    \    — InMemoryRepository（IO なし）
     /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
    /        Domain          \  — 純粋 Python（モック不要）
   ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
```

- **Domain**: Value Object の検証ルール、エンティティの振る舞い（create, update, tag sync 等）、ドメインサービスのロジック。外部依存ゼロ、ミリ秒で完了。
- **Application**: ユースケースのフロー（上限チェック → 検証 → 永続化 → レスポンス変換）。`InMemoryRepository` を使い DB なしで高速に実行。
- **DSQL**: デプロイ済みクラスタへの生 SQL テスト。アプリケーションコードは import せず、SQL レベルでの動作保証と DSQL 固有挙動（OCC、Cコレーション等）の検証が目的。

---

## pytest 設定

### `pytest.ini`

```ini
[pytest]
pythonpath = ../src
testpaths = domain application
```

> `testpaths` はローカルで常に実行するテスト（domain, application）のみを指定。
> DSQL テストは明示的に `python -m pytest dsql/ -v` で実行する。

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

# ローカルテスト（domain + application、デフォルト）
python -m pytest -v

# ドメインテストのみ（最速）
python -m pytest domain/ -v

# アプリケーションテストのみ
python -m pytest application/ -v

# DSQL テスト（AWS 認証が必要）
AWS_PROFILE=shogi python -m pytest dsql/ -v

# 全テスト
AWS_PROFILE=shogi python -m pytest domain/ application/ dsql/ -v
```

---

## テスト命名規約

```
test_<操作>_<シナリオ>[_<期待結果>]
```

例:
- `test_create_kifu_success`
- `test_create_kifu_limit_exceeded`
- `test_slug_auto_appends_kif`
- `test_compute_tag_changes`
- `test_delete_account_wrong_password`
