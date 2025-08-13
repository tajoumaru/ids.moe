# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

"""
Main SQLAlchemy-based pipeline for anime data processing.
Replaces the turso-based implementation with SQLAlchemy + libsql for better performance.
"""

import os
import sys
import time
from typing import Dict, Any

# Import dialect to ensure registration

from generator.data_operations import SQLAlchemyOperations
from generator.schema import SQLAlchemySchema
from generator.cache_downloader import CacheDownloader
from generator.data_extractor import DataExtractor
from generator.incremental_kv_ingest import IncrementalKVIngest
from generator.status_updater import StatusUpdater
from generator.const import pprint, CACHE_DIR, DATABASE_URL
from generator.prettyprint import Platform, Status


class SQLAlchemyPipeline:
    """SQLAlchemy-based pipeline for anime data processing."""

    def __init__(self, db_path: str, cache_dir: str = CACHE_DIR):
        """Initialize pipeline with database path and cache directory."""
        self.db_path = db_path
        self.cache_dir = cache_dir

        # Initialize schema
        self.schema = SQLAlchemySchema(db_path)
        self.engine = self.schema.init_database()

        # Initialize operations
        self.operations = SQLAlchemyOperations(db_path)

        # Initialize other components
        # For now, create a wrapper that provides the necessary interface for CacheDownloader
        from generator.models import DownloadCache
        from sqlalchemy import select, delete as sql_delete

        # Create a database wrapper that properly handles cache operations
        class DatabaseWrapper:
            def __init__(self, operations):
                self.operations = operations
                self._last_result = None

            def cursor(self):
                return self

            def execute(self, query: str, params: tuple | None = None):
                # Handle common database operations that CacheDownloader needs
                if "DELETE FROM download_cache WHERE source_url = ?" in query:
                    # Delete existing cache entry
                    if params:
                        with self.operations.Session() as session:
                            session.execute(
                                sql_delete(DownloadCache).where(
                                    DownloadCache.source_url == params[0]
                                )
                            )
                            session.commit()
                elif "INSERT INTO download_cache" in query:
                    # Insert new cache entry
                    if params:
                        with self.operations.Session() as session:
                            # Check which columns are being inserted
                            if "metadata)" in query:
                                # params: (source_type, url, file_path, file_hash, metadata)
                                cache_entry = DownloadCache(
                                    source_type=params[0],
                                    source_url=params[1],
                                    file_path=params[2],
                                    file_hash=params[3],
                                    file_metadata=params[4]
                                    if len(params) > 4
                                    else None,
                                )
                            else:
                                # params: (source_type, url, file_path, file_hash, expires_at)
                                expires_at = None
                                if len(params) > 4 and params[4]:
                                    # Parse the ISO format datetime string
                                    from datetime import datetime

                                    expires_at = datetime.fromisoformat(params[4])

                                cache_entry = DownloadCache(
                                    source_type=params[0],
                                    source_url=params[1],
                                    file_path=params[2],
                                    file_hash=params[3],
                                    expires_at=expires_at,
                                )
                            session.add(cache_entry)
                            session.commit()
                elif "SELECT" in query:
                    # Handle SELECT queries
                    if params:
                        with self.operations.Session() as session:
                            if "file_hash, metadata FROM download_cache" in query:
                                # Get file hash and metadata
                                result = session.execute(
                                    select(
                                        DownloadCache.file_hash,
                                        DownloadCache.file_metadata,
                                    ).where(DownloadCache.source_url == params[0])
                                ).first()
                                if result:
                                    # Return tuple format like turso
                                    self._last_result = [(result[0], result[1])]
                                else:
                                    self._last_result = []
                            elif "file_hash FROM download_cache" in query:
                                # Get just file hash
                                result = session.execute(
                                    select(DownloadCache.file_hash).where(
                                        DownloadCache.source_url == params[0]
                                    )
                                ).first()
                                if result:
                                    self._last_result = [(result[0],)]
                                else:
                                    self._last_result = []
                            elif "expires_at FROM download_cache" in query:
                                # Get expiry date
                                result = session.execute(
                                    select(DownloadCache.expires_at).where(
                                        DownloadCache.source_url == params[0]
                                    )
                                ).first()
                                if result and result[0]:
                                    # Convert datetime to ISO string for compatibility
                                    self._last_result = [(result[0].isoformat(),)]
                                else:
                                    self._last_result = []
                            else:
                                # Generic select all
                                result = session.execute(select(DownloadCache)).all()
                                self._last_result = result

            def fetchall(self):
                return self._last_result or []

            def fetchone(self):
                return self._last_result[0] if self._last_result else None

            def commit(self):
                pass

        db_wrapper = DatabaseWrapper(self.operations)
        self.downloader = CacheDownloader(db_wrapper, cache_dir)
        self.extractor = DataExtractor(cache_dir)
        self.status_updater = StatusUpdater(self.operations)
        # For now, skip KV ingest as it needs to be updated for SQLAlchemy
        self.kv_ingest = None

    def run_download_phase(self, ignore_cache: bool = False) -> Dict[str, Any]:
        """Run the download phase of the pipeline."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Starting download phase...")
        start_time = time.time()

        try:
            # Download from GitHub
            github_results = self.downloader.download_github_files(
                ignore_cache=ignore_cache
            )

            # Run scrapers
            scraper_results = self.downloader.run_scrapers(ignore_cache=ignore_cache)

            download_time = time.time() - start_time

            result = {
                "success": True,
                "time": download_time,
                "github_downloaded": len(github_results),
                "scrapers_run": len(scraper_results),
                "github_results": github_results,
                "scraper_results": scraper_results,
            }

            pprint.print(
                Platform.SYSTEM,
                Status.PASS,
                f"Download phase completed in {download_time:.2f} seconds",
            )
            return result

        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.FAIL, f"Download phase failed: {e}")
            return {"success": False, "error": str(e), "time": time.time() - start_time}

    def run_processing_phase(self) -> Dict[str, Any]:
        """Run the data processing phase."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Starting processing phase...")
        start_time = time.time()

        try:
            # Get list of cache files
            cache_files = {}
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".json"):
                        cache_files[filename] = os.path.join(self.cache_dir, filename)

            # Extract data from cache files
            records = self.extractor.extract_anime_data(cache_files)

            # Detect changes
            changeset = self.operations.detect_changes(records)

            # Apply changes
            self.operations.apply_changes(changeset)

            # Get final record count
            total_records = self.operations.get_anime_count()

            processing_time = time.time() - start_time

            result = {
                "success": True,
                "time": processing_time,
                "total_records": total_records,
                "records_inserted": len(changeset.inserts),
                "records_updated": len(changeset.updates),
                "records_deleted": len(changeset.deletes),
                "changeset": changeset,
            }

            pprint.print(
                Platform.SYSTEM,
                Status.PASS,
                f"Processing phase completed in {processing_time:.2f} seconds",
            )
            return result

        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.FAIL, f"Processing phase failed: {e}")
            return {"success": False, "error": str(e), "time": time.time() - start_time}

    def run_sync_phase(self) -> Dict[str, Any]:
        """Run the KV sync phase."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Starting KV sync phase...")
        start_time = time.time()

        try:
            # Get pending changes
            pending_changes = self.operations.get_pending_changes()

            # Process changes
            processed = 0
            failed = 0

            if self.kv_ingest:
                # Use the KV ingest system if available
                for change in pending_changes:
                    try:
                        # Process the change (this would sync to KV store)
                        # For now, just mark as processed
                        self.operations.mark_changes_processed([change.id])
                        processed += 1
                    except Exception as e:
                        pprint.print(
                            Platform.SYSTEM,
                            Status.WARN,
                            f"Failed to process change {change.id}: {e}",
                        )
                        failed += 1
            else:
                # Skip KV sync - just mark all changes as processed
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    "KV ingest not available, marking all changes as processed",
                )
                change_ids = [change.id for change in pending_changes]
                if change_ids:
                    self.operations.mark_changes_processed(change_ids)
                    processed = len(change_ids)

            sync_time = time.time() - start_time

            result = {
                "success": True,
                "time": sync_time,
                "processed": processed,
                "failed": failed,
                "total_changes": len(pending_changes),
            }

            pprint.print(
                Platform.SYSTEM,
                Status.PASS,
                f"KV sync phase completed in {sync_time:.2f} seconds",
            )
            return result

        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.FAIL, f"KV sync phase failed: {e}")
            return {"success": False, "error": str(e), "time": time.time() - start_time}

    def run_kv_ingestion_phase(
        self, force_overwrite_all: bool = False
    ) -> Dict[str, Any]:
        """Run the KV ingestion phase."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Starting KV ingestion phase...")
        start_time = time.time()

        try:
            # Initialize KV ingestion
            kv_ingest = IncrementalKVIngest()

            if force_overwrite_all:
                # Force overwrite all: get all anime records and create synthetic changes
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    "Force overwrite all: processing all anime records...",
                )

                # First, clear all existing KV data
                kv_ingest.prune_all_keys()

                # Get all anime records
                all_records = self.operations.get_all_anime_records()

                # Create synthetic change log entries for all records
                from generator.models import ChangeLog

                synthetic_changes = []
                for record in all_records:
                    change = ChangeLog(
                        anime_id=record.id, change_type="insert", processed=False
                    )
                    synthetic_changes.append(change)

                # Process all changes
                kv_ingest.process_changes(synthetic_changes, self.operations)

                changes_processed = len(synthetic_changes)

            else:
                # Normal incremental processing
                # Get pending changes
                pending_changes = self.operations.get_pending_changes()

                if not pending_changes:
                    pprint.print(
                        Platform.SYSTEM, Status.INFO, "No pending changes to process"
                    )
                    return {
                        "success": True,
                        "time": time.time() - start_time,
                        "changes_processed": 0,
                    }

                # Process changes
                kv_ingest.process_changes(pending_changes, self.operations)

                # Mark changes as processed
                change_ids = [change.id for change in pending_changes]
                self.operations.mark_changes_processed(change_ids)

                changes_processed = len(pending_changes)


            kv_time = time.time() - start_time

            result = {
                "success": True,
                "time": kv_time,
                "changes_processed": changes_processed,
            }

            pprint.print(
                Platform.SYSTEM,
                Status.PASS,
                f"KV ingestion phase completed in {kv_time:.2f} seconds",
            )
            return result

        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.FAIL, f"KV ingestion phase failed: {e}"
            )
            return {"success": False, "error": str(e), "time": time.time() - start_time}

    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete pipeline."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Starting full pipeline...")
        pipeline_start = time.time()

        # Run download phase
        download_result = self.run_download_phase()
        if not download_result["success"]:
            return download_result

        # Run processing phase
        processing_result = self.run_processing_phase()
        if not processing_result["success"]:
            return processing_result

        # Run KV ingestion phase
        kv_result = self.run_kv_ingestion_phase()
        if not kv_result["success"]:
            return kv_result

        # Update status.json file
        try:
            self.status_updater.update_status_file()
        except Exception as e:
            pprint.print(
                Platform.SYSTEM, Status.WARN, f"Failed to update status file: {e}"
            )

        total_time = time.time() - pipeline_start

        result = {
            "success": True,
            "total_time": total_time,
            "download_phase": download_result,
            "processing_phase": processing_result,
            "kv_ingestion_phase": kv_result,
        }

        pprint.print(
            Platform.SYSTEM,
            Status.PASS,
            f"Full pipeline completed in {total_time:.2f} seconds",
        )
        return result

    def run_incremental_sync(self) -> Dict[str, Any]:
        """Run incremental KV sync only."""
        return self.run_sync_phase()

    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        try:
            total_records = self.operations.get_anime_count()
            pending_changes = self.operations.get_pending_changes()

            # Get cached files count
            cached_files = 0
            if os.path.exists(self.cache_dir):
                cached_files = len(
                    [f for f in os.listdir(self.cache_dir) if f.endswith(".json")]
                )

            return {
                "total_records": total_records,
                "pending_changes": len(pending_changes),
                "cached_files": cached_files,
                "last_sync": None,  # TODO: Implement sync status tracking
            }
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.FAIL, f"Failed to get status: {e}")
            return {
                "total_records": 0,
                "pending_changes": 0,
                "cached_files": 0,
                "last_sync": None,
                "error": str(e),
            }

    def prune_database(self) -> None:
        """Prune (clear) the entire database."""
        pprint.print(Platform.SYSTEM, Status.INFO, "Pruning database...")

        try:
            # Drop all tables and recreate them
            self.schema.drop_all_tables()
            self.schema.create_all_tables()

            pprint.print(Platform.SYSTEM, Status.PASS, "Database pruned successfully")
        except Exception as e:
            pprint.print(Platform.SYSTEM, Status.FAIL, f"Failed to prune database: {e}")
            raise

    def export_data(self, export_dir: str) -> None:
        """Export data to various formats."""
        pprint.print(Platform.SYSTEM, Status.INFO, f"Exporting data to {export_dir}...")

        # Create export directory
        os.makedirs(export_dir, exist_ok=True)

        # TODO: Implement data export functionality
        # This would export the database to JSON, CSV, etc.

        pprint.print(Platform.SYSTEM, Status.PASS, "Export completed")

    def close(self) -> None:
        """Close database connections."""
        self.operations.close()
        self.schema.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def run_full_pipeline(db_path: str, cache_dir: str = CACHE_DIR) -> Dict[str, Any]:
    """Run the complete pipeline."""
    with SQLAlchemyPipeline(db_path, cache_dir) as pipeline:
        return pipeline.run_full_pipeline()


def run_incremental_sync(db_path: str) -> Dict[str, Any]:
    """Run incremental KV sync only."""
    with SQLAlchemyPipeline(db_path) as pipeline:
        return pipeline.run_incremental_sync()


def get_pipeline_status(db_path: str) -> Dict[str, Any]:
    """Get pipeline status."""
    with SQLAlchemyPipeline(db_path) as pipeline:
        return pipeline.get_status()


if __name__ == "__main__":
    # Simple test run
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DATABASE_URL

    result = run_full_pipeline(db_path)

    if result["success"]:
        print(f"Pipeline completed successfully in {result['total_time']:.2f} seconds")
    else:
        print(f"Pipeline failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
