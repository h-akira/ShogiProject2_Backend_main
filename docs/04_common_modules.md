# 共通処理

## 概要

本ドキュメントは `common/` 配下の共通モジュールの詳細設計を定義する。認証、設定管理、例外処理、バリデーション、ユーティリティの仕様を含む。

---

## 認証 (`common/auth.py`)

### `get_username(app) -> str`

Lambda Powertools の `app.current_event` から Cognito のユーザー名を取得する。

```python
def get_username(app) -> str:
    return app.current_event.request_context.authorizer.claims["cognito:username"]
```

- API Gateway の Cognito Authorizer が認証を処理するため、Lambda に到達した時点でトークンは検証済み
- `cognito:username` を DB クエリの `WHERE username = ?` 条件に使用する
- 認証不要エンドポイント（`/shared/*`）ではこの関数を呼ばない

---

## 環境変数と設定 (`common/config.py`)

| 変数名 | 型 | デフォルト | 用途 |
|--------|-----|---------|------|
| `DSQL_CLUSTER_ENDPOINT` | str | なし（必須） | Aurora DSQL クラスタエンドポイント |
| `KIFU_MAX` | int | `2000` | ユーザーあたり棋譜上限数 |
| `TAG_MAX` | int | `50` | ユーザーあたりタグ上限数 |
| `USER_POOL_ID` | str | なし（必須） | Cognito User Pool ID |
| `CLIENT_ID` | str | なし（必須） | Cognito App Client ID |

```python
import os

DSQL_CLUSTER_ENDPOINT: str = os.environ["DSQL_CLUSTER_ENDPOINT"]
KIFU_MAX: int = int(os.environ.get("KIFU_MAX", "2000"))
TAG_MAX: int = int(os.environ.get("TAG_MAX", "50"))
USER_POOL_ID: str = os.environ["USER_POOL_ID"]
CLIENT_ID: str = os.environ["CLIENT_ID"]
```

---

## カスタム例外 (`common/exceptions.py`)

### 例外クラス階層

```python
class AppError(Exception):
    """Base application error."""
    status_code: int = 500
    def __init__(self, message: str = "Internal server error"):
        self.message = message
        super().__init__(self.message)

class NotFoundError(AppError):
    status_code = 404
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)

class ValidationError(AppError):
    status_code = 400
    def __init__(self, message: str = "Validation error"):
        super().__init__(message)

class ConflictError(AppError):
    status_code = 409
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)

class LimitExceededError(AppError):
    status_code = 400
    def __init__(self, message: str = "Limit exceeded"):
        super().__init__(message)

class AuthenticationError(AppError):
    status_code = 401
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)
```

### 用途一覧

| 例外 | HTTP | 使用場面 |
|------|------|---------|
| `NotFoundError` | 404 | 棋譜・タグ・共有棋譜が見つからない |
| `ValidationError` | 400 | slug 形式不正、タグ名が空/長すぎる、必須フィールド不足、enum 値不正 |
| `ConflictError` | 409 | slug がユーザー内で重複、タグ名がユーザー内で重複 |
| `LimitExceededError` | 400 | 棋譜数が `KIFU_MAX` 超過、タグ数が `TAG_MAX` 超過 |
| `AuthenticationError` | 401 | アカウント削除時のパスワード検証失敗（Cognito `AdminInitiateAuth` のエラー） |

---

## エラーハンドリング

`app.py` で例外ハンドラを登録し、全ルートからの例外を一元処理する。

### AppError のハンドリング

```python
@app.exception_handler(AppError)
def handle_app_error(ex: AppError):
    return Response(
        status_code=ex.status_code,
        content_type="application/json",
        body=json.dumps({"message": ex.message}),
    )
```

### 未捕捉例外のハンドリング

```python
@app.exception_handler(Exception)
def handle_unexpected_error(ex: Exception):
    logger.exception("Unexpected error")
    return Response(
        status_code=500,
        content_type="application/json",
        body=json.dumps({"message": "Internal server error"}),
    )
```

### レスポンス形式

全エラーレスポンスは [openapi_main.yaml](../../../docs/openapi_main.yaml) の `Error` スキーマに準拠する。

```json
{
  "message": "エラーメッセージ"
}
```

---

## バリデーション

バリデーションはサービス層で実施する。不正な入力に対してはカスタム例外を送出する。

### バリデーション一覧

| 対象 | ルール | 例外 |
|------|-------|------|
| `slug` | 1〜255 文字 | `ValidationError` |
| `slug` | 先頭に `/` を含まない | `ValidationError` |
| `slug` | `.kif` 拡張子は自動付与（ユーザーが付与した場合は二重付与しない） | — |
| `slug` | 同一ユーザー内で一意 | `ConflictError` |
| `side` | `none`, `sente`, `gote` のいずれか | `ValidationError` |
| `result` | `none`, `win`, `loss`, `sennichite`, `jishogi` のいずれか | `ValidationError` |
| `kif` | 必須（空文字列でないこと） | `ValidationError` |
| `tag name` | 1〜127 文字 | `ValidationError` |
| `tag name` | 同一ユーザー内で一意 | `ConflictError` |
| `tag_ids` | 指定されたタグ ID が全て存在すること | `ValidationError` |
| 棋譜数 | ユーザーあたり最大 `KIFU_MAX` | `LimitExceededError` |
| タグ数 | ユーザーあたり最大 `TAG_MAX` | `LimitExceededError` |
| `password` (DELETE /users/me) | 必須 | `ValidationError` |

### slug の正規化

```python
def normalize_slug(slug: str) -> str:
    if not slug.endswith(".kif"):
        slug = slug + ".kif"
    return slug
```

---

## ID 生成 (`common/id_generator.py`)

### `generate_id(length: int = 12) -> str`

棋譜 ID (`kid`) およびタグ ID (`tid`) に使用する。英数字 (`a-z`, `A-Z`, `0-9`) のランダム文字列を生成する。

```python
import secrets
import string

_ALPHABET = string.ascii_letters + string.digits

def generate_id(length: int = 12) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
```

### `generate_share_code(length: int = 36) -> str`

共有コードに使用する。衝突確率を下げるために長めの文字列を生成する。

```python
def generate_share_code(length: int = 36) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
```

---

## 日時ユーティリティ (`common/datetime_util.py`)

### `now_iso8601() -> str`

ISO 8601 UTC 形式の現在日時文字列を返す。[openapi_main.yaml](../../../docs/openapi_main.yaml) の `date-time` 形式に対応する。

```python
from datetime import datetime, timezone

def now_iso8601() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

出力例: `2025-01-15T09:30:00Z`

---

## レスポンス生成パターン

Lambda Powertools の `APIGatewayRestResolver` は、ハンドラ関数の戻り値に応じてレスポンスを生成する。

### 200 レスポンス

dict を返すと Powertools が自動で JSON シリアライズする。

```python
@router.get("/")
def get_tags():
    tags = tag_service.get_tags(username)
    return {"tags": tags}
```

### 201 レスポンス

`Response` オブジェクトで明示的にステータスコードを指定する。

```python
@router.post("/")
def create_tag():
    tag = tag_service.create_tag(username, body)
    return Response(
        status_code=201,
        content_type="application/json",
        body=json.dumps(tag),
    )
```

### 204 レスポンス

ボディなしのレスポンスを返す。

```python
@router.delete("/<tid>")
def delete_tag(tid: str):
    tag_service.delete_tag(username, tid)
    return Response(status_code=204, body="")
```
