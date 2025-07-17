"""
Database operations using SQLAlchemy ORM with libsql for better performance.
Implements bulk operations and proper transaction handling.
"""

import os
from typing import List, Dict, Tuple
from sqlalchemy import create_engine, Engine, select, update, delete, func
from sqlalchemy.orm import Session, sessionmaker
from dataclasses import asdict

from generator.models import Base, Anime, ChangeLog, ManualMapping
from generator.anime_record import AnimeRecord
from generator.const import pprint
from generator.prettyprint import Platform, Status


class ChangeSet:
    """Represents a set of changes to be applied to the database."""

    def __init__(self):
        self.inserts: List[AnimeRecord] = []
        self.updates: List[Tuple[int, AnimeRecord]] = []  # (anime_id, record)
        self.deletes: List[int] = []  # anime_ids to delete

    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.inserts) + len(self.updates) + len(self.deletes)


class SQLAlchemyOperations:
    """High-performance database operations using SQLAlchemy ORM."""

    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self._create_tables()

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with libsql dialect."""
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

        return create_engine(
            connection_string,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            future=True,
        )

    def _create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)

    def detect_changes(self, new_records: List[AnimeRecord]) -> ChangeSet:
        """Detect changes between new records and existing database."""
        pprint.print(
            Platform.SYSTEM, Status.INFO, "Detecting changes in anime records..."
        )

        changeset = ChangeSet()

        with self.Session() as session:
            # Get existing records from database
            existing_records = session.execute(
                select(Anime.id, Anime.title, Anime.myanimelist, Anime.data_hash)
            ).all()

            existing_by_mal = {
                r.myanimelist: r for r in existing_records if r.myanimelist
            }
            existing_by_title = {r.title: r for r in existing_records}

            # Track processed records
            processed_mal_ids = set()
            processed_titles = set()

            # Process new records
            for record in new_records:
                # Compute hash for change detection
                record.data_hash = record.compute_hash()

                existing_record = None

                # Try to find existing record by MAL ID first
                if record.myanimelist and record.myanimelist in existing_by_mal:
                    existing_record = existing_by_mal[record.myanimelist]
                    processed_mal_ids.add(record.myanimelist)
                # Then try by title
                elif record.title in existing_by_title:
                    existing_record = existing_by_title[record.title]
                    processed_titles.add(record.title)

                if existing_record:
                    # Check if record has changed
                    if existing_record.data_hash != record.data_hash:
                        changeset.updates.append((existing_record.id, record))
                else:
                    # New record
                    changeset.inserts.append(record)
                    if record.myanimelist:
                        processed_mal_ids.add(record.myanimelist)
                    processed_titles.add(record.title)

            # Find records to delete (existed before but not in new data)
            for existing_record in existing_records:
                should_delete = False

                if existing_record.myanimelist:
                    if existing_record.myanimelist not in processed_mal_ids:
                        should_delete = True
                elif existing_record.title not in processed_titles:
                    should_delete = True

                if should_delete:
                    changeset.deletes.append(existing_record.id)

        pprint.print(
            Platform.SYSTEM,
            Status.INFO,
            f"Changes detected: {len(changeset.inserts)} inserts, {len(changeset.updates)} updates, {len(changeset.deletes)} deletes",
        )
        return changeset

    def apply_changes(self, changeset: ChangeSet) -> None:
        """Apply changes to the database using efficient bulk operations."""
        if changeset.total_changes() == 0:
            pprint.print(Platform.SYSTEM, Status.INFO, "No changes to apply")
            return

        pprint.print(
            Platform.SYSTEM,
            Status.INFO,
            f"Applying {changeset.total_changes()} changes to database...",
        )

        with self.Session() as session:
            try:
                # Apply bulk inserts
                if changeset.inserts:
                    anime_ids = self._bulk_insert_anime_records(
                        session, changeset.inserts
                    )
                    self._bulk_log_changes(session, anime_ids, "insert")

                # Apply bulk updates
                if changeset.updates:
                    self._bulk_update_anime_records(session, changeset.updates)
                    anime_ids = [anime_id for anime_id, _ in changeset.updates]
                    self._bulk_log_changes(session, anime_ids, "update")

                # Apply bulk deletes
                if changeset.deletes:
                    self._bulk_delete_anime_records(session, changeset.deletes)
                    self._bulk_log_changes(session, changeset.deletes, "delete")

                # Commit all changes
                session.commit()
                pprint.print(
                    Platform.SYSTEM, Status.PASS, "Changes applied successfully"
                )

            except Exception as e:
                session.rollback()
                pprint.print(
                    Platform.SYSTEM, Status.FAIL, f"Failed to apply changes: {e}"
                )
                raise

    def _bulk_insert_anime_records(
        self, session: Session, records: List[AnimeRecord]
    ) -> List[int]:
        """Insert multiple anime records using bulk operations."""
        if not records:
            return []

        # SQLite has a limit on the number of variables (usually 999)
        # We need to batch our inserts to avoid "too many SQL variables" error
        BATCH_SIZE = 999

        all_anime_ids = []

        # Process records in batches
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i : i + BATCH_SIZE]

            # Convert AnimeRecord objects to Anime ORM objects
            anime_objects = []
            for record in batch:
                record_dict = asdict(record)
                # Remove None values to use database defaults
                record_dict = {k: v for k, v in record_dict.items() if v is not None}
                anime_obj = Anime(**record_dict)
                anime_objects.append(anime_obj)

            # Use add_all for bulk insert
            session.add_all(anime_objects)
            session.flush()  # Ensure inserts are executed

            # Get the inserted IDs
            anime_ids = [obj.id for obj in anime_objects]
            all_anime_ids.extend(anime_ids)

            # Log progress for large batches
            if len(records) > BATCH_SIZE:
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Inserted batch {i // BATCH_SIZE + 1}/{(len(records) + BATCH_SIZE - 1) // BATCH_SIZE}",
                )

        return all_anime_ids

    def _bulk_update_anime_records(
        self, session: Session, updates: List[Tuple[int, AnimeRecord]]
    ) -> None:
        """Update multiple anime records using bulk operations."""
        if not updates:
            return

        # Batch updates to avoid "too many SQL variables" error
        BATCH_SIZE = 999

        from sqlalchemy import bindparam

        # Process updates in batches
        for i in range(0, len(updates), BATCH_SIZE):
            batch = updates[i : i + BATCH_SIZE]

            # Prepare update data
            update_values = []
            for anime_id, record in batch:
                record_dict = asdict(record)
                record_dict["id"] = anime_id  # Include the primary key for bulk update
                record_dict["b_id"] = (
                    anime_id  # Bind parameter name (different from column name)
                )
                update_values.append(record_dict)

            if update_values:
                # Build update statement with bound parameters
                stmt = update(Anime).where(Anime.id == bindparam("b_id"))

                # Execute bulk update with synchronize_session=False
                session.execute(
                    stmt,
                    update_values,
                    execution_options={"synchronize_session": False},
                )
                session.flush()

            # Log progress for large batches
            if len(updates) > BATCH_SIZE:
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Updated batch {i // BATCH_SIZE + 1}/{(len(updates) + BATCH_SIZE - 1) // BATCH_SIZE}",
                )

    def _bulk_delete_anime_records(
        self, session: Session, anime_ids: List[int]
    ) -> None:
        """Delete multiple anime records using bulk operations."""
        if not anime_ids:
            return

        # Batch deletes to avoid "too many SQL variables" error
        BATCH_SIZE = 999

        # Process deletes in batches
        for i in range(0, len(anime_ids), BATCH_SIZE):
            batch = anime_ids[i : i + BATCH_SIZE]

            # Use bulk delete with IN clause
            stmt = delete(Anime).where(Anime.id.in_(batch))
            session.execute(stmt, execution_options={"synchronize_session": False})

            # Log progress for large batches
            if len(anime_ids) > BATCH_SIZE:
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Deleted batch {i // BATCH_SIZE + 1}/{(len(anime_ids) + BATCH_SIZE - 1) // BATCH_SIZE}",
                )

    def _bulk_log_changes(
        self, session: Session, anime_ids: List[int], change_type: str
    ) -> None:
        """Log multiple changes for KV sync."""
        if not anime_ids:
            return

        # Batch change logs to avoid "too many SQL variables" error
        BATCH_SIZE = 999  # Can use larger batch for simple change logs

        # Process logs in batches
        for i in range(0, len(anime_ids), BATCH_SIZE):
            batch = anime_ids[i : i + BATCH_SIZE]

            # Create ChangeLog objects
            change_logs = [
                ChangeLog(anime_id=anime_id, change_type=change_type)
                for anime_id in batch
            ]

            # Use add_all for bulk insert
            session.add_all(change_logs)

    def get_manual_mappings(self, platform: str) -> Dict[str, str]:
        """Get manual mappings for a platform."""
        with self.Session() as session:
            mappings = session.execute(
                select(ManualMapping.platform_id, ManualMapping.platform_slug).where(
                    ManualMapping.platform == platform
                )
            ).all()

            return {
                mapping.platform_id: mapping.platform_slug or mapping.platform_id
                for mapping in mappings
            }

    def get_anime_count(self) -> int:
        """Get total count of anime records."""
        with self.Session() as session:
            count = session.execute(select(func.count(Anime.id))).scalar()
            return count or 0

    def get_pending_changes(self) -> List[ChangeLog]:
        """Get unprocessed change log entries."""
        with self.Session() as session:
            changes = (
                session.execute(
                    select(ChangeLog)
                    .where(ChangeLog.processed.is_(False))
                    .order_by(ChangeLog.created_at)
                )
                .scalars()
                .all()
            )

            return list(changes)

    def get_all_anime_records(self) -> List[Anime]:
        """Get all anime records from the database."""
        with self.Session() as session:
            records = session.execute(select(Anime)).scalars().all()
            return list(records)

    def mark_changes_processed(self, change_ids: List[int]) -> None:
        """Mark change log entries as processed."""
        if not change_ids:
            return

        # Batch the IDs to avoid "too many SQL variables" error
        BATCH_SIZE = 999  # Conservative batch size for SQLite

        with self.Session() as session:
            for i in range(0, len(change_ids), BATCH_SIZE):
                batch = change_ids[i : i + BATCH_SIZE]
                stmt = (
                    update(ChangeLog)
                    .where(ChangeLog.id.in_(batch))
                    .values(processed=True, processed_at=func.now())
                )
                session.execute(stmt, execution_options={"synchronize_session": False})
            session.commit()

    def get_platform_count(self, platform: str) -> int:
        """Get count of non-null entries for a specific platform."""
        try:
            with self.Session() as session:
                # Get the column by name
                column = getattr(Anime, platform, None)
                if column is None:
                    return 0

                # Count non-null entries
                count = (
                    session.query(func.count(column))
                    .filter(column.is_not(None))
                    .scalar()
                )
                return count or 0

        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.WARN, f"Error counting {platform}: {e}"
            )
            return 0

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()
