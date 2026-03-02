# ルーティング設計

## 概要

AWS Lambda Powertools for Python の `APIGatewayRestResolver` をエントリポイントとして使用し、`Router` クラスで機能単位にファイルを分割する。

API Gateway のステージパス `/api/v1/main` は `strip_prefixes` で除去し、Lambda 内のルート定義はプレフィックスなしで記述する。

---

## app.py のエントリポイント設計

```python
app = APIGatewayRestResolver(
    strip_prefixes=["/api/v1/main"],
    cors=CORSConfig(
        allow_origin="*",
        allow_headers=["Content-Type", "Authorization"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_credentials=False,
    ),
)
```

### Router の include

```python
app.include_router(users_router, prefix="/users")
app.include_router(kifus_router, prefix="/kifus")
app.include_router(shared_router, prefix="/shared")
app.include_router(tags_router, prefix="/tags")
```

### 例外ハンドラの登録

`@app.exception_handler` で `AppError` と未捕捉例外を一元処理する。詳細は [04_common_modules.md](04_common_modules.md) を参照。

### lambda_handler

```python
def lambda_handler(event, context):
    return app.resolve(event, context)
```

---

## ルーティング一覧

### users.py

| メソッド | Router 内パス | ハンドラ関数 | 認証 | HTTP ステータス |
|---------|-------------|------------|------|---------------|
| GET | `/me` | `get_me` | 要 | 200 |
| DELETE | `/me` | `delete_me` | 要 | 204 |

### kifus.py

| メソッド | Router 内パス | ハンドラ関数 | 認証 | HTTP ステータス |
|---------|-------------|------------|------|---------------|
| GET | `/recent` | `get_recent_kifus` | 要 | 200 |
| POST | `/` | `create_kifu` | 要 | 201 |
| GET | `/explorer` | `get_kifu_explorer` | 要 | 200 |
| GET | `/<kid>` | `get_kifu` | 要 | 200 |
| PUT | `/<kid>` | `update_kifu` | 要 | 200 |
| DELETE | `/<kid>` | `delete_kifu` | 要 | 204 |
| PUT | `/<kid>/share-code` | `regenerate_share_code` | 要 | 200 |

> `/recent` と `/explorer` は `/<kid>` より先に定義し、パスの誤マッチを防ぐ。

### shared.py

| メソッド | Router 内パス | ハンドラ関数 | 認証 | HTTP ステータス |
|---------|-------------|------------|------|---------------|
| GET | `/<share_code>` | `get_shared_kifu` | 不要 | 200 |

> 認証は API Gateway 側で `Auth: Authorizer: NONE` を設定。Lambda 内のルート定義に認証の区別はない。

### tags.py

| メソッド | Router 内パス | ハンドラ関数 | 認証 | HTTP ステータス |
|---------|-------------|------------|------|---------------|
| GET | `/` | `get_tags` | 要 | 200 |
| POST | `/` | `create_tag` | 要 | 201 |
| GET | `/<tid>` | `get_tag` | 要 | 200 |
| PUT | `/<tid>` | `update_tag` | 要 | 200 |
| DELETE | `/<tid>` | `delete_tag` | 要 | 204 |

---

## 認証の扱い

### API Gateway レベル

- Cognito Authorizer をデフォルトで全エンドポイントに適用する
- `/shared/{share_code}` のみ SAM テンプレートで `Auth: Authorizer: NONE` を指定する
- 認証に失敗したリクエストは API Gateway が 401 を返し、Lambda には到達しない

### Lambda レベル

- `app.current_event.request_context.authorizer` からクレーム情報を取得する
- 使用するクレーム: `cognito:username`（ユーザー識別子として DB の WHERE 条件に使用）
- `common/auth.py` の `get_username()` 関数で取得をラップする

---

## 各ハンドラの処理フロー

### Users

#### `get_me` — ユーザー情報取得

1. `get_username()` で username を取得
2. `app.current_event.request_context.authorizer["claims"]` から email, email_verified を取得
3. Cognito の `AdminGetUser` API で `UserCreateDate` を取得
4. `User` レスポンスを返却

#### `delete_me` — アカウント削除

1. `get_username()` で username を取得
2. リクエストボディから `password` を取得
3. `user_service.delete_account(username, password)` を呼び出し:
   - Cognito `AdminInitiateAuth` でパスワード検証
   - 失敗時は 401 エラー
   - DB からユーザーの全データを削除（kifu_tags → kifus → tags の順）
   - Cognito `AdminDeleteUser` でユーザーを削除
4. 204 を返却

### Kifus

#### `get_recent_kifus` — 最近の棋譜一覧

1. `get_username()` で username を取得
2. `kifu_service.get_recent_kifus(username)` を呼び出し:
   - `idx_kifus_user_updated` インデックスを利用し最大 10 件を取得
   - `COUNT(*) OVER()` で棋譜総数（`total_count`）を同時取得
3. `{ "kifus": [...], "total_count": N }` を返却

#### `create_kifu` — 棋譜作成

1. `get_username()` で username を取得
2. リクエストボディを取得
3. `kifu_service.create_kifu(username, body)` を呼び出し:
   - バリデーション（slug 形式、side/result enum、棋譜数上限）
   - kid, share_code を生成
   - kifus テーブルに INSERT（slug 一意性は UNIQUE インデックスで保証）
   - tag_ids が指定されていれば kifu_tags に INSERT
   - KifuDetail レスポンスを組み立て
4. 201 で返却

#### `get_kifu_explorer` — フォルダ階層での棋譜取得

1. `get_username()` で username を取得
2. クエリパラメータ `path` を取得（デフォルト: `""`）
3. `kifu_service.get_explorer(username, path)` を呼び出し:
   - `slug LIKE path || '%'` で前方一致検索
   - 結果を `path` の深さに基づいてフォルダとファイルに分類
   - フォルダ: 次の階層セグメントをグルーピングし、件数をカウント
   - ファイル: 現在の階層に直接属する棋譜
4. `ExplorerResponse` を返却

#### `get_kifu` — 棋譜詳細取得

1. `get_username()` で username を取得
2. パスパラメータ `kid` を取得
3. `kifu_service.get_kifu(username, kid)` を呼び出し:
   - kifus テーブルから SELECT（LEFT JOIN で kifu_tags + tags を結合し、タグ情報を同時取得）
   - 見つからない場合は NotFoundError
   - KifuDetail レスポンスを組み立て
4. 200 で返却

#### `update_kifu` — 棋譜更新

1. `get_username()` で username を取得
2. パスパラメータ `kid`、リクエストボディを取得
3. `kifu_service.update_kifu(username, kid, body)` を呼び出し:
   - 既存の棋譜を取得（存在チェック）
   - バリデーション（slug 形式、side/result enum）
   - kifus テーブルを UPDATE（slug 一意性は UNIQUE インデックスで保証）
   - tag_ids が指定されていれば kifu_tags の差分同期
   - shared 変更時は share_code の設定/NULL 化
   - KifuDetail レスポンスを組み立て
4. 200 で返却

#### `delete_kifu` — 棋譜削除

1. `get_username()` で username を取得
2. パスパラメータ `kid` を取得
3. `kifu_service.delete_kifu(username, kid)` を呼び出し:
   - 既存の棋譜を取得（存在チェック）
   - 1 トランザクション内で kifu_tags → kifus の順に DELETE
4. 204 を返却

#### `regenerate_share_code` — 共有コード再生成

1. `get_username()` で username を取得
2. パスパラメータ `kid` を取得
3. `kifu_service.regenerate_share_code(username, kid)` を呼び出し:
   - 既存の棋譜を取得（存在チェック）
   - 新しい share_code を生成
   - kifus テーブルの `share_code`, `updated_at` を UPDATE
4. `{ "share_code": "..." }` を返却

### Shared

#### `get_shared_kifu` — 共有棋譜取得

1. パスパラメータ `share_code` を取得
2. `kifu_service.get_shared_kifu(share_code)` を呼び出し:
   - `WHERE share_code = $1 AND shared = TRUE` で検索
   - 見つからない場合は NotFoundError
   - SharedKifuDetail レスポンスを組み立て
3. 200 で返却

> このエンドポイントは認証不要のため `get_username()` を呼ばない。

### Tags

#### `get_tags` — タグ一覧

1. `get_username()` で username を取得
2. `tag_service.get_tags(username)` を呼び出し:
   - `SELECT * FROM tags WHERE username = $1 ORDER BY name` で全タグを取得
3. `{ "tags": [...] }` を返却

#### `create_tag` — タグ作成

1. `get_username()` で username を取得
2. リクエストボディから `name` を取得
3. `tag_service.create_tag(username, name)` を呼び出し:
   - バリデーション（名前長さ、タグ数上限）
   - tid を生成
   - tags テーブルに INSERT（タグ名一意性は UNIQUE インデックスで保証）
4. 201 で返却

#### `get_tag` — タグ詳細取得

1. `get_username()` で username を取得
2. パスパラメータ `tid` を取得
3. `tag_service.get_tag(username, tid)` を呼び出し:
   - tags テーブルから SELECT
   - 見つからない場合は NotFoundError
   - JOIN で関連棋譜を 1 クエリで取得
   - TagDetail レスポンスを組み立て
4. 200 で返却

#### `update_tag` — タグ更新

1. `get_username()` で username を取得
2. パスパラメータ `tid`、リクエストボディから `name` を取得
3. `tag_service.update_tag(username, tid, name)` を呼び出し:
   - 既存のタグを取得（存在チェック）
   - バリデーション（名前長さ）
   - tags テーブルを UPDATE（タグ名一意性は UNIQUE インデックスで保証）
4. 200 で返却

#### `delete_tag` — タグ削除

1. `get_username()` で username を取得
2. パスパラメータ `tid` を取得
3. `tag_service.delete_tag(username, tid)` を呼び出し:
   - 既存のタグを取得（存在チェック）
   - 1 トランザクション内で kifu_tags → tags の順に DELETE
4. 204 を返却
