"""Tests for domain services."""

from domain.kifu import Kifu
from domain.services import ExplorerResult, FileEntry, FolderEntry, KifuExplorerService
from domain.value_objects import GameResult, KifuId, Side, Slug, Username


def _make_kifu(kid_suffix: str, slug_str: str) -> Kifu:
  """Helper to create a minimal Kifu for explorer tests."""
  return Kifu.reconstitute(
    kid=KifuId(f"kid{kid_suffix:>9s}"[:12].replace(" ", "0")),
    username=Username("testuser"),
    slug=Slug(slug_str),
    side=Side.NONE,
    result=GameResult.NONE,
    memo="",
    kif="data",
    shared=False,
    share_code=None,
    tag_ids=set(),
    created_at="2024-01-01T00:00:00Z",
    updated_at="2024-01-01T00:00:00Z",
  )


class TestKifuExplorerService:
  def test_root_level_mixed(self):
    kifus = [
      _make_kifu("001", "root_file.kif"),
      _make_kifu("002", "year/2024/game1.kif"),
      _make_kifu("003", "year/2024/game2.kif"),
      _make_kifu("004", "year/2023/game1.kif"),
      _make_kifu("005", "other/game.kif"),
    ]
    result = KifuExplorerService.classify(kifus, "")

    assert result.path == ""
    assert len(result.folders) == 2
    assert FolderEntry(name="other", count=1) in result.folders
    assert FolderEntry(name="year", count=3) in result.folders
    assert len(result.files) == 1
    assert result.files[0].name == "root_file.kif"

  def test_nested_folder(self):
    kifus = [
      _make_kifu("001", "year/2024/Jan/game1.kif"),
      _make_kifu("002", "year/2024/Feb/game1.kif"),
      _make_kifu("003", "year/2024/game_at_root.kif"),
    ]
    result = KifuExplorerService.classify(kifus, "year/2024/")

    assert result.path == "year/2024"
    assert len(result.folders) == 2
    assert FolderEntry(name="Feb", count=1) in result.folders
    assert FolderEntry(name="Jan", count=1) in result.folders
    assert len(result.files) == 1
    assert result.files[0].name == "game_at_root.kif"

  def test_path_without_trailing_slash(self):
    kifus = [
      _make_kifu("001", "year/2024/game.kif"),
    ]
    result = KifuExplorerService.classify(kifus, "year/2024")

    assert result.path == "year/2024"
    assert len(result.files) == 1

  def test_empty_kifus(self):
    result = KifuExplorerService.classify([], "")
    assert result.path == ""
    assert result.folders == []
    assert result.files == []

  def test_files_only(self):
    kifus = [
      _make_kifu("001", "game1.kif"),
      _make_kifu("002", "game2.kif"),
    ]
    result = KifuExplorerService.classify(kifus, "")

    assert result.folders == []
    assert len(result.files) == 2

  def test_folders_sorted_alphabetically(self):
    kifus = [
      _make_kifu("001", "c_folder/game.kif"),
      _make_kifu("002", "a_folder/game.kif"),
      _make_kifu("003", "b_folder/game.kif"),
    ]
    result = KifuExplorerService.classify(kifus, "")

    folder_names = [f.name for f in result.folders]
    assert folder_names == ["a_folder", "b_folder", "c_folder"]
