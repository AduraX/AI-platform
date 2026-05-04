from __future__ import annotations

from pathlib import Path

from python_common import AppSettings
from python_common.db import get_connection, get_conninfo


def migration_files(migrations_dir: Path | None = None) -> list[Path]:
    directory = migrations_dir or Path(__file__).resolve().parents[1] / "migrations"
    return sorted(directory.glob("*.sql"))


def _ensure_migrations_table(conninfo: str) -> None:
    """Create the schema_migrations tracking table if it doesn't exist."""
    with get_connection(conninfo) as conn, conn.cursor() as cursor:
        cursor.execute("""
                create table if not exists schema_migrations (
                    filename text primary key,
                    applied_at timestamptz not null default now()
                )
            """)


def _applied_migrations(conninfo: str) -> set[str]:
    """Return filenames of already-applied migrations."""
    with get_connection(conninfo) as conn, conn.cursor() as cursor:
        cursor.execute("select filename from schema_migrations")
        return {row[0] for row in cursor.fetchall()}


def run_migrations(*, settings: AppSettings, migrations_dir: Path | None = None) -> int:
    conninfo = get_conninfo(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )

    _ensure_migrations_table(conninfo)
    applied = _applied_migrations(conninfo)
    files = migration_files(migrations_dir)

    newly_applied = 0
    for file_path in files:
        if file_path.name in applied:
            continue

        with get_connection(conninfo) as conn, conn.cursor() as cursor:
            cursor.execute(file_path.read_text())
            cursor.execute(
                "insert into schema_migrations (filename) values (%s)",
                (file_path.name,),
            )
        newly_applied += 1

    return newly_applied


def main() -> None:
    settings = AppSettings(service_name="ingestion-service")
    applied_count = run_migrations(settings=settings)
    print(f"Applied {applied_count} new migration(s).")


if __name__ == "__main__":
    main()
