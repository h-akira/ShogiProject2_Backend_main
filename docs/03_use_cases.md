# ユースケース一覧

## 概要

本ドキュメントは、全14エンドポイントに対応するユースケースを定義する。
各ユースケースは Application 層のクラスとして実装され、
Command（入力DTO）を受け取り、Response（出力DTO）を返す。

親リポジトリの `docs/openapi_main.yaml` の仕様に厳密に対応する。

## DTO 設計方針

- Command（入力）と Response（出力）はすべて `@dataclass(frozen=True)` で定義
- ドメインオブジェクト（Entity/VO）は DTO に含めない（プリミティブ型のみ）
- Response の `from_entity()` 静的メソッドでエンティティから変換

## Kifu ユースケース

### UC-K1: CreateKifu（棋譜作成）

| 項目 | 内容 |
|---|---|
| エンドポイント | `POST /kifus` |
| 認証 | 必要 |
| ユースケースクラス | `CreateKifuUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class CreateKifuCommand:
    username: str
    slug: str
    side: str
    result: str
    memo: str
    kif: str
    shared: bool
    tag_ids: list[str]
```

**処理フロー:**
1. ユーザーの棋譜数を確認（KIFU_MAX チェック）
2. tag_ids が指定されていれば TagRepository で存在確認
3. Value Object を生成（Slug, Side, GameResult 等 — 検証は VO 内部で実施）
4. KifuId, ShareCode を生成
5. `Kifu.create()` でエンティティ生成
6. `KifuRepository.save()` で永続化
7. タグ関連があれば `KifuRepository.save_tag_associations()` で永続化
8. `KifuDetailResponse` を返却

**例外:**
- `LimitExceededError` — 棋譜数上限超過
- `DomainValidationError` — 入力値不正
- `ConflictError` — slug 重複

---

### UC-K2: GetKifu（棋譜取得）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /kifus/{kid}` |
| 認証 | 必要 |
| ユースケースクラス | `GetKifuUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetKifuCommand:
    username: str
    kid: str
```

**処理フロー:**
1. `KifuRepository.find_by_id_with_tags()` で棋譜取得
2. 見つからなければ `EntityNotFoundError`
3. `KifuDetailResponse` を返却

---

### UC-K3: GetRecentKifus（最近の棋譜一覧）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /kifus/recent` |
| 認証 | 必要 |
| ユースケースクラス | `GetRecentKifusUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetRecentKifusCommand:
    username: str
```

**処理フロー:**
1. `KifuRepository.find_recent()` で最新10件 + 総件数を取得
2. `RecentKifusResponse` を返却

---

### UC-K4: GetExplorer（エクスプローラー）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /kifus/explorer` |
| 認証 | 必要 |
| ユースケースクラス | `GetExplorerUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetExplorerCommand:
    username: str
    path: str
```

**処理フロー:**
1. `KifuRepository.find_by_slug_prefix()` でパスプレフィックス一致する棋譜取得
2. `KifuExplorerService.classify()` でフォルダ/ファイルに分類
3. `ExplorerResponse` を返却

---

### UC-K5: UpdateKifu（棋譜更新）

| 項目 | 内容 |
|---|---|
| エンドポイント | `PUT /kifus/{kid}` |
| 認証 | 必要 |
| ユースケースクラス | `UpdateKifuUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class UpdateKifuCommand:
    username: str
    kid: str
    slug: str
    side: str
    result: str
    memo: str
    kif: str
    shared: bool
    tag_ids: list[str] | None  # None = tag association unchanged
```

**処理フロー:**
1. `KifuRepository.find_by_id()` で既存棋譜取得
2. 見つからなければ `EntityNotFoundError`
3. tag_ids が指定されていれば TagRepository で存在確認
4. Value Object を生成（検証）
5. share_code の管理（shared 変更時の生成/破棄）
6. `kifu.update()` でエンティティ更新
7. `KifuRepository.save()` で永続化
8. タグ関連の差分を計算・保存
9. 更新後の棋譜を `KifuRepository.find_by_id_with_tags()` で再取得
10. `KifuDetailResponse` を返却

**例外:**
- `EntityNotFoundError` — 棋譜が見つからない
- `DomainValidationError` — 入力値不正
- `ConflictError` — slug 重複

---

### UC-K6: DeleteKifu（棋譜削除）

| 項目 | 内容 |
|---|---|
| エンドポイント | `DELETE /kifus/{kid}` |
| 認証 | 必要 |
| ユースケースクラス | `DeleteKifuUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class DeleteKifuCommand:
    username: str
    kid: str
```

**処理フロー:**
1. `KifuRepository.find_by_id()` で既存棋譜取得
2. 見つからなければ `EntityNotFoundError`
3. `KifuRepository.delete()` で削除（kifu_tags も含む）

---

### UC-K7: GetSharedKifu（共有棋譜取得）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /shared/{share_code}` |
| 認証 | **不要** |
| ユースケースクラス | `GetSharedKifuUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetSharedKifuCommand:
    share_code: str
```

**処理フロー:**
1. `KifuRepository.find_by_share_code()` で共有棋譜取得
2. 見つからなければ `EntityNotFoundError`
3. `SharedKifuResponse` を返却（share_code を**含まない**レスポンス）

---

### UC-K8: RegenerateShareCode（共有コード再生成）

| 項目 | 内容 |
|---|---|
| エンドポイント | `PUT /kifus/{kid}/share-code` |
| 認証 | 必要 |
| ユースケースクラス | `RegenerateShareCodeUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class RegenerateShareCodeCommand:
    username: str
    kid: str
```

**処理フロー:**
1. `KifuRepository.find_by_id()` で既存棋譜取得
2. 見つからなければ `EntityNotFoundError`
3. 新しい ShareCode を生成
4. `kifu.regenerate_share_code()` でエンティティ更新
5. `KifuRepository.save()` で永続化
6. `ShareCodeResponse` を返却

---

## Tag ユースケース

### UC-T1: CreateTag（タグ作成）

| 項目 | 内容 |
|---|---|
| エンドポイント | `POST /tags` |
| 認証 | 必要 |
| ユースケースクラス | `CreateTagUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class CreateTagCommand:
    username: str
    name: str
```

**処理フロー:**
1. ユーザーのタグ数を確認（TAG_MAX チェック）
2. TagName Value Object を生成（検証）
3. TagId を生成
4. `Tag.create()` でエンティティ生成
5. `TagRepository.save()` で永続化
6. `TagResponse` を返却

**例外:**
- `LimitExceededError` — タグ数上限超過
- `DomainValidationError` — タグ名不正
- `ConflictError` — タグ名重複

---

### UC-T2: GetTags（タグ一覧）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /tags` |
| 認証 | 必要 |
| ユースケースクラス | `GetTagsUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetTagsCommand:
    username: str
```

**処理フロー:**
1. `TagRepository.find_all()` でユーザーの全タグ取得（名前順ソート）
2. `list[TagResponse]` を返却

---

### UC-T3: GetTag（タグ詳細）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /tags/{tid}` |
| 認証 | 必要 |
| ユースケースクラス | `GetTagUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetTagCommand:
    username: str
    tid: str
```

**処理フロー:**
1. `TagRepository.find_by_id()` でタグ取得
2. 見つからなければ `EntityNotFoundError`
3. `TagRepository.find_kifus_by_tag()` で関連棋譜取得
4. `TagDetailResponse` を返却（タグ情報 + 関連棋譜リスト）

---

### UC-T4: UpdateTag（タグ更新）

| 項目 | 内容 |
|---|---|
| エンドポイント | `PUT /tags/{tid}` |
| 認証 | 必要 |
| ユースケースクラス | `UpdateTagUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class UpdateTagCommand:
    username: str
    tid: str
    name: str
```

**処理フロー:**
1. `TagRepository.find_by_id()` で既存タグ取得
2. 見つからなければ `EntityNotFoundError`
3. TagName Value Object を生成（検証）
4. `tag.rename()` でエンティティ更新
5. `TagRepository.save()` で永続化
6. `TagResponse` を返却

---

### UC-T5: DeleteTag（タグ削除）

| 項目 | 内容 |
|---|---|
| エンドポイント | `DELETE /tags/{tid}` |
| 認証 | 必要 |
| ユースケースクラス | `DeleteTagUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class DeleteTagCommand:
    username: str
    tid: str
```

**処理フロー:**
1. `TagRepository.find_by_id()` で既存タグ取得
2. 見つからなければ `EntityNotFoundError`
3. `TagRepository.delete()` で削除（kifu_tags の関連も削除）

---

## User ユースケース

### UC-U1: GetMe（ユーザー情報取得）

| 項目 | 内容 |
|---|---|
| エンドポイント | `GET /users/me` |
| 認証 | 必要 |
| ユースケースクラス | `GetMeUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class GetMeCommand:
    claims: dict  # Cognito claims from JWT
```

**処理フロー:**
1. claims から username, email, email_verified を抽出
2. CognitoClient で UserCreateDate を取得
3. `UserResponse` を返却

**備考:** User はドメインエンティティではないため、直接 CognitoClient を使用する。

---

### UC-U2: DeleteAccount（アカウント削除）

| 項目 | 内容 |
|---|---|
| エンドポイント | `DELETE /users/me` |
| 認証 | 必要 |
| ユースケースクラス | `DeleteAccountUseCase` |

**Command:**
```python
@dataclass(frozen=True)
class DeleteAccountCommand:
    username: str
    password: str
```

**処理フロー:**
1. パスワードが空でないことを確認
2. CognitoClient でパスワード検証（AdminInitiateAuth）
3. 1トランザクションで全データ削除:
   - kifu_tags → kifus → tags の順で削除
4. CognitoClient でユーザー削除

**例外:**
- `DomainValidationError` — パスワード未入力
- `AuthenticationError` — パスワード不正

---

## Response DTO 一覧

### KifuDetailResponse

```python
@dataclass(frozen=True)
class KifuDetailResponse:
    kid: str
    slug: str
    side: str
    result: str
    tags: list[dict]        # [{"tid": str, "name": str}, ...]
    memo: str
    shared: bool
    kif: str
    share_code: str | None  # shared=false のとき None（レスポンスから除外）
    created_at: str
    updated_at: str
```

### KifuSummaryResponse

```python
@dataclass(frozen=True)
class KifuSummaryResponse:
    kid: str
    slug: str
    side: str
    result: str
    tags: list[dict]
    updated_at: str
```

### RecentKifusResponse

```python
@dataclass(frozen=True)
class RecentKifusResponse:
    kifus: list[KifuSummaryResponse]
    total_count: int
```

### ExplorerResponse

```python
@dataclass(frozen=True)
class ExplorerResponse:
    path: str
    folders: list[dict]  # [{"name": str, "count": int}, ...]
    files: list[dict]    # [{"kid": str, "name": str}, ...]
```

### SharedKifuResponse

```python
@dataclass(frozen=True)
class SharedKifuResponse:
    slug: str
    side: str
    result: str
    memo: str
    kif: str
    created_at: str
    updated_at: str
```

### ShareCodeResponse

```python
@dataclass(frozen=True)
class ShareCodeResponse:
    share_code: str
```

### TagResponse

```python
@dataclass(frozen=True)
class TagResponse:
    tid: str
    name: str
    created_at: str
    updated_at: str
```

### TagDetailResponse

```python
@dataclass(frozen=True)
class TagDetailResponse:
    tid: str
    name: str
    created_at: str
    updated_at: str
    kifus: list[dict]  # [{"kid": str, "slug": str, "created_at": str, "updated_at": str}, ...]
```

### UserResponse

```python
@dataclass(frozen=True)
class UserResponse:
    username: str
    email: str
    email_verified: bool
    created_at: str
```
