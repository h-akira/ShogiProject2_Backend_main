# DSQL テスト方針

## 概要

既存のローカルテスト（`tests/local/`）はモックまたはローカル PostgreSQL を使用しており、実際の Aurora DSQL には接続していない。本ドキュメントでは、デプロイ済みの Aurora DSQL クラスタに対する結合テストの方針を定める。

### 目的

1. **疎通確認**: デプロイ済み DSQL クラスタへの接続・認証が正しく動作すること
2. **マイグレーション検証**: テーブル・インデックスが正しく作成されていること
3. **CRUD 検証**: リポジトリ層の SQL が DSQL 上で正しく動作すること
4. **DSQL 固有動作の確認**: PostgreSQL との差異が問題にならないこと

---

## テスト構成

```
Backend/main/
└── tests/
    ├── pytest.ini                    # pytest 設定
    ├── local/                        # ローカル実行可能（AWS 不要）
    │   ├── conftest.py
    │   ├── test_repositories.py
    │   ├── test_services.py
    │   └── test_routes.py
    └── dsql/                         # 実 DSQL 接続が必要（AWS 認証必須）
        ├── README.md                 # テスト項目・設計の詳細
        ├── RESULTS.md                # テスト実行結果
        ├── conftest.py               # DSQL 接続フィクスチャ
        ├── test_00_connectivity.py   # Phase 1: 疎通テスト
        ├── test_01_schema.py         # Phase 2: スキーマ検証
        ├── test_02_kifu_crud.py      # Phase 3: 棋譜 CRUD テスト
        ├── test_03_tag_crud.py       # Phase 3: タグ CRUD テスト
        └── test_04_dsql_specific.py  # Phase 4: DSQL 固有動作テスト
```

### ローカルテストとの分離

- `tests/dsql/` はローカルテスト（`tests/local/`）と同じ `tests/` 配下に配置するが、サブディレクトリで明確に分離する
- `tests/pytest.ini` の `testpaths` は `local` のみを指定し、デフォルトでは DSQL テストは実行されない
- DSQL テストは `tests/` ディレクトリから明示的に `python -m pytest dsql/ -v` で実行する
- AWS 認証情報と DSQL エンドポイントが必要（CI/CD では実行しない想定）

---

## 前提条件

| 項目 | 値 |
|------|-----|
| リージョン | `ap-northeast-1` |
| スタック名 | `stack-${PROJECT}-${ENV}-backend-main` |
| DSQL エンドポイント | `${DSQL_ENDPOINT}` |
| マイグレーション | 実行済み（テーブル・インデックス作成済み） |
| 接続ライブラリ | `aurora_dsql_psycopg`（v0.2.x 準拠） |

---

## テストフェーズ

| Phase | 概要 | ファイル |
|-------|------|---------|
| Phase 1 | DSQL への接続・基本クエリ | `test_00_connectivity.py` |
| Phase 2 | テーブル・カラム・インデックスの存在確認 | `test_01_schema.py` |
| Phase 3 | 棋譜・タグの CRUD 操作 | `test_02_kifu_crud.py`, `test_03_tag_crud.py` |
| Phase 4 | トランザクション・NOW()・コレーション等の DSQL 固有動作 | `test_04_dsql_specific.py` |

各フェーズの具体的なテストケースは [tests/dsql/README.md](../tests/dsql/README.md) を参照。

---

## 実行方法

```bash
cd Backend/main/tests

# 依存パッケージのインストール
pip install -r ../requirements.txt
pip install pytest

# DSQL テストの実行
python -m pytest dsql/ -v

# 特定フェーズのみ実行
python -m pytest dsql/test_00_connectivity.py -v
```

---

## 注意事項

- DSQL テストは実際の AWS リソースに接続するため、AWS 認証情報が必要
- テストデータは専用プレフィックスで管理し、teardown で必ず削除する
- テストの並列実行は行わない（データ競合を避けるため）
- DSQL の非同期インデックス作成 (`CREATE INDEX ASYNC`) はインデックスがまだ構築中の場合、クエリのパフォーマンスに影響する可能性がある
- 本テストは開発環境 (`dev`) でのみ実行する
