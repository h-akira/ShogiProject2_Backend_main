# 集約定義

## 概要

本ドキュメントは、KifuManagement コンテキストの集約（Aggregate）を詳細に定義する。
各集約の構成要素、不変条件、Value Object の検証ルール、および振る舞い（メソッド）を記述する。

## Value Objects（値オブジェクト）

Value Object は不変（immutable）であり、等価性は値で判断される。
Python では `@dataclass(frozen=True)` で実装する。

### KifuId

| 項目 | 内容 |
|---|---|
| 型 | `str` のラッパー |
| 制約 | 12文字の英数字（a-z, A-Z, 0-9） |
| 生成 | `common.id_generator.generate_id()` で生成 |
| 用途 | Kifu エンティティの一意識別子 |

### TagId

| 項目 | 内容 |
|---|---|
| 型 | `str` のラッパー |
| 制約 | 8-12文字の英数字（a-z, A-Z, 0-9）。レガシーデータは8文字、新規は12文字 |
| 生成 | `common.id_generator.generate_id()` で生成（12文字） |
| 用途 | Tag エンティティの一意識別子 |

### Slug

| 項目 | 内容 |
|---|---|
| 型 | `str` のラッパー |
| 制約 | 1-255文字、先頭 `/` 禁止 |
| 正規化 | `.kif` で終わらない場合、自動的に `.kif` を付与 |
| 用途 | 棋譜の階層パス（エクスプローラーのフォルダ構造を形成） |

```python
# Construction example
slug = Slug("year/2024/January/game")  # -> value = "year/2024/January/game.kif"
slug = Slug("year/2024/January/game.kif")  # -> value = "year/2024/January/game.kif"
Slug("")  # -> raises DomainValidationError
Slug("/invalid")  # -> raises DomainValidationError
```

### Side

| 項目 | 内容 |
|---|---|
| 型 | `Enum` |
| 値 | `NONE = "none"`, `SENTE = "sente"`, `GOTE = "gote"` |
| 用途 | 対局者の手番 |

### GameResult

| 項目 | 内容 |
|---|---|
| 型 | `Enum` |
| 値 | `NONE = "none"`, `WIN = "win"`, `LOSS = "loss"`, `SENNICHITE = "sennichite"`, `JISHOGI = "jishogi"` |
| 用途 | 対局の結果 |

### ShareCode

| 項目 | 内容 |
|---|---|
| 型 | `str` のラッパー |
| 制約 | 36文字の英数字（a-z, A-Z, 0-9） |
| 生成 | `common.id_generator.generate_share_code()` で生成 |
| 用途 | 公開棋譜へのアクセスキー |

### TagName

| 項目 | 内容 |
|---|---|
| 型 | `str` のラッパー |
| 制約 | 1-127文字 |
| 用途 | タグの表示名 |

### Username

| 項目 | 内容 |
|---|---|
| 型 | `str` のラッパー |
| 制約 | 非空文字列 |
| 生成元 | Cognito の `cognito:username` クレーム |
| 用途 | ユーザー識別（全集約の所有者を示す） |

## Kifu 集約

### 構成

```
Kifu (集約ルート)
├── KifuId kid           # 識別子
├── Username username    # 所有者
├── Slug slug            # 階層パス
├── Side side            # 手番
├── GameResult result    # 対局結果
├── str memo             # メモ（プレーンテキスト）
├── str kif              # KIF形式データ（プレーンテキスト）
├── bool shared          # 公開フラグ
├── ShareCode? share_code # 共有コード（shared=true のとき非null）
├── Set[TagId] tag_ids   # 関連タグID群
├── str created_at       # 作成日時（ISO 8601）
└── str updated_at       # 更新日時（ISO 8601）
```

### 不変条件（Invariants）

1. `slug` は有効な Slug Value Object でなければならない
2. `side` は有効な Side Enum でなければならない
3. `result` は有効な GameResult Enum でなければならない
4. `kif` は空文字列であってはならない
5. `shared == True` のとき `share_code` は非 null でなければならない
6. `shared == False` のとき `share_code` は null でなければならない
7. 同一ユーザー内で `slug` は一意（DBレベルで強制、ドメインではConflictErrorで表現）

### ファクトリメソッド

#### `Kifu.create(...) -> Kifu`

新規棋譜を作成する。全バリデーションを実行し、不変条件を保証する。

**パラメータ:**
- `kid: KifuId` — 事前に生成された棋譜ID
- `username: Username` — 所有者
- `slug: Slug` — 階層パス（Value Object として渡される＝検証済み）
- `side: Side` — 手番
- `result: GameResult` — 対局結果
- `memo: str` — メモ
- `kif: str` — KIFデータ（空文字チェックはここで実施）
- `shared: bool` — 公開フラグ
- `share_code: ShareCode | None` — 共有コード（shared=true なら必須）
- `tag_ids: set[TagId]` — 関連タグID
- `now: str` — 現在時刻（ISO 8601）

**例外:** `DomainValidationError` — kif が空の場合

### コマンドメソッド

#### `update(slug, side, result, memo, kif, shared, share_code, now) -> None`

棋譜のメタデータを更新する。共有状態の変更に伴う share_code の管理はユースケース層で行う。

#### `regenerate_share_code(new_code: ShareCode, now: str) -> None`

共有コードを再生成する。

#### `compute_tag_changes(new_tag_ids: set[TagId]) -> tuple[set[TagId], set[TagId]]`

現在のタグ関連と新しいタグ関連を比較し、追加すべきタグIDと削除すべきタグIDを返す。

**戻り値:** `(to_add, to_remove)`

#### `apply_tag_changes(new_tag_ids: set[TagId]) -> None`

タグ関連をまるごと置き換える。

## Tag 集約

### 構成

```
Tag (集約ルート)
├── TagId tid            # 識別子
├── Username username    # 所有者
├── TagName name         # タグ名
├── str created_at       # 作成日時（ISO 8601）
└── str updated_at       # 更新日時（ISO 8601）
```

### 不変条件（Invariants）

1. `name` は有効な TagName Value Object でなければならない
2. 同一ユーザー内で `name` は一意（DBレベルで強制、ドメインでは ConflictError で表現）

### ファクトリメソッド

#### `Tag.create(...) -> Tag`

新規タグを作成する。

**パラメータ:**
- `tid: TagId` — 事前に生成されたタグID
- `username: Username` — 所有者
- `name: TagName` — タグ名（Value Object として渡される＝検証済み）
- `now: str` — 現在時刻（ISO 8601）

### コマンドメソッド

#### `rename(new_name: TagName, now: str) -> None`

タグ名を変更する。

## ドメインサービス

### KifuExplorerService

Slug の階層構造を解析し、フォルダ/ファイルのツリー構造を構築する。
純粋なロジック（IO 依存なし）であり、ドメイン層に配置する。

**メソッド:**

#### `classify(kifus: list[Kifu], path: str) -> ExplorerResult`

指定パス配下の棋譜一覧から、フォルダとファイルに分類する。

**入力:**
- `kifus` — 指定パスプレフィックスに一致する棋譜リスト
- `path` — 現在のパス（例: `year/2024/`）

**出力:** `ExplorerResult`
- `path: str` — 現在のパス
- `folders: list[FolderEntry]` — フォルダ一覧（名前、件数）
- `files: list[FileEntry]` — ファイル一覧（kid、ファイル名）

## ドメイン例外

| 例外クラス | 用途 | 対応 HTTP ステータス（プレゼンテーション層で変換） |
|---|---|---|
| `DomainValidationError` | 入力値の検証エラー | 400 |
| `EntityNotFoundError` | エンティティが見つからない | 404 |
| `ConflictError` | 一意制約違反 | 409 |
| `LimitExceededError` | リソース数上限超過 | 400 |
| `AuthenticationError` | 認証エラー（パスワード不一致等） | 403 |

これらの例外は HTTP ステータスコードを**持たない**。
ステータスコードへの変換はプレゼンテーション層の責務である。
