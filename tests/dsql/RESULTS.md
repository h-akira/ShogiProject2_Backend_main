# DSQL テスト実行結果

## 2026-03-07 初回実行

### 環境

| 項目 | 値 |
|------|-----|
| Python | 3.13.12 |
| pytest | 9.0.2 |
| aurora-dsql-python-connector | 0.2.6 |
| psycopg | 3.3.3 |
| AWS Profile | `shogi` |
| DSQL エンドポイント | `zzttduq7k3thoasbisd4ieg75q.dsql.ap-northeast-1.on.aws` |

### 結果サマリー

```
33 passed in 6.10s
```

| Phase | ファイル | テスト数 | 結果 |
|-------|---------|---------|------|
| Phase 1: 疎通 | `test_00_connectivity.py` | 4 | ALL PASSED |
| Phase 2: スキーマ | `test_01_schema.py` | 7 | ALL PASSED |
| Phase 3: 棋譜 CRUD | `test_02_kifu_crud.py` | 9 | ALL PASSED |
| Phase 3: タグ CRUD | `test_03_tag_crud.py` | 8 | ALL PASSED |
| Phase 4: DSQL 固有 | `test_04_dsql_specific.py` | 5 | ALL PASSED |

### 全テストケース

```
tests_dsql/test_00_connectivity.py::TestConnectivity::test_connect_to_dsql PASSED
tests_dsql/test_00_connectivity.py::TestConnectivity::test_execute_select_1 PASSED
tests_dsql/test_00_connectivity.py::TestConnectivity::test_current_database PASSED
tests_dsql/test_00_connectivity.py::TestConnectivity::test_version_check PASSED
tests_dsql/test_01_schema.py::TestTableExists::test_kifus_table_exists PASSED
tests_dsql/test_01_schema.py::TestTableExists::test_tags_table_exists PASSED
tests_dsql/test_01_schema.py::TestTableExists::test_kifu_tags_table_exists PASSED
tests_dsql/test_01_schema.py::TestTableColumns::test_kifus_columns PASSED
tests_dsql/test_01_schema.py::TestTableColumns::test_tags_columns PASSED
tests_dsql/test_01_schema.py::TestTableColumns::test_kifu_tags_columns PASSED
tests_dsql/test_01_schema.py::TestIndexes::test_indexes_exist PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuInsertAndGet::test_insert_kifu PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuInsertAndGet::test_get_kifu PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuInsertAndGet::test_get_kifu_not_found PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuListAndQuery::test_list_recent_kifus PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuListAndQuery::test_query_by_slug_prefix PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuUpdate::test_update_kifu PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuUniqueConstraint::test_slug_unique_constraint PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuShared::test_shared_kifu PASSED
tests_dsql/test_02_kifu_crud.py::TestKifuDelete::test_delete_kifu PASSED
tests_dsql/test_03_tag_crud.py::TestTagInsertAndGet::test_insert_tag PASSED
tests_dsql/test_03_tag_crud.py::TestTagInsertAndGet::test_get_tag PASSED
tests_dsql/test_03_tag_crud.py::TestTagInsertAndGet::test_get_tag_not_found PASSED
tests_dsql/test_03_tag_crud.py::TestTagList::test_list_tags PASSED
tests_dsql/test_03_tag_crud.py::TestTagUniqueConstraint::test_tag_name_unique_constraint PASSED
tests_dsql/test_03_tag_crud.py::TestKifuTagAssociation::test_insert_kifu_tags PASSED
tests_dsql/test_03_tag_crud.py::TestKifuTagAssociation::test_get_kifu_with_tags PASSED
tests_dsql/test_03_tag_crud.py::TestKifuTagAssociation::test_delete_tag_cascades_kifu_tags PASSED
tests_dsql/test_04_dsql_specific.py::TestTransaction::test_transaction_commit PASSED
tests_dsql/test_04_dsql_specific.py::TestTransaction::test_transaction_rollback PASSED
tests_dsql/test_04_dsql_specific.py::TestTransaction::test_multiple_dml_in_transaction PASSED
tests_dsql/test_04_dsql_specific.py::TestDsqlFunctions::test_now_function PASSED
tests_dsql/test_04_dsql_specific.py::TestDsqlFunctions::test_collation_c PASSED
```

### 確認できた事項

| カテゴリ | 確認内容 |
|---------|---------|
| 接続・認証 | `aurora_dsql_psycopg` による IAM 認証接続が正常に動作 |
| スキーマ | マイグレーションで作成した 3 テーブル・5 インデックスがすべて存在 |
| SQL 互換性 | `INSERT RETURNING *`, `UPDATE RETURNING *`, `COUNT(*) OVER()`, `LIKE`, `LEFT JOIN`, `json_agg`, `json_build_object`, `FILTER (WHERE ...)` が DSQL 上で正しく動作 |
| 一意制約 | `UNIQUE INDEX` による一意制約が `UniqueViolation` を正しく発生 |
| トランザクション | `commit` でデータ永続化、`rollback` でデータ取り消し、1 トランザクション内の複数 DML が正常動作 |
| DSQL 固有 | `NOW()` がタイムゾーン付き、C コレーションによるソート順（大文字→小文字）を確認 |

### 初回実行時に発見・修正した問題

| 問題 | 原因 | 対処 |
|------|------|------|
| `StringDataRightTruncation` | テスト用 ID `dsql_test_k01`（13文字）が `VARCHAR(12)` を超過 | ID プレフィックスを `dt_` に変更し 12 文字以内に収めた |
| `InFailedSqlTransaction` | テスト失敗後にトランザクションがエラー状態のまま cleanup が実行された | cleanup 冒頭で `rollback()` を先行実行するように修正 |
