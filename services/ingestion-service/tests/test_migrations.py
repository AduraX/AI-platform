from pathlib import Path

from ingestion_service.migrations import migration_files


def test_migration_files_are_sorted(tmp_path: Path) -> None:
    second = tmp_path / "002_second.sql"
    first = tmp_path / "001_first.sql"
    second.write_text("select 2;")
    first.write_text("select 1;")

    assert migration_files(tmp_path) == [first, second]
