"""Domain services.

Contains pure domain logic that doesn't belong to a single entity.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.kifu import Kifu


@dataclass(frozen=True)
class FolderEntry:
  """A folder in the explorer view."""
  name: str
  count: int


@dataclass(frozen=True)
class FileEntry:
  """A file in the explorer view."""
  kid: str
  name: str


@dataclass(frozen=True)
class ExplorerResult:
  """Result of the explorer classification."""
  path: str
  folders: list[FolderEntry]
  files: list[FileEntry]


class KifuExplorerService:
  """Classifies kifus into a folder/file hierarchy based on slug structure.

  This is pure domain logic with no IO dependencies.
  """

  @staticmethod
  def classify(kifus: list[Kifu], path: str) -> ExplorerResult:
    """Classify kifus at the given path into folders and files.

    Args:
        kifus: Kifus whose slug starts with the given path prefix.
        path: Current path (e.g., "year/2024/"). Empty string for root.

    Returns:
        ExplorerResult with folders and files at this level.
    """
    if path and not path.endswith("/"):
      path = path + "/"

    depth = len(path.split("/")) - 1 if path else 0

    folders: dict[str, int] = {}
    files: list[FileEntry] = []

    for kifu in kifus:
      slug = kifu.slug.value
      parts = slug.split("/")
      if len(parts) == depth + 1:
        # Direct file at this level
        files.append(FileEntry(kid=kifu.kid.value, name=parts[-1]))
      elif len(parts) > depth + 1:
        # Folder
        folder_name = parts[depth]
        folders[folder_name] = folders.get(folder_name, 0) + 1

    sorted_folders = [
      FolderEntry(name=name, count=count)
      for name, count in sorted(folders.items())
    ]

    display_path = path.rstrip("/") if path else ""

    return ExplorerResult(
      path=display_path,
      folders=sorted_folders,
      files=files,
    )
