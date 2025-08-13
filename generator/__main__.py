#!/usr/bin/env python

# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

"""
Main entry point for the SQLAlchemy-based anime data pipeline.
Can be run as: python -m generator [command] [options]
"""

import sys
import os
import argparse
from datetime import datetime

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.pipeline import SQLAlchemyPipeline
from generator.const import (
    pprint,
    CACHE_DIR,
    DATABASE_URL,
    GITHUB_TOKEN,
    KAIZE_EMAIL,
    KAIZE_PASSWORD,
)
from generator.prettyprint import Platform, Status


def check_environment_variables():
    """Check and report on required environment variables."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Checking environment variables...")

    # Check GitHub token
    if GITHUB_TOKEN:
        pprint.print(Platform.SYSTEM, Status.PASS, "GITHUB_TOKEN is set")
    else:
        pprint.print(
            Platform.SYSTEM,
            Status.WARN,
            "GITHUB_TOKEN is not set (optional, but recommended)",
        )

    # Check Kaize authentication
    kaize_vars = ["KAIZE_SESSION", "KAIZE_XSRF_TOKEN", "KAIZE_EMAIL", "KAIZE_PASSWORD"]
    kaize_values = [KAIZE_EMAIL, KAIZE_PASSWORD]
    kaize_set = all(kaize_values)

    if kaize_set:
        pprint.print(Platform.SYSTEM, Status.PASS, "All Kaize variables are set")
    else:
        pprint.print(
            Platform.SYSTEM,
            Status.WARN,
            "Kaize variables not set (Kaize data will not be fetched)",
        )
        missing = [var for var, val in zip(kaize_vars, kaize_values) if not val]
        for var in missing:
            pprint.print(Platform.SYSTEM, Status.WARN, f"  - {var}")

    # Check PostgreSQL configuration
    if DATABASE_URL:
        pprint.print(Platform.SYSTEM, Status.PASS, "PostgreSQL DATABASE_URL is set")
    else:
        pprint.print(
            Platform.SYSTEM, Status.FAIL, "PostgreSQL DATABASE_URL is required"
        )

    pprint.print(Platform.SYSTEM, Status.INFO, "")


def run_full_pipeline(db_path: str, cache_dir: str):
    """Run the complete pipeline (download, process, KV sync)."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Running full pipeline...")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Database: {db_path}")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Cache directory: {cache_dir}")
    pprint.print(
        Platform.SYSTEM, Status.INFO, f"Started at: {datetime.now().isoformat()}"
    )
    pprint.print(Platform.SYSTEM, Status.INFO, "-" * 60)

    try:
        with SQLAlchemyPipeline(db_path, cache_dir) as pipeline:
            result = pipeline.run_full_pipeline()

            if result["success"]:
                pprint.print(Platform.SYSTEM, Status.INFO, "=" * 60)
                pprint.print(Platform.SYSTEM, Status.INFO, "PIPELINE SUMMARY")
                pprint.print(Platform.SYSTEM, Status.INFO, "=" * 60)
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Total time: {result['total_time']:.2f} seconds",
                )

                # Download phase summary
                download = result["download_phase"]
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Download phase: {download['time']:.2f}s",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - GitHub files: {download['github_downloaded']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - Scrapers run: {download.get('scrapers_run', 0)}",
                )

                # Processing phase summary
                processing = result["processing_phase"]
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Processing phase: {processing['time']:.2f}s",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - Records inserted: {processing['records_inserted']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - Records updated: {processing['records_updated']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - Records deleted: {processing['records_deleted']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - Total records: {processing['total_records']}",
                )

                # KV ingestion phase summary
                kv = result["kv_ingestion_phase"]
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"KV ingestion phase: {kv['time']:.2f}s",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  - Changes processed: {kv['changes_processed']}",
                )

                return True
            else:
                pprint.print(
                    Platform.SYSTEM,
                    Status.FAIL,
                    f"Pipeline failed: {result.get('error', 'Unknown error')}",
                )
                return False

    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_download_phase(db_path: str, cache_dir: str, ignore_cache: bool = False):
    """Run download phase only."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Running download phase...")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Database: {db_path}")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Cache directory: {cache_dir}")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Ignore cache: {ignore_cache}")
    pprint.print(
        Platform.SYSTEM, Status.INFO, f"Started at: {datetime.now().isoformat()}"
    )
    pprint.print(Platform.SYSTEM, Status.INFO, "-" * 60)

    try:
        with SQLAlchemyPipeline(db_path, cache_dir) as pipeline:
            result = pipeline.run_download_phase(ignore_cache=ignore_cache)

            if result["success"]:
                pprint.print(
                    Platform.SYSTEM,
                    Status.PASS,
                    f"Download phase completed in {result['time']:.2f} seconds",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"GitHub files: {result['github_downloaded']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Scrapers run: {result.get('scrapers_run', 0)}",
                )

                # List downloaded files
                if result.get("github_results"):
                    pprint.print(
                        Platform.SYSTEM, Status.INFO, "GitHub files downloaded:"
                    )
                    for file in result["github_results"]:
                        pprint.print(
                            Platform.SYSTEM,
                            Status.INFO,
                            f"  - {os.path.basename(file)}",
                        )

                if result.get("scraper_results"):
                    pprint.print(Platform.SYSTEM, Status.INFO, "Scrapers run:")
                    for file in result["scraper_results"]:
                        pprint.print(
                            Platform.SYSTEM,
                            Status.INFO,
                            f"  - {os.path.basename(file)}",
                        )

                return True
            else:
                pprint.print(
                    Platform.SYSTEM,
                    Status.FAIL,
                    f"Download phase failed: {result.get('error', 'Unknown error')}",
                )
                return False

    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Download phase failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_process_phase(db_path: str, cache_dir: str):
    """Run processing phase only."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Running processing phase...")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Database: {db_path}")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Cache directory: {cache_dir}")
    pprint.print(
        Platform.SYSTEM, Status.INFO, f"Started at: {datetime.now().isoformat()}"
    )
    pprint.print(Platform.SYSTEM, Status.INFO, "-" * 60)

    try:
        with SQLAlchemyPipeline(db_path, cache_dir) as pipeline:
            result = pipeline.run_processing_phase()

            if result["success"]:
                pprint.print(
                    Platform.SYSTEM,
                    Status.PASS,
                    f"Processing phase completed in {result['time']:.2f} seconds",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Total records: {result['total_records']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Records inserted: {result['records_inserted']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Records updated: {result['records_updated']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Records deleted: {result['records_deleted']}",
                )
                return True
            else:
                pprint.print(
                    Platform.SYSTEM,
                    Status.FAIL,
                    f"Processing phase failed: {result.get('error', 'Unknown error')}",
                )
                return False

    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Processing phase failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_ingest_phase(db_path: str, force_overwrite_all: bool = False):
    """Run KV ingestion phase only."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Running KV ingestion phase...")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Database: {db_path}")
    pprint.print(
        Platform.SYSTEM, Status.INFO, f"Force overwrite all: {force_overwrite_all}"
    )
    pprint.print(
        Platform.SYSTEM, Status.INFO, f"Started at: {datetime.now().isoformat()}"
    )
    pprint.print(Platform.SYSTEM, Status.INFO, "-" * 60)

    try:
        with SQLAlchemyPipeline(db_path) as pipeline:
            result = pipeline.run_kv_ingestion_phase(
                force_overwrite_all=force_overwrite_all
            )

            if result["success"]:
                pprint.print(
                    Platform.SYSTEM,
                    Status.PASS,
                    f"KV ingestion phase completed in {result['time']:.2f} seconds",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"Changes processed: {result['changes_processed']}",
                )
                return True
            else:
                pprint.print(
                    Platform.SYSTEM,
                    Status.FAIL,
                    f"KV ingestion phase failed: {result.get('error', 'Unknown error')}",
                )
                return False

    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"KV ingestion phase failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def get_pipeline_status(db_path: str):
    """Get and display pipeline status."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Getting pipeline status...")
    pprint.print(Platform.SYSTEM, Status.INFO, f"Database: {db_path}")
    pprint.print(Platform.SYSTEM, Status.INFO, "-" * 60)

    try:
        with SQLAlchemyPipeline(db_path) as pipeline:
            status = pipeline.get_status()

            pprint.print(
                Platform.SYSTEM,
                Status.INFO,
                f"Total records: {status['total_records']}",
            )
            pprint.print(
                Platform.SYSTEM,
                Status.INFO,
                f"Pending changes: {status['pending_changes']}",
            )
            pprint.print(
                Platform.SYSTEM, Status.INFO, f"Cached files: {status['cached_files']}"
            )

            if status.get("last_sync"):
                pprint.print(Platform.SYSTEM, Status.INFO, "Last sync:")
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Started: {status['last_sync']['last_sync_start']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Ended: {status['last_sync']['last_sync_end']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Type: {status['last_sync']['sync_type']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Records processed: {status['last_sync']['records_processed']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Inserted: {status['last_sync']['records_inserted']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Updated: {status['last_sync']['records_updated']}",
                )
                pprint.print(
                    Platform.SYSTEM,
                    Status.INFO,
                    f"  Deleted: {status['last_sync']['records_deleted']}",
                )
            else:
                pprint.print(Platform.SYSTEM, Status.INFO, "No sync history found")

            return True

    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Failed to get status: {e}")
        return False


def prune_cache(cache_dir: str):
    """Prune cache directory."""
    pprint.print(Platform.SYSTEM, Status.INFO, f"Pruning cache directory: {cache_dir}")

    # Ask for confirmation
    response = input("Are you sure you want to delete all cached files? (y/N): ")
    if response.lower() != "y":
        pprint.print(Platform.SYSTEM, Status.INFO, "Cache pruning cancelled")
        return True

    try:
        import shutil

        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            pprint.print(
                Platform.SYSTEM, Status.PASS, f"Cache directory {cache_dir} removed"
            )
        else:
            pprint.print(
                Platform.SYSTEM,
                Status.INFO,
                f"Cache directory {cache_dir} does not exist",
            )
        return True
    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Failed to prune cache: {e}")
        return False


def prune_database(db_path: str):
    """Prune PostgreSQL database."""
    pprint.print(Platform.SYSTEM, Status.INFO, f"Pruning database: {db_path}")

    # Ask for confirmation
    response = input("Are you sure you want to delete the entire database? (y/N): ")
    if response.lower() != "y":
        pprint.print(Platform.SYSTEM, Status.INFO, "Database pruning cancelled")
        return True

    try:
        with SQLAlchemyPipeline(db_path) as pipeline:
            pipeline.prune_database()
            pprint.print(Platform.SYSTEM, Status.PASS, "Database pruned successfully")
        return True
    except Exception as e:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Failed to prune database: {e}")
        return False


def prune_redis():
    """Prune Redis/KV store."""
    pprint.print(Platform.SYSTEM, Status.INFO, "Pruning Redis/KV store...")

    # Ask for confirmation
    response = input("Are you sure you want to delete all Redis/KV data? (y/N): ")
    if response.lower() != "y":
        pprint.print(Platform.SYSTEM, Status.INFO, "Redis pruning cancelled")
        return True

    try:
        from generator.incremental_kv_ingest import IncrementalKVIngest

        kv_ingest = IncrementalKVIngest()
        kv_ingest.prune_all_keys()
        pprint.print(Platform.SYSTEM, Status.PASS, "Redis/KV store pruned successfully")
        return True
    except Exception as e:
        pprint.print(
            Platform.SYSTEM, Status.FAIL, f"Failed to prune Redis/KV store: {e}"
        )
        return False


def prune_all(db_path: str, cache_dir: str):
    """Prune all data (cache, database, and Redis)."""
    pprint.print(
        Platform.SYSTEM, Status.INFO, "Pruning ALL data (cache, database, and Redis)..."
    )

    # Ask for extra confirmation
    response = input(
        "Are you ABSOLUTELY sure you want to delete ALL data? This cannot be undone. (y/N): "
    )
    if response.lower() != "y":
        pprint.print(Platform.SYSTEM, Status.INFO, "Full pruning cancelled")
        return True

    success = True
    success &= prune_cache(cache_dir)
    success &= prune_database(db_path)
    success &= prune_redis()

    if success:
        pprint.print(Platform.SYSTEM, Status.PASS, "All data pruned successfully")
    else:
        pprint.print(Platform.SYSTEM, Status.FAIL, "Some pruning operations failed")

    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SQLAlchemy-based anime data pipeline", prog="python -m generator"
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Full command (default)
    full_parser = subparsers.add_parser("full", help="Run complete pipeline (default)")
    full_parser.add_argument("--database-url", help="PostgreSQL database URL")
    full_parser.add_argument("--cache-dir", help="Cache directory path")
    full_parser.add_argument("--redis-url", help="Redis connection URL")
    full_parser.add_argument("--redis-host", help="Redis host")
    full_parser.add_argument("--redis-port", type=int, help="Redis port")
    full_parser.add_argument("--redis-user", help="Redis username")
    full_parser.add_argument("--redis-password", help="Redis password")
    full_parser.add_argument("--redis-db", type=int, help="Redis database number")
    full_parser.add_argument("--redis-ssl", action="store_true", help="Use Redis SSL")
    full_parser.add_argument("--upstash-url", help="Upstash Redis URL")
    full_parser.add_argument("--upstash-token", help="Upstash Redis token")
    full_parser.add_argument(
        "--no-env-check", action="store_true", help="Skip environment variable checks"
    )

    # Download command
    download_parser = subparsers.add_parser("download", help="Run download phase only")
    download_parser.add_argument("--database-url", help="PostgreSQL database URL")
    download_parser.add_argument("--cache-dir", help="Cache directory path")
    download_parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Ignore cache and re-download all files",
    )
    download_parser.add_argument(
        "--no-env-check", action="store_true", help="Skip environment variable checks"
    )

    # Process command
    process_parser = subparsers.add_parser("process", help="Run processing phase only")
    process_parser.add_argument("--database-url", help="PostgreSQL database URL")
    process_parser.add_argument("--cache-dir", help="Cache directory path")
    process_parser.add_argument(
        "--no-env-check", action="store_true", help="Skip environment variable checks"
    )

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Run KV ingestion phase only")
    ingest_parser.add_argument("--database-url", help="PostgreSQL database URL")
    ingest_parser.add_argument("--redis-url", help="Redis connection URL")
    ingest_parser.add_argument("--redis-host", help="Redis host")
    ingest_parser.add_argument("--redis-port", type=int, help="Redis port")
    ingest_parser.add_argument("--redis-user", help="Redis username")
    ingest_parser.add_argument("--redis-password", help="Redis password")
    ingest_parser.add_argument("--redis-db", type=int, help="Redis database number")
    ingest_parser.add_argument("--redis-ssl", action="store_true", help="Use Redis SSL")
    ingest_parser.add_argument("--upstash-url", help="Upstash Redis URL")
    ingest_parser.add_argument("--upstash-token", help="Upstash Redis token")
    ingest_parser.add_argument(
        "--force-overwrite-all", action="store_true", help="Force overwrite all KV data"
    )
    ingest_parser.add_argument(
        "--no-env-check", action="store_true", help="Skip environment variable checks"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument("--database-url", help="PostgreSQL database URL")
    status_parser.add_argument(
        "--no-env-check", action="store_true", help="Skip environment variable checks"
    )

    # Prune commands
    prune_parser = subparsers.add_parser("prune", help="Prune data")
    prune_subparsers = prune_parser.add_subparsers(
        dest="prune_target", help="What to prune"
    )

    cache_prune_parser = prune_subparsers.add_parser(
        "cache", help="Prune cache directory"
    )
    cache_prune_parser.add_argument("--cache-dir", help="Cache directory path")

    db_prune_parser = prune_subparsers.add_parser("database", help="Prune database")
    db_prune_parser.add_argument("--database-url", help="PostgreSQL database URL")

    prune_subparsers.add_parser("redis", help="Prune Redis/KV store")

    all_prune_parser = prune_subparsers.add_parser("all", help="Prune all data")
    all_prune_parser.add_argument("--database-url", help="PostgreSQL database URL")
    all_prune_parser.add_argument("--cache-dir", help="Cache directory path")

    # Parse arguments
    args = parser.parse_args()

    # Default to 'full' command if no command provided
    if args.command is None:
        args.command = "full"

    # Configure database path
    db_path = (
        args.database_url
        if hasattr(args, "database_url") and args.database_url
        else DATABASE_URL
    )

    # Configure cache directory
    cache_dir = (
        args.cache_dir if hasattr(args, "cache_dir") and args.cache_dir else CACHE_DIR
    )

    # Check environment variables unless skipped
    if not hasattr(args, "no_env_check") or not args.no_env_check:
        check_environment_variables()

    # Execute command
    success = False

    if args.command == "full":
        success = run_full_pipeline(db_path, cache_dir)
    elif args.command == "download":
        success = run_download_phase(db_path, cache_dir, args.ignore_cache)
    elif args.command == "process":
        success = run_process_phase(db_path, cache_dir)
    elif args.command == "ingest":
        success = run_ingest_phase(db_path, args.force_overwrite_all)
    elif args.command == "status":
        success = get_pipeline_status(db_path)
    elif args.command == "prune":
        if args.prune_target == "cache":
            success = prune_cache(cache_dir)
        elif args.prune_target == "database":
            success = prune_database(db_path)
        elif args.prune_target == "redis":
            success = prune_redis()
        elif args.prune_target == "all":
            success = prune_all(db_path, cache_dir)
        else:
            pprint.print(
                Platform.SYSTEM,
                Status.ERR,
                "Please specify what to prune: cache, database, redis, or all",
            )
            sys.exit(1)

    if success:
        pprint.print(
            Platform.SYSTEM,
            Status.PASS,
            f"Command '{args.command}' completed successfully!",
        )
        sys.exit(0)
    else:
        pprint.print(Platform.SYSTEM, Status.FAIL, f"Command '{args.command}' failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
