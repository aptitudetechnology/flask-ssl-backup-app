"""
Database Backup System with Pathlib Integration
Handles SQLite database backups with proper path management
"""

import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import gzip
import json

# We don't need app_paths or get_config here if the config object is always passed in __init__
# from config import app_paths, get_config


class DatabaseBackup:
    """Database backup manager using pathlib"""

    def __init__(self, config=None):
        """
        Initialize backup manager.
        'config' is expected to be Flask's app.config dictionary.
        """
        self.config = config # This will now be Flask's app.config

        # --- FIX: Retrieve AppPaths instance correctly from config ---
        self.app_paths = self.config.get('APP_PATHS')
        if not self.app_paths:
            raise ValueError("AppPaths instance not found in Flask app config. "
                             "Ensure app.config['APP_PATHS'] is set in your app factory.")
        
        # Now use self.app_paths for all path-related properties
        self.logger = self._setup_logging()

        # Ensure backup directories exist using app_paths properties
        self.app_paths.backup_dir.mkdir(parents=True, exist_ok=True)
        self.app_paths.log_dir.mkdir(parents=True, exist_ok=True)
        self.app_paths.temp_dir.mkdir(parents=True, exist_ok=True) # Ensure temp_dir also exists


    def _setup_logging(self):
        """Setup logging for backup operations"""
        logger = logging.getLogger('backup')
        
        # Access LOG_LEVEL from self.config (which is app.config)
        log_level_str = self.config.get('LOG_LEVEL', 'INFO')
        logger.setLevel(getattr(logging, log_level_str.upper(), logging.INFO))

        if not logger.handlers:
            # Access backup_log_file from self.app_paths
            handler = logging.FileHandler(self.app_paths.backup_log_file)
            
            # Access LOG_FORMAT from self.config
            log_format = self.config.get('LOG_FORMAT', '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
            formatter = logging.Formatter(log_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.addHandler(logging.StreamHandler()) # Add console handler for visibility

        return logger

    def create_backup(self, format='zip', include_attachments=False, backup_type='manual', description='Manual backup', user_id=None) -> Optional[Path]:
        """
        Create a database backup based on the requested format and other options.

        Args:
            format (str): The desired backup format ('zip', 'json', 'csv', 'gz').
                          Currently, 'zip' and 'gz' will result in .gz compressed DBs.
            include_attachments (bool): Whether to include attachments (not implemented here yet).
            backup_type (str): Type of backup (manual, pre_restore, etc.).
            description (str): Description for the backup record.
            user_id (int): ID of the user creating the backup.

        Returns:
            Path to created backup file or None if failed.
        """
        try:
            # Determine compression based on the 'format' requested from the UI
            compress = False # Default to no compression
            if format.lower() == 'zip' or format.lower() == 'gz':
                compress = True

            self.logger.debug(f"Starting backup creation. format='{format}', compress={compress}, include_attachments={include_attachments}")
            # Use self.app_paths for database_file
            self.logger.debug(f"Database file: {self.app_paths.database_file}")
            # Use self.app_paths for backup_dir
            self.logger.debug(f"Backup directory: {self.app_paths.backup_dir}")

            # Check if source database exists
            if not self.app_paths.database_file.exists():
                self.logger.error(f"Source database not found: {self.app_paths.database_file}")
                return None

            # Generate backup filename using AppPaths' method
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = self.app_paths.get_backup_filename(backup_type=backup_type, timestamp=timestamp)
            self.logger.debug(f"Generated base backup name: {backup_name}")

            # Adjust filename for compression if needed
            final_backup_name = backup_name
            if compress:
                final_backup_name += ".gz"
                self.logger.debug("Compression enabled, updated backup name to .gz: %s", final_backup_name)
            elif format.lower() == 'json':
                 self.logger.warning(f"JSON format requested, but only SQLite DB backup is supported. Creating .db backup.")
            elif format.lower() == 'csv':
                 self.logger.warning(f"CSV format requested, but only SQLite DB backup is supported. Creating .db backup.")

            # Construct final backup path using self.app_paths.backup_dir
            backup_path = self.app_paths.backup_dir / final_backup_name
            self.logger.debug(f"Final backup path: {backup_path}")

            # Create backup
            if compress:
                self.logger.debug("Calling _create_compressed_backup (will result in .gz)")
                success = self._create_compressed_backup(backup_path)
            else:
                self.logger.debug("Calling _create_simple_backup (will result in .db)")
                success = self._create_simple_backup(backup_path)

            if success:
                self.logger.debug("Backup file created: %s, checking size.", backup_path)
                # Verify size after creation
                if not backup_path.exists() or backup_path.stat().st_size == 0:
                     self.logger.error(f"Created backup file is empty or missing: {backup_path}")
                     # Attempt to clean up the empty file
                     if backup_path.exists():
                         backup_path.unlink()
                     return None # Return None if backup is empty or missing

                # Add metadata (always included by default in this method's logic if success is true)
                self.logger.debug("Creating backup metadata for: %s", backup_path)
                self._create_backup_metadata(backup_path)

                self.logger.info(f"Backup created successfully: {backup_path} (Size: {backup_path.stat().st_size} bytes)")
                return backup_path
            else:
                self.logger.error("Backup creation failed (success flag was False)")
                return None

        except Exception as e:
            self.logger.error(f"Backup creation error caught in create_backup: {str(e)}")
            return None

    def _create_simple_backup(self, backup_path: Path) -> bool:
        """Create a simple file copy backup"""
        try:
            self.logger.debug(f"Starting _create_simple_backup to {backup_path}")
            # Use SQLite backup API for consistent backup
            # Access database_file from self.app_paths
            source_conn = sqlite3.connect(str(self.app_paths.database_file))
            backup_conn = sqlite3.connect(str(backup_path))

            # Perform backup
            source_conn.backup(backup_conn)
            self.logger.debug(f"SQLite backup API completed from {self.app_paths.database_file} to {backup_path}")

            # Close connections
            backup_conn.close()
            source_conn.close()

            # Verify the file size right after creation
            if not backup_path.exists() or backup_path.stat().st_size == 0:
                self.logger.error(f"Simple backup created 0-byte file or failed: {backup_path}")
                # Fallback to shutil.copy2 if sqlite3.backup failed
                try:
                    self.logger.debug(f"Attempting fallback copy2 from {self.app_paths.database_file} to {backup_path}")
                    shutil.copy2(self.app_paths.database_file, backup_path)
                    if not backup_path.exists() or backup_path.stat().st_size == 0:
                        self.logger.error(f"Fallback copy2 also created 0-byte file or failed: {backup_path}")
                        return False
                    self.logger.debug(f"Fallback copy2 succeeded, size: {backup_path.stat().st_size} bytes")
                    return True
                except Exception as fallback_error:
                    self.logger.error(f"Fallback backup failed: {str(fallback_error)}")
                    return False

            return True # If sqlite3.backup worked and file is not 0-byte

        except Exception as e:
            self.logger.error(f"Simple backup failed: {str(e)}")
            # If the initial sqlite3.backup fails, attempt fallback
            try:
                self.logger.debug(f"Attempting fallback copy2 from {self.app_paths.database_file} to {backup_path} due to initial failure.")
                shutil.copy2(self.app_paths.database_file, backup_path)
                if not backup_path.exists() or backup_path.stat().st_size == 0:
                    self.logger.error(f"Fallback copy2 also created 0-byte file or failed: {backup_path}")
                    return False
                self.logger.debug(f"Fallback copy2 succeeded, size: {backup_path.stat().st_size} bytes")
                return True
            except Exception as fallback_error:
                self.logger.error(f"Fallback backup failed: {str(fallback_error)}")
                return False

    def _create_compressed_backup(self, backup_path: Path) -> bool:
        """Create a compressed backup (gzip)"""
        try:
            self.logger.debug(f"Starting _create_compressed_backup to {backup_path}")
            # First create temporary uncompressed backup
            temp_backup_filename = f"temp_backup_{datetime.now().timestamp()}.db"
            # Access temp_dir from self.app_paths
            temp_backup = self.app_paths.temp_dir / temp_backup_filename
            self.app_paths.temp_dir.mkdir(parents=True, exist_ok=True) # Ensure temp dir exists
            self.logger.debug(f"Temporary backup path: {temp_backup}")

            # Use _create_simple_backup to create the uncompressed temp file
            if self._create_simple_backup(temp_backup):
                if not temp_backup.exists() or temp_backup.stat().st_size == 0:
                    self.logger.error(f"Temporary backup for compression is empty or missing: {temp_backup}")
                    if temp_backup.exists(): temp_backup.unlink() # Clean up empty temp file
                    return False

                self.logger.debug(f"Compressing {temp_backup} to {backup_path}")
                # Compress the backup
                with temp_backup.open('rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Verify compressed file size
                if not backup_path.exists() or backup_path.stat().st_size == 0:
                    self.logger.error(f"Compressed backup created 0-byte file or failed: {backup_path}")
                    return False # Return False if compressed file is empty

                # Clean up temporary file
                temp_backup.unlink()
                self.logger.debug(f"Compressed backup created at {backup_path}, size: {backup_path.stat().st_size} bytes")
                return True
            else:
                self.logger.error(f"Failed to create temporary backup for compression: {temp_backup}")
                return False

        except Exception as e:
            self.logger.error(f"Compressed backup failed: {str(e)}")
            # Clean up temp file in case of error
            if temp_backup.exists():
                temp_backup.unlink()
            if backup_path.exists(): # Clean up potentially empty/corrupt target file
                backup_path.unlink()
            return False

    def _create_backup_metadata(self, backup_path: Path):
        """Create metadata file for backup"""
        try:
            metadata = {
                'backup_file': backup_path.name,
                'created_at': datetime.now().isoformat(),
                # Access database_file from self.app_paths
                'source_database': str(self.app_paths.database_file),
                'database_size': self.app_paths.database_file.stat().st_size,
                'backup_size': backup_path.stat().st_size,
                'compressed': backup_path.suffix == '.gz',
                'backup_method': 'sqlite_backup_api'
            }

            metadata_path = backup_path.with_suffix(backup_path.suffix + '.meta')

            with metadata_path.open('w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to create metadata for {backup_path}: {str(e)}")

    def restore_backup(self, backup_path: Path, target_path: Optional[Path] = None) -> bool:
        """
        Restore database from backup

        Args:
            backup_path: Path to backup file
            target_path: Target restoration path (defaults to main database)

        Returns:
            True if restoration successful
        """
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup file not found for restore: {backup_path}")
                return False

            # Access database_file from self.app_paths
            target = target_path or self.app_paths.database_file

            # Create target directory if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Handle compressed backups
            if backup_path.suffix == '.gz':
                return self._restore_compressed_backup(backup_path, target)
            else:
                return self._restore_simple_backup(backup_path, target)

        except Exception as e:
            self.logger.error(f"Backup restoration error: {str(e)}")
            return False

    def _restore_simple_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore from simple backup"""
        try:
            shutil.copy2(backup_path, target_path)
            self.logger.info(f"Database restored from {backup_path} to {target_path}")
            return True
        except Exception as e:
            self.logger.error(f"Simple restore failed: {str(e)}")
            return False

    def _restore_compressed_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore from compressed backup"""
        try:
            with gzip.open(backup_path, 'rb') as f_in:
                with target_path.open('wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            self.logger.info(f"Compressed database restored from {backup_path} to {target_path}")
            return True
        except Exception as e:
            self.logger.error(f"Compressed restore failed: {str(e)}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups with metadata"""
        backups = []

        try:
            # Find all backup files using self.app_paths.backup_dir
            backup_files = list(self.app_paths.backup_dir.glob("backup_*.db*"))

            for backup_file in sorted(backup_files, reverse=True):
                # Skip metadata files
                if backup_file.suffix == '.meta':
                    continue

                # Ensure we only process files that exist and are not directories
                if not backup_file.is_file():
                    continue

                # Try to get file size safely
                file_size = 0
                try:
                    file_size = backup_file.stat().st_size
                except FileNotFoundError:
                    self.logger.warning(f"File not found during list_backups, skipping: {backup_file}")
                    continue # Skip if file disappeared

                backup_info = {
                    'path': backup_file,
                    'name': backup_file.name,
                    'size': file_size,
                    'created': datetime.fromtimestamp(backup_file.stat().st_mtime),
                    'compressed': backup_file.suffix == '.gz'
                }

                # Load metadata if available
                metadata_path = backup_file.with_suffix(backup_file.suffix + '.meta')
                if metadata_path.exists():
                    try:
                        with metadata_path.open('r') as f:
                            metadata = json.load(f)
                        backup_info['metadata'] = metadata
                    except Exception as e:
                        self.logger.warning(f"Failed to load metadata for {backup_file}: {str(e)}")

                backups.append(backup_info)

        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")

        return backups

    def cleanup_old_backups(self, retention_days: Optional[int] = None) -> int:
        """
        Clean up old backup files

        Args:
            retention_days: Days to retain backups (uses config default if None)

        Returns:
            Number of files deleted
        """
        # Access BACKUP_RETENTION_DAYS from self.config
        retention_days = retention_days or self.config.get('BACKUP_RETENTION_DAYS', 30) # Default to 30 if not in config
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0

        try:
            # Use self.app_paths.backup_dir
            backup_files = list(self.app_paths.backup_dir.glob("backup_*"))

            for backup_file in backup_files:
                # Ensure it's a file before checking stat()
                if not backup_file.is_file():
                    continue

                try:
                    file_date = datetime.fromtimestamp(backup_file.stat().st_mtime)

                    if file_date < cutoff_date:
                        try:
                            backup_file.unlink()
                            deleted_count += 1
                            self.logger.info(f"Deleted old backup: {backup_file}")

                            # Also delete associated metadata file
                            metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
                            if metadata_file.exists():
                                metadata_file.unlink()

                        except Exception as e:
                            self.logger.error(f"Failed to delete {backup_file}: {str(e)}")
                except FileNotFoundError:
                    self.logger.warning(f"File not found during cleanup, skipping: {backup_file}")
                    continue # Skip if file disappeared while iterating


            self.logger.info(f"Cleanup completed: {deleted_count} files deleted")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

        return deleted_count

    def verify_backup(self, backup_path: Path) -> bool:
        """
        Verify backup file integrity

        Args:
            backup_path: Path to backup file to verify

        Returns:
            True if backup is valid
        """
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup file not found for verification: {backup_path}")
                return False

            # Create temporary file for verification
            temp_file_name = f"verify_{datetime.now().timestamp()}.db"
            # Access temp_dir from self.app_paths
            temp_file = self.app_paths.temp_dir / temp_file_name
            self.app_paths.temp_dir.mkdir(parents=True, exist_ok=True) # Ensure temp dir exists

            # Try to restore to temporary location
            if self.restore_backup(backup_path, temp_file):
                # Try to open and query the restored database
                try:
                    conn = sqlite3.connect(str(temp_file))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    conn.close()

                    # Clean up temporary file
                    if temp_file.exists():
                        temp_file.unlink()

                    self.logger.info(f"Backup verification successful: {backup_path}")
                    return len(tables) > 0  # Valid if has tables

                except Exception as e:
                    self.logger.error(f"Database verification failed for {backup_path}: {str(e)}")
                    if temp_file.exists():
                        temp_file.unlink()
                    return False
            else:
                self.logger.error(f"Failed to restore backup to temp location for verification: {backup_path}")
                return False

        except Exception as e:
            self.logger.error(f"Backup verification error: {str(e)}")
            return False

    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        try:
            backups = self.list_backups()

            if not backups:
                return {
                    'total_backups': 0,
                    'total_size': 0,
                    'oldest_backup': None,
                    'newest_backup': None,
                    'compressed_count': 0
                }

            total_size = sum(backup['size'] for backup in backups)
            compressed_count = sum(1 for backup in backups if backup['compressed'])

            # Ensure datetime objects for oldest/newest are handled to avoid errors
            oldest_backup_date = None
            newest_backup_date = None
            if backups:
                dates = [b['created'] for b in backups]
                if dates:
                    oldest_backup_date = min(dates)
                    newest_backup_date = max(dates)

            return {
                'total_backups': len(backups),
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_backup': oldest_backup_date,
                'newest_backup': newest_backup_date,
                'compressed_count': compressed_count,
                'uncompressed_count': len(backups) - compressed_count
            }

        except Exception as e:
            self.logger.error(f"Failed to get backup stats: {str(e)}")
            return {}


# Convenience functions for easy access (These are designed for standalone use or where app.config isn't available)
def create_backup_convenience(compress=True) -> Optional[Path]: # Renamed to avoid confusion with class method
    """Create a database backup"""
    # This will use get_config() which returns a custom config instance.
    # The DatabaseBackup here will instantiate with that.
    # If this is used outside a Flask app, ensure get_config() provides the 'paths' attribute directly.
    backup_manager = DatabaseBackup(config=get_config())
    return backup_manager.create_backup(format='zip' if compress else 'db', include_attachments=False)


def restore_from_backup_convenience(backup_path: Path) -> bool: # Renamed
    """Restore database from backup"""
    backup_manager = DatabaseBackup(config=get_config())
    return backup_manager.restore_backup(backup_path)


def cleanup_backups_convenience(retention_days=30) -> int: # Renamed
    """Clean up old backups"""
    backup_manager = DatabaseBackup(config=get_config())
    return backup_manager.cleanup_old_backups(retention_days)


def list_available_backups_convenience() -> List[Dict[str, Any]]: # Renamed
    """List all available backups"""
    backup_manager = DatabaseBackup(config=get_config())
    return backup_manager.list_backups()


if __name__ == "__main__":
    # CLI interface for backup operations
    import sys

    if len(sys.argv) < 2:
        print("Usage: python backup.py [create|restore|list|cleanup|verify]")
        sys.exit(1)

    command = sys.argv[1].lower()
    # For standalone execution, DatabaseBackup should get its config from get_config()
    # which provides the 'paths' attribute directly on its returned object.
    # The __init__ of DatabaseBackup has been updated to handle either Flask's app.config
    # or your custom config object if passed explicitly (by checking for 'APP_PATHS' vs 'paths').
    # A more robust solution for standalone might be to have two different init paths,
    # or ensure get_config always returns a dict-like object.
    # For now, we'll assume get_config() returns an object that has a 'paths' attribute
    # for the CLI usage.
    
    # If you intend for this CLI to strictly mimic Flask's config,
    # you'd need to mock or load a similar dict structure.
    # For simplicity, if `config.py`'s `get_config()` returns an object
    # with `config_instance.paths.some_path`, then this setup is fine for CLI.
    
    # Let's ensure the CLI uses a config that has `paths` as an attribute for its operation
    # Since `DatabaseBackup`'s `__init__` now checks for `APP_PATHS` first,
    # we need to make sure `get_config()` provides it, or adapt `__init__` further.

    # Option for CLI: Create a dummy config that mimics app.config
    class CliConfigDict(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # When running CLI, directly get AppPaths
            from paths import AppPaths # Import AppPaths here to avoid global import if not always needed
            self['APP_PATHS'] = AppPaths()
            self['LOG_LEVEL'] = 'INFO' # Default for CLI logging
            self['LOG_FORMAT'] = '%(asctime)s %(levelname)s: %(message)s'
            self['BACKUP_RETENTION_DAYS'] = 30 # Default for CLI cleanup

    # Instantiate with the CLI-specific config
    cli_config = CliConfigDict()
    backup_manager = DatabaseBackup(config=cli_config)


    if command == "create":
        backup_format_cli = 'zip'
        if '--format' in sys.argv:
            try:
                format_idx = sys.argv.index('--format')
                backup_format_cli = sys.argv[format_idx + 1]
            except (ValueError, IndexError):
                print("Error: --format requires a value (e.g., zip, gz, json, csv)")
                sys.exit(1)

        backup_path = backup_manager.create_backup(format=backup_format_cli, include_attachments=False)
        if backup_path:
            print(f"Backup created: {backup_path}")
        else:
            print("Backup creation failed")

    elif command == "list":
        backups = backup_manager.list_backups()
        if backups:
            print(f"Found {len(backups)} backups:")
            for backup in backups:
                created_date_str = backup['created'].isoformat() if isinstance(backup['created'], datetime) else str(backup['created'])
                print(f"  {backup['name']} - {backup['size']} bytes - {created_date_str}")
        else:
            print("No backups found")

    elif command == "cleanup":
        deleted = backup_manager.cleanup_old_backups()
        print(f"Deleted {deleted} old backup files")

    elif command == "restore" and len(sys.argv) > 2:
        backup_path = Path(sys.argv[2])
        if backup_manager.restore_backup(backup_path):
            print(f"Database restored from {backup_path}")
        else:
            print("Restore failed")

    elif command == "verify" and len(sys.argv) > 2:
        backup_path = Path(sys.argv[2])
        if backup_manager.verify_backup(backup_path):
            print(f"Backup verified: {backup_path}")
        else:
            print(f"Backup verification failed: {backup_path}")

    else:
        print("Invalid command or missing arguments")