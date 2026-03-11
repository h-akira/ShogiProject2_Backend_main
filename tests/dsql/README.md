# DSQL 結合テスト

Aurora DSQL クラスタに対する結合テスト。テスト方針は [docs/08_dsql_testing.md](../../docs/08_dsql_testing.md) を参照。

---

## 実行前の準備

以下の環境変数を設定すること。

| 環境変数 | 必須 | 説明 |
|---------|------|------|
| `DSQL_ENDPOINT` | **必須** | Aurora DSQL クラスタのエンドポイントホスト名 |
| `AWS_REGION` | 任意 | リージョン（デフォルト: `ap-northeast-1`） |
| `AWS_PROFILE` | 任意 | 使用する AWS プロファイル名 |

```bash
export DSQL_ENDPOINT=<your-cluster-id>.dsql.ap-northeast-1.on.aws
export AWS_PROFILE=shogi
pytest tests/dsql/
```

> **注意:** `DSQL_ENDPOINT` が未設定の場合、テストは `KeyError` で即時失敗する。

---

## テストケース一覧

### Phase 1: 疎通テスト (`test_00_connectivity.py`)

| テストケース | 検証内容 |
|------------|---------|
| `test_connect_to_dsql` | 接続オブジェクトが有効で閉じていないこと |
| `test_execute_select_1` | `SELECT 1` が正常に実行できること |
| `test_current_database` | `SELECT current_database()` が `postgres` を返すこと |
| `test_version_check` | `SHOW server_version` で PostgreSQL 16 互換であること |

### Phase 2: スキーマ検証 (`test_01_schema.py`)

| テストケース | 検証内容 |
|------------|---------|
| `test_kifus_table_exists` | `kifus` テーブルが存在すること |
| `test_tags_table_exists` | `tags` テーブルが存在すること |
| `test_kifu_tags_table_exists` | `kifu_tags` テーブルが存在すること |
| `test_kifus_columns` | `kifus` テーブルのカラム名と型が設計どおりであること |
| `test_tags_columns` | `tags` テーブルのカラム名と型が設計どおりであること |
| `test_kifu_tags_columns` | `kifu_tags` テーブルのカラム名と型が設計どおりであること |
| `test_indexes_exist` | 5 つのインデックスが作成されていること |

### Phase 3: 棋譜 CRUD (`test_02_kifu_crud.py`)

| テストケース | 検証内容 |
|------------|---------|
| `test_insert_kifu` | INSERT → RETURNING * で棋譜が作成されること |
| `test_get_kifu` | SELECT で棋譜が取得できること |
| `test_get_kifu_not_found` | 存在しない kid で None が返ること |
| `test_list_recent_kifus` | ORDER BY updated_at DESC + COUNT(*) OVER() が動作すること |
| `test_query_by_slug_prefix` | LIKE によるプレフィックス検索が動作すること |
| `test_update_kifu` | UPDATE → RETURNING * で更新されること |
| `test_slug_unique_constraint` | 同一ユーザーの slug 重複で UniqueViolation が発生すること |
| `test_shared_kifu` | share_code による取得が動作すること |
| `test_delete_kifu` | DELETE 後に SELECT で取得できないこと |

### Phase 3: タグ CRUD (`test_03_tag_crud.py`)

| テストケース | 検証内容 |
|------------|---------|
| `test_insert_tag` | INSERT → RETURNING * でタグが作成されること |
| `test_get_tag` | SELECT でタグが取得できること |
| `test_get_tag_not_found` | 存在しない tid で None が返ること |
| `test_list_tags` | ORDER BY name でタグ一覧がアルファベット順に取得できること |
| `test_tag_name_unique_constraint` | 同一ユーザーのタグ名重複で UniqueViolation が発生すること |
| `test_insert_kifu_tags` | kifu_tags への INSERT が動作すること |
| `test_get_kifu_with_tags` | LEFT JOIN + json_agg でタグ付き棋譜が取得できること |
| `test_delete_tag_cascades_kifu_tags` | kifu_tags を先に削除してからタグを削除できること（CASCADE なし） |

### Phase 4: DSQL 固有動作 (`test_04_dsql_specific.py`)

| テストケース | 検証内容 |
|------------|---------|
| `test_transaction_commit` | 明示的 commit でデータが永続化されること |
| `test_transaction_rollback` | rollback でデータが取り消されること |
| `test_multiple_dml_in_transaction` | 1 トランザクション内で複数 DML が実行できること |
| `test_now_function` | `NOW()` がタイムゾーン付きで動作すること |
| `test_collation_c` | 文字列ソートが C コレーション（大文字 < 小文字）であること |

---

## テスト用データの規約

| 項目 | 値 |
|------|-----|
| テストユーザー名 | `dsql_test_user` |
| kid/tid プレフィックス | `dt_`（VARCHAR(12) 制約内に収めるため） |
| slug プレフィックス | `dsql_test/` |

> **設計上の注意:** `kid` / `tid` は `VARCHAR(12)` のため、テスト ID は `dt_` + 最大9文字（計12文字以内）とする。

テスト終了後、上記プレフィックスを持つデータは全て削除する（`conftest.py` の teardown で実施）。

---

## conftest.py 設計

### dsql_conn フィクスチャ（session スコープ）

- `aurora_dsql_psycopg.connect()` で DSQL に接続
- `dict_row` を設定し、クエリ結果を辞書形式で取得
- テストごとに接続を張り直すとオーバーヘッドが大きいため、セッション全体で 1 コネクション共有

### cleanup フィクスチャ（autouse）

各テスト終了後にテストデータを削除する。

1. **rollback 先行実行**: テスト失敗時にトランザクションがエラー状態（`InFailedSqlTransaction`）になるため、cleanup 冒頭で `rollback()` を実行してリセットする
2. **DELETE を個別トランザクションに分割**: `kifu_tags → kifus → tags` の順に削除
3. **例外時の安全策**: DELETE 自体が失敗した場合は `rollback()` で状態をリセット

### DSQL 固有の注意点

- **CASCADE 制約なし**: DSQL は外部キー制約をサポートしないため、`kifu_tags` を先に削除してから `tags` を削除する必要がある
- **C コレーション**: 文字列ソートはバイト順（大文字が小文字より前）
