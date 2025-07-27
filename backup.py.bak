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

from config import app_paths, get_config


class DatabaseBackup:
    """Database backup manager using pathlib"""
    
    def __init__(self, config=None):
        """Initialize backup manager"""
        self.config = config or get_config()
        self.paths = self.config.paths
        self.logger = self._setup_logging()
        
        # Ensure backup directories exist
        self.paths.backup_dir.mkdir(parents=True, exist_ok=True)
        self.paths.log_dir.mkdir(parents=True, exist_ok=True)

    
    def _setup_logging(self):
        """Setup logging for backup operations"""
        logger = logging.getLogger('backup')
        logger.setLevel(getattr(logging, self.config.LOG_LEVEL))
        
        if not logger.handlers:
            handler = logging.FileHandler(self.paths.backup_log_file)

            formatter = logging.Formatter(self.config.LOG_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def create_backup(self, compress=True, include_metadata=True) -> Optional[Path]:
        """
        Create a database backup
        
        Args:
            compress: Whether to compress the backup file
            include_metadata: Whether to include backup metadata
            
        Returns:
            Path to created backup file or None if failed
        """
        try:
            self.logger.debug(f"Starting backup creation. compress={compress}, include_metadata={include_metadata}")
            self.logger.debug(f"Database file: {self.paths.database_file}")
            self.logger.debug(f"Backup directory: {self.paths.backup_dir}")
            # Check if source database exists
            if not self.paths.database_file.exists():
                self.logger.error(f"Source database not found: {self.paths.database_file}")
                return None
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.db"
            self.logger.debug(f"Generated backup name: {backup_name}")
            
            if compress:
                backup_name += ".gz"
                self.logger.debug("Compression enabled, updated backup name: %s", backup_name)
            
            backup_path = self.paths.backup_dir / backup_name
            self.logger.debug(f"Backup path: {backup_path}")
            
            # Create backup
            if compress:
                self.logger.debug("Calling _create_compressed_backup")
                success = self._create_compressed_backup(backup_path)
            else:
                self.logger.debug("Calling _create_simple_backup")
                success = self._create_simple_backup(backup_path)
            
            if success:
                self.logger.debug("Backup file created: %s", backup_path)
                # Add metadata if requested
                if include_metadata:
                    self.logger.debug("Creating backup metadata for: %s", backup_path)
                    self._create_backup_metadata(backup_path)
                
                self.logger.info(f"Backup created successfully: {backup_path}")
                return backup_path
            else:
                self.logger.error("Backup creation failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Backup creation error: {str(e)}")
            return None
    
    def _create_simple_backup(self, backup_path: Path) -> bool:
        """Create a simple file copy backup"""
        try:
            self.logger.debug(f"Starting _create_simple_backup to {backup_path}")
            # Use SQLite backup API for consistent backup
            source_conn = sqlite3.connect(str(self.paths.database_file))
            backup_conn = sqlite3.connect(str(backup_path))
            
            # Perform backup
            source_conn.backup(backup_conn)
            self.logger.debug(f"SQLite backup API completed from {self.paths.database_file} to {backup_path}")
            
            # Close connections
            backup_conn.close()
            source_conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Simple backup failed: {str(e)}")
            # Fallback to file copy
            try:
                self.logger.debug(f"Attempting fallback copy2 from {self.paths.database_file} to {backup_path}")
                shutil.copy2(self.paths.database_file, backup_path)
                self.logger.debug(f"Fallback copy2 succeeded")
                return True
            except Exception as fallback_error:
                self.logger.error(f"Fallback backup failed: {str(fallback_error)}")
                return False
    
    def _create_compressed_backup(self, backup_path: Path) -> bool:
        """Create a compressed backup"""
        try:
            self.logger.debug(f"Starting _create_compressed_backup to {backup_path}")
            # First create temporary uncompressed backup
            temp_backup = self.paths.temp_dir / f"temp_backup_{datetime.now().timestamp()}.db"
            self.logger.debug(f"Temporary backup path: {temp_backup}")
            
            if self._create_simple_backup(temp_backup):
                self.logger.debug(f"Compressing {temp_backup} to {backup_path}")
                # Compress the backup
                with temp_backup.open('rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Clean up temporary file
                temp_backup.unlink()
                self.logger.debug(f"Compressed backup created at {backup_path}")
                return True
            else:
                self.logger.error(f"Failed to create temporary backup for compression: {temp_backup}")
                return False
                
        except Exception as e:
            self.logger.error(f"Compressed backup failed: {str(e)}")
            return False
    
    def _create_backup_metadata(self, backup_path: Path):
        """Create metadata file for backup"""
        try:
            metadata = {
                'backup_file': backup_path.name,
                'created_at': datetime.now().isoformat(),
                'source_database': str(self.paths.database_file),
                'database_size': self.paths.database_file.stat().st_size,
                'backup_size': backup_path.stat().st_size,
                'compressed': backup_path.suffix == '.gz',
                'backup_method': 'sqlite_backup_api'
            }
            
            metadata_path = backup_path.with_suffix(backup_path.suffix + '.meta')
            
            with metadata_path.open('w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to create metadata: {str(e)}")
    
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
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            target = target_path or self.paths.database_file
            
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
            # Find all backup files
            backup_files = list(self.paths.backup_dir.glob("backup_*.db*"))
            
            for backup_file in sorted(backup_files, reverse=True):
                # Skip metadata files
                if backup_file.suffix == '.meta':
                    continue
                
                backup_info = {
                    'path': backup_file,
                    'name': backup_file.name,
                    'size': backup_file.stat().st_size,
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
        retention_days = retention_days or self.config.BACKUP_RETENTION_DAYS
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        try:
            backup_files = list(self.paths.backup_dir.glob("backup_*"))
            
            for backup_file in backup_files:
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
                return False
            
            # Create temporary file for verification
            temp_file = self.paths.temp_dir / f"verify_{datetime.now().timestamp()}.db"
            
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
                    temp_file.unlink()
                    
                    self.logger.info(f"Backup verification successful: {backup_path}")
                    return len(tables) > 0  # Valid if has tables
                    
                except Exception as e:
                    self.logger.error(f"Database verification failed: {str(e)}")
                    if temp_file.exists():
                        temp_file.unlink()
                    return False
            else:
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
            
            return {
                'total_backups': len(backups),
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_backup': min(backup['created'] for backup in backups),
                'newest_backup': max(backup['created'] for backup in backups),
                'compressed_count': compressed_count,
                'uncompressed_count': len(backups) - compressed_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get backup stats: {str(e)}")
            return {}


# Convenience functions for easy access
def create_backup(compress=True) -> Optional[Path]:
    """Create a database backup"""
    backup_manager = DatabaseBackup()
    return backup_manager.create_backup(compress=compress)


def restore_from_backup(backup_path: Path) -> bool:
    """Restore database from backup"""
    backup_manager = DatabaseBackup()
    return backup_manager.restore_backup(backup_path)


def cleanup_backups(retention_days=30) -> int:
    """Clean up old backups"""
    backup_manager = DatabaseBackup()
    return backup_manager.cleanup_old_backups(retention_days)


def list_available_backups() -> List[Dict[str, Any]]:
    """List all available backups"""
    backup_manager = DatabaseBackup()
    return backup_manager.list_backups()


if __name__ == "__main__":
    # CLI interface for backup operations
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python backup.py [create|restore|list|cleanup|verify]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    backup_manager = DatabaseBackup()
    
    if command == "create":
        backup_path = backup_manager.create_backup()
        if backup_path:
            print(f"Backup created: {backup_path}")
        else:
            print("Backup creation failed")
    
    elif command == "list":
        backups = backup_manager.list_backups()
        if backups:
            print(f"Found {len(backups)} backups:")
            for backup in backups:
                print(f"  {backup['name']} - {backup['size']} bytes - {backup['created']}")
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