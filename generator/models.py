"""
SQLAlchemy models for anime database.
Defines ORM models for all database tables.
"""

from typing import Optional
from sqlalchemy import Integer, Text, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Anime(Base):
    """Main anime data table."""

    __tablename__ = "anime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)

    # Core platform IDs
    myanimelist: Mapped[Optional[int]] = mapped_column(Integer)
    anilist: Mapped[Optional[int]] = mapped_column(Integer)
    anidb: Mapped[Optional[int]] = mapped_column(Integer)
    kitsu: Mapped[Optional[int]] = mapped_column(Integer)

    # Additional platform IDs
    animenewsnetwork: Mapped[Optional[int]] = mapped_column(Integer)
    animeplanet: Mapped[Optional[str]] = mapped_column(Text)  # Slug, not ID
    anisearch: Mapped[Optional[int]] = mapped_column(Integer)
    annict: Mapped[Optional[int]] = mapped_column(Integer)
    imdb: Mapped[Optional[str]] = mapped_column(Text)
    livechart: Mapped[Optional[int]] = mapped_column(Integer)
    notify: Mapped[Optional[str]] = mapped_column(Text)  # Base64 ID
    otakotaku: Mapped[Optional[int]] = mapped_column(Integer)
    shikimori: Mapped[Optional[int]] = mapped_column(Integer)
    shoboi: Mapped[Optional[int]] = mapped_column(Integer)
    silveryasha: Mapped[Optional[int]] = mapped_column(Integer)
    simkl: Mapped[Optional[int]] = mapped_column(Integer)
    themoviedb: Mapped[Optional[int]] = mapped_column(Integer)

    # Kaize (has both slug and ID)
    kaize: Mapped[Optional[str]] = mapped_column(Text)
    kaize_id: Mapped[Optional[int]] = mapped_column(Integer)

    # Nautiljon (has both slug and ID)
    nautiljon: Mapped[Optional[str]] = mapped_column(Text)
    nautiljon_id: Mapped[Optional[int]] = mapped_column(Integer)

    # Trakt (complex structure)
    trakt: Mapped[Optional[int]] = mapped_column(Integer)
    trakt_type: Mapped[Optional[str]] = mapped_column(Text)
    trakt_season: Mapped[Optional[int]] = mapped_column(Integer)

    # Internal tracking
    data_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"Anime(id={self.id!r}, title={self.title!r}, myanimelist={self.myanimelist!r})"


class DownloadCache(Base):
    """File caching and hash tracking."""

    __tablename__ = "download_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    file_metadata: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"DownloadCache(id={self.id!r}, source_type={self.source_type!r}, file_path={self.file_path!r})"


class ManualMapping(Base):
    """Human-curated mappings."""

    __tablename__ = "manual_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    platform_id: Mapped[str] = mapped_column(Text, nullable=False)
    platform_slug: Mapped[Optional[str]] = mapped_column(Text)
    override_existing: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"ManualMapping(id={self.id!r}, platform={self.platform!r}, title={self.title!r})"


class UnlinkedEntry(Base):
    """Failed fuzzy matches."""

    __tablename__ = "unlinked_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    platform_id: Mapped[str] = mapped_column(Text, nullable=False)
    platform_slug: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"UnlinkedEntry(id={self.id!r}, platform={self.platform!r}, title={self.title!r})"


class ChangeLog(Base):
    """Change tracking for KV sync."""

    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anime_id: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # No foreign key for Turso compatibility
    change_type: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"ChangeLog(id={self.id!r}, anime_id={self.anime_id!r}, change_type={self.change_type!r})"


class SyncStatus(Base):
    """Pipeline execution tracking."""

    __tablename__ = "sync_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    last_sync_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_sync_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sync_type: Mapped[Optional[str]] = mapped_column(Text)
    records_processed: Mapped[Optional[int]] = mapped_column(Integer)
    records_inserted: Mapped[Optional[int]] = mapped_column(Integer)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer)
    records_deleted: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"SyncStatus(id={self.id!r}, sync_type={self.sync_type!r}, records_processed={self.records_processed!r})"


class SchemaVersion(Base):
    """Schema version tracking."""

    __tablename__ = "schema_version"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return (
            f"SchemaVersion(version={self.version!r}, applied_at={self.applied_at!r})"
        )
