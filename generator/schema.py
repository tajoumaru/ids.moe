"""
Database schema initialization using SQLAlchemy with PostgreSQL.
Handles database creation, table management, and migrations.
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from generator.models import Base, SchemaVersion
from generator.const import DATABASE_URL


class AsyncSQLAlchemySchema:
    """Manages database schema using SQLAlchemy with PostgreSQL (async version)."""

    def __init__(self, db_url: str = DATABASE_URL):
        """Initialize with database URL."""
        self.db_url = db_url
        self.engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            pool_size=10,
            max_overflow=20,
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_database(self) -> AsyncEngine:
        """Initialize database and create tables if needed."""
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Handle migrations
        await self.migrate_schema()

        return self.engine

    async def migrate_schema(self) -> None:
        """Handle schema migrations for updates."""
        async with self.async_session() as session:
            # Get current version
            current_version = await self._get_current_version(session)

            # Apply migrations based on current version
            if current_version < 1:
                # Initial schema version
                session.add(SchemaVersion(version=1))
                await session.commit()
                current_version = 1

            if current_version < 2:
                # Add any future migrations here
                # For now, just mark as version 2
                session.add(SchemaVersion(version=2))
                await session.commit()

    async def _get_current_version(self, session: AsyncSession) -> int:
        """Get current schema version."""
        try:
            # Check if schema_version table exists (PostgreSQL syntax)
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'schema_version'"
                )
            )
            table_exists = result.fetchone()

            if not table_exists:
                return 0

            # Get max version
            result = await session.execute(
                text("SELECT MAX(version) FROM schema_version")
            )
            row = result.fetchone()

            return row[0] if row and row[0] else 0
        except Exception:
            return 0

    async def get_table_info(self, table_name: str) -> list:
        """Get table schema information for PostgreSQL."""
        async with self.async_session() as session:
            result = await session.execute(
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

    async def verify_schema(self) -> bool:
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

        async with self.async_session() as session:
            result = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            existing_tables = [row[0] for row in result.fetchall()]
            return all(table in existing_tables for table in required_tables)

    async def drop_all_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def create_all_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close database connection."""
        await self.engine.dispose()


class SQLAlchemySchema:
    """Synchronous wrapper for AsyncSQLAlchemySchema to maintain compatibility."""

    def __init__(self, db_path: str = DATABASE_URL):
        """Initialize with database path."""
        self.db_path = db_path
        self.async_schema = AsyncSQLAlchemySchema(db_path)

    def _run_async(self, coro):
        """Helper to run async coroutines in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    @property
    def engine(self):
        """Get the async engine (for compatibility)."""
        return self.async_schema.engine

    @engine.setter
    def engine(self, value):
        """Set the async engine (for compatibility)."""
        self.async_schema.engine = value

    def init_database(self) -> AsyncEngine:
        """Initialize database and create tables if needed."""
        # Run async initialization and return the async engine
        self._run_async(self.async_schema.init_database())
        # Return the async engine for better performance
        return self.async_schema.engine

    def migrate_schema(self) -> None:
        """Handle schema migrations for updates."""
        self._run_async(self.async_schema.migrate_schema())

    def get_table_info(self, table_name: str) -> list:
        """Get table schema information."""
        return self._run_async(self.async_schema.get_table_info(table_name))

    def verify_schema(self) -> bool:
        """Verify that all required tables exist."""
        return self._run_async(self.async_schema.verify_schema())

    def drop_all_tables(self) -> None:
        """Drop all database tables."""
        self._run_async(self.async_schema.drop_all_tables())

    def create_all_tables(self) -> None:
        """Create all database tables."""
        self._run_async(self.async_schema.create_all_tables())

    def close(self) -> None:
        """Close database connection."""
        self._run_async(self.async_schema.close())


def init_database(db_path: str = DATABASE_URL) -> AsyncEngine:
    """Initialize database and return async engine."""
    schema = SQLAlchemySchema(db_path)
    return schema.init_database()


async def create_tables(engine: AsyncEngine) -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate_schema(engine: AsyncEngine) -> None:
    """Apply schema migrations."""
    # Create a temporary async schema to handle migrations
    async_schema = AsyncSQLAlchemySchema()
    async_schema.engine = engine
    await async_schema.migrate_schema()
