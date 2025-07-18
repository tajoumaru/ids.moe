"""
Database schema initialization using SQLAlchemy with PostgreSQL.
Handles database creation, table management, and migrations.
"""

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import Session, sessionmaker

from generator.models import Base, SchemaVersion
from generator.const import DATABASE_URL


class SQLAlchemySchema:
    """Manages database schema using SQLAlchemy with PostgreSQL."""

    def __init__(self, db_path: str = DATABASE_URL):
        """Initialize with database path."""
        self.db_path = db_path
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with PostgreSQL."""
        return create_engine(
            self.db_path,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            pool_size=10,
            max_overflow=20,
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
            # Check if schema_version table exists (PostgreSQL syntax)
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'schema_version'"
                )
            )
            table_exists = result.fetchone()

            if not table_exists:
                return 0

            # Get max version
            result = session.execute(text("SELECT MAX(version) FROM schema_version"))
            row = result.fetchone()

            return row[0] if row and row[0] else 0
        except Exception:
            return 0

    def get_table_info(self, table_name: str) -> list:
        """Get table schema information for PostgreSQL."""
        with self.Session() as session:
            result = session.execute(
                text(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = :table_name AND table_schema = 'public'
                    ORDER BY ordinal_position
                    """
                ),
                {"table_name": table_name},
            )
            return result.fetchall()

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
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            existing_tables = [row[0] for row in result.fetchall()]
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


def init_database(db_path: str = DATABASE_URL) -> Engine:
    """Initialize database and return engine."""
    schema = SQLAlchemySchema(db_path)
    return schema.init_database()


def create_tables(engine: Engine) -> None:
    """Create all database tables."""
    Base.metadata.create_all(engine)


def migrate_schema(engine: Engine) -> None:
    """Apply schema migrations."""
    # Create a temporary schema to handle migrations
    schema = SQLAlchemySchema()
    schema.engine = engine
    schema.migrate_schema()
