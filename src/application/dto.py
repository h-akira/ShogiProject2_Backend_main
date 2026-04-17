"""Command and Response DTOs for the application layer.

All DTOs use primitive types only (no domain objects).
Commands represent input; Responses represent output.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# -- Kifu Commands --

@dataclass(frozen=True)
class CreateKifuCommand:
  username: str
  slug: str
  side: str
  result: str
  memo: str
  kif: str
  shared: bool
  tag_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GetKifuCommand:
  username: str
  kid: str


@dataclass(frozen=True)
class GetRecentKifusCommand:
  username: str


@dataclass(frozen=True)
class GetExplorerCommand:
  username: str
  path: str


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
  tag_ids: list[str] | None = None


@dataclass(frozen=True)
class DeleteKifuCommand:
  username: str
  kid: str


@dataclass(frozen=True)
class GetSharedKifuCommand:
  share_code: str


@dataclass(frozen=True)
class RegenerateShareCodeCommand:
  username: str
  kid: str


# -- Tag Commands --

@dataclass(frozen=True)
class CreateTagCommand:
  username: str
  name: str


@dataclass(frozen=True)
class GetTagsCommand:
  username: str


@dataclass(frozen=True)
class GetTagCommand:
  username: str
  tid: str


@dataclass(frozen=True)
class UpdateTagCommand:
  username: str
  tid: str
  name: str


@dataclass(frozen=True)
class DeleteTagCommand:
  username: str
  tid: str


# -- User Commands --

@dataclass(frozen=True)
class GetMeCommand:
  claims: dict


@dataclass(frozen=True)
class DeleteAccountCommand:
  username: str
  password: str


# -- Kifu Responses --

@dataclass(frozen=True)
class KifuDetailResponse:
  kid: str
  slug: str
  side: str
  result: str
  tags: list[dict]
  memo: str
  shared: bool
  kif: str
  share_code: str | None
  created_at: str
  updated_at: str

  def to_dict(self) -> dict:
    d = {
      "kid": self.kid,
      "slug": self.slug,
      "side": self.side,
      "result": self.result,
      "tags": self.tags,
      "memo": self.memo,
      "shared": self.shared,
      "kif": self.kif,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
    }
    if self.share_code is not None:
      d["share_code"] = self.share_code
    return d


@dataclass(frozen=True)
class KifuSummaryResponse:
  kid: str
  slug: str
  side: str
  result: str
  tags: list[dict]
  updated_at: str

  def to_dict(self) -> dict:
    return {
      "kid": self.kid,
      "slug": self.slug,
      "side": self.side,
      "result": self.result,
      "tags": self.tags,
      "updated_at": self.updated_at,
    }


@dataclass(frozen=True)
class RecentKifusResponse:
  kifus: list[KifuSummaryResponse]
  total_count: int

  def to_dict(self) -> dict:
    return {
      "kifus": [k.to_dict() for k in self.kifus],
      "total_count": self.total_count,
    }


@dataclass(frozen=True)
class ExplorerResponse:
  path: str
  folders: list[dict]
  files: list[dict]

  def to_dict(self) -> dict:
    return {
      "path": self.path,
      "folders": self.folders,
      "files": self.files,
    }


@dataclass(frozen=True)
class SharedKifuResponse:
  slug: str
  side: str
  result: str
  memo: str
  kif: str
  created_at: str
  updated_at: str

  def to_dict(self) -> dict:
    return {
      "slug": self.slug,
      "side": self.side,
      "result": self.result,
      "memo": self.memo,
      "kif": self.kif,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
    }


@dataclass(frozen=True)
class ShareCodeResponse:
  share_code: str

  def to_dict(self) -> dict:
    return {"share_code": self.share_code}


# -- Tag Responses --

@dataclass(frozen=True)
class TagResponse:
  tid: str
  name: str
  created_at: str
  updated_at: str

  def to_dict(self) -> dict:
    return {
      "tid": self.tid,
      "name": self.name,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
    }


@dataclass(frozen=True)
class TagDetailResponse:
  tid: str
  name: str
  created_at: str
  updated_at: str
  kifus: list[dict]

  def to_dict(self) -> dict:
    return {
      "tid": self.tid,
      "name": self.name,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "kifus": self.kifus,
    }


# -- User Responses --

@dataclass(frozen=True)
class UserResponse:
  username: str
  email: str
  email_verified: bool
  created_at: str

  def to_dict(self) -> dict:
    return {
      "username": self.username,
      "email": self.email,
      "email_verified": self.email_verified,
      "created_at": self.created_at,
    }
