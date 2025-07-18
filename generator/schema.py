"""
Database schema initialization using SQLAlchemy with libsql dialect.
Handles database creation, table management, and migrations.
"""

import os
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import Session, sessionmaker

from generator.models import Base, SchemaVersion


class SQLAlchemySchema:
    """Manages database schema using SQLAlchemy."""

    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with libsql dialect."""
        # Import TURSO_AUTH_TOKEN for remote connections
        from generator.const import TURSO_AUTH_TOKEN

        # Check if the db_path is already a processed connection string
        if self.db_path.startswith("sqlite+libsql://"):
            # Already processed, use as-is
            connection_string = self.db_path
        else:
            # Create directory if it doesn't exist for local files
            if not (
                self.db_path.startswith("libsql://")
                or self.db_path.startswith("ws://")
                or self.db_path.startswith("wss://")
            ):
                os.makedirs(
                    os.path.dirname(self.db_path)
                    if os.path.dirname(self.db_path)
                    else ".",
                    exist_ok=True,
                )

            # Use libsql dialect for better performance
            if (
                self.db_path.startswith("libsql://")
                or self.db_path.startswith("ws://")
                or self.db_path.startswith("wss://")
            ):
                # Remote Turso database
                connection_string = f"sqlite+libsql://{self.db_path}"
            else:
                # Local SQLite database
                connection_string = f"sqlite+libsql:///{self.db_path}"

        # Prepare connect_args for remote connections
        connect_args = {}
        if TURSO_AUTH_TOKEN and (
            ".turso.io" in self.db_path
            or ".aws" in self.db_path
            or self.db_path.startswith("libsql://")
            or self.db_path.startswith("ws://")
            or self.db_path.startswith("wss://")
        ):
            connect_args["auth_token"] = TURSO_AUTH_TOKEN

        return create_engine(
            connection_string,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            future=True,
            connect_args=connect_args,
        )

    def init_database(self) -> Engine:
        """Initialize database and create tables if needed."""
        # Create all tables
        Base.metadata.create_all(self.engine)

        # Handle migrations
        self.migrate_schema()

        return self.engine

    def migrate_schema(self) -> None:
        """Handle schema migrations for updates."""
        with self.Session() as session:
            # Get current version
            current_version = self._get_current_version(session)

            # Apply migrations based on current version
            if current_version < 1:
                # Initial schema version
                session.add(SchemaVersion(version=1))
                session.commit()
                current_version = 1

            if current_version < 2:
                # Add any future migrations here
                # For now, just mark as version 2
                session.add(SchemaVersion(version=2))
                session.commit()

    def _get_current_version(self, session: Session) -> int:
        """Get current schema version."""
        try:
            # Check if schema_version table exists
            result = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                )
            ).fetchone()

            if not result:
                return 0

            # Get max version
            result = session.execute(
                text("SELECT MAX(version) FROM schema_version")
            ).fetchone()

            return result[0] if result and result[0] else 0
        except Exception:
            return 0

    def get_table_info(self, table_name: str) -> list:
        """Get table schema information."""
        with self.Session() as session:
            result = session.execute(
                text(f"PRAGMA table_info({table_name})")
            ).fetchall()
            return result

    def verify_schema(self) -> bool:
        """Verify that all required tables exist."""
        required_tables = [
            "anime",
            "download_cache",
            "manual_mappings",
            "unlinked_entries",
            "change_log",
            "sync_status",
            "schema_version",
        ]

        with self.Session() as session:
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()

            existing_tables = [row[0] for row in result]
            return all(table in existing_tables for table in required_tables)

    def drop_all_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(self.engine)

    def create_all_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()


def init_database(db_path: str) -> Engine:
    """Initialize database and return engine."""
    schema = SQLAlchemySchema(db_path)
    return schema.init_database()


def create_tables(engine: Engine) -> None:
    """Create all database tables."""
    Base.metadata.create_all(engine)


def migrate_schema(engine: Engine) -> None:
    """Apply schema migrations."""
    schema = SQLAlchemySchema("")
    schema.engine = engine
    schema.migrate_schema()
