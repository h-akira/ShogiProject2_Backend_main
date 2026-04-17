# テスト戦略

## 概要

DDD のテストピラミッドに従い、内側の層ほどテストが厚く・高速になるように設計する。

## テストピラミッド

```
        /‾‾‾‾‾‾‾\
       / E2E/DSQL \        5%   — 実AWS環境（Aurora DSQL）
      /‾‾‾‾‾‾‾‾‾‾‾‾‾\
     / Infrastructure  \   10%  — ローカルPostgreSQL
    /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
   /  Presentation (Route)  \ 10%  — Lambda Powertools イベントモック
  /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
 /     Application (Use Case)   \ 35%  — InMemoryRepository
/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
/          Domain (Entity/VO)        \ 40%  — 純粋Python、モック不要
‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
```

## テストディレクトリ構造

```
tests/
├── domain/                      # Domain layer tests
│   ├── __init__.py
│   ├── test_value_objects.py    # VO creation, validation, equality
│   ├── test_kifu.py             # Kifu entity behavior
│   ├── test_tag.py              # Tag entity behavior
│   └── test_services.py         # KifuExplorerService logic
├── application/                 # Application layer tests
│   ├── __init__.py
│   ├── helpers/
│   │   ├── __init__.py
│   │   └── in_memory_repositories.py  # InMemory implementations of Repository ABCs
│   ├── test_kifu_use_cases.py
│   ├── test_tag_use_cases.py
│   └── test_user_use_cases.py
├── infrastructure/              # Infrastructure layer tests
│   ├── __init__.py
│   ├── conftest.py              # PostgreSQL fixtures
│   ├── test_kifu_repository.py
│   └── test_tag_repository.py
├── presentation/                # Presentation layer tests
│   ├── __init__.py
│   ├── conftest.py              # Lambda event helpers, mock container
│   └── test_routes.py
├── dsql/                        # DSQL integration tests (unchanged)
│   ├── conftest.py
│   ├── test_00_connectivity.py
│   ├── test_01_schema.py
│   ├── test_02_kifu_crud.py
│   ├── test_03_tag_crud.py
│   └── test_04_dsql_specific.py
├── __init__.py
└── pytest.ini
```

## 各テスト層の詳細

### 1. Domain Tests（ドメインテスト）

**目的:** ビジネスルールの正しさを検証
**速度:** 最速（ミリ秒）
**外部依存:** なし（純粋Python）
**モック:** 不要

#### test_value_objects.py

```python
# What to test:
# - Valid creation: Slug("year/2024/game") -> .value == "year/2024/game.kif"
# - Invalid creation: Slug("") -> DomainValidationError
# - Normalization: Slug auto-appends .kif
# - Equality: Slug("a.kif") == Slug("a.kif")
# - Enum members: Side.SENTE, GameResult.JISHOGI
# - Edge cases: Slug with max length (255), TagName with max length (127)
```

#### test_kifu.py

```python
# What to test:
# - Kifu.create() success with all valid inputs
# - Kifu.create() raises DomainValidationError when kif is empty
# - Kifu.update() changes fields correctly
# - share_code invariant: shared=True requires share_code, shared=False requires None
# - compute_tag_changes() returns correct (to_add, to_remove)
# - apply_tag_changes() replaces tag_ids entirely
# - regenerate_share_code() updates share_code and updated_at
# - Properties return correct values
```

#### test_tag.py

```python
# What to test:
# - Tag.create() success
# - Tag.rename() updates name and updated_at
```

#### test_services.py

```python
# What to test:
# - KifuExplorerService.classify() with nested folders
# - classify() with files at root level
# - classify() with empty list
# - classify() with mixed folders and files
# - Path normalization (trailing slash)
```

### 2. Application Tests（アプリケーションテスト）

**目的:** ユースケースフローの正しさを検証
**速度:** 高速（秒単位）
**外部依存:** なし
**モック:** InMemoryRepository（ABC を dict で実装）

#### InMemoryRepository パターン

```python
# tests/application/helpers/in_memory_repositories.py
class InMemoryKifuRepository(KifuRepository):
    """Dict-based in-memory implementation for testing."""
    
    def __init__(self):
        self._store: dict[str, Kifu] = {}
        self._tag_associations: dict[str, set[str]] = {}
    
    def save(self, kifu: Kifu) -> Kifu:
        self._store[kifu.kid.value] = kifu
        return kifu
    
    def find_by_id(self, username: Username, kid: KifuId) -> Kifu | None:
        kifu = self._store.get(kid.value)
        if kifu and kifu.username == username:
            return kifu
        return None
    
    # ... other methods
```

**利点:**
- DB なしで全ユースケースをテスト可能
- テストが高速（IO なし）
- リポジトリの契約（ABC）が正しく定義されているか暗黙的に検証

#### test_kifu_use_cases.py

```python
# What to test:
# - CreateKifuUseCase: success, limit exceeded, tag not found, slug conflict
# - GetKifuUseCase: success, not found
# - GetRecentKifusUseCase: success, empty result
# - GetExplorerUseCase: success with folders/files
# - UpdateKifuUseCase: success, not found, tag sync
# - DeleteKifuUseCase: success, not found
# - GetSharedKifuUseCase: success, not found
# - RegenerateShareCodeUseCase: success, not found
```

#### test_tag_use_cases.py

```python
# What to test:
# - CreateTagUseCase: success, limit exceeded, name conflict
# - GetTagsUseCase: success, empty result
# - GetTagUseCase: success, not found, with related kifus
# - UpdateTagUseCase: success, not found, name conflict
# - DeleteTagUseCase: success, not found
```

#### test_user_use_cases.py

```python
# What to test:
# - GetMeUseCase: success (CognitoClient is mocked with @patch)
# - DeleteAccountUseCase: success, wrong password, empty password
# Note: CognitoClient is an external dependency, so mock it with @patch
```

### 3. Infrastructure Tests（インフラテスト）

**目的:** SQL クエリとエンティティ変換の正しさを検証
**速度:** 中程度（ローカル PostgreSQL 起動）
**外部依存:** ローカル PostgreSQL（pytest-postgresql）
**前提:** PostgreSQL がインストールされていない環境ではスキップ

```python
# What to test:
# - save() + find_by_id() round-trip: entity → SQL → entity
# - find_recent() returns correct order and total_count
# - find_by_slug_prefix() returns correct matches
# - find_by_share_code() works correctly
# - count() returns correct count
# - delete() removes kifu and tag associations
# - UniqueViolation → ConflictError conversion
# - Tag CRUD round-trip
```

### 4. Presentation Tests（プレゼンテーションテスト）

**目的:** HTTP リクエスト/レスポンスの形式検証
**速度:** 高速
**外部依存:** なし
**モック:** Use Case をモック化

```python
# What to test:
# - Each route calls the correct use case with correct parameters
# - Response status codes (200, 201, 204)
# - Response JSON structure matches API spec
# - Exception handler maps domain exceptions to correct HTTP status
# - Authentication: username extracted from Cognito claims
```

### 5. DSQL Tests（DSQL統合テスト）

**目的:** 実際の Aurora DSQL 環境での動作検証
**速度:** 最遅（ネットワーク通信）
**外部依存:** AWS 認証情報 + DSQL クラスター
**変更:** なし（既存テストをそのまま維持）

## テスト実行コマンド

```bash
# All local tests (domain + application + presentation)
pytest tests/domain/ tests/application/ tests/presentation/ -v

# Domain tests only (fastest)
pytest tests/domain/ -v

# Application tests only
pytest tests/application/ -v

# Infrastructure tests (requires local PostgreSQL)
pytest tests/infrastructure/ -v

# DSQL tests (requires AWS credentials)
AWS_PROFILE=shogi pytest tests/dsql/ -v

# All tests
pytest -v
```

## テスト命名規約

```
test_<operation>_<scenario>[_<expected_outcome>]
```

例:
- `test_create_kifu_success`
- `test_create_kifu_limit_exceeded`
- `test_create_kifu_slug_conflict`
- `test_slug_auto_appends_kif`
- `test_slug_empty_raises_error`

## InMemoryRepository における ConflictError の扱い

InMemoryRepository は DB の UNIQUE 制約を再現する必要がある:

```python
def save(self, kifu: Kifu) -> Kifu:
    # Check slug uniqueness (simulating DB UNIQUE constraint)
    for existing in self._store.values():
        if (existing.username == kifu.username 
            and existing.slug == kifu.slug 
            and existing.kid != kifu.kid):
            raise ConflictError(f"slug '{kifu.slug.value}' already exists")
    self._store[kifu.kid.value] = kifu
    return kifu
```

これにより、アプリケーション層のテストで ConflictError のハンドリングも検証できる。
