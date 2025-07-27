# paths.py

import os
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta # Ensure these are imported for utility methods


class AppPaths:
    """Centralized path management using pathlib"""

    def __init__(self, app_root: Optional[Path] = None):
        # Determine the application root. Prioritize explicit app_root, then a common parent structure.
        # This assumes the project root is two levels up from paths.py (e.g., app_root/paths.py)
        self.app_root = Path(app_root) if app_root else Path(__file__).parent.parent
        
        # Initialize internal variables for directories that are properties
        # This ensures they are available before _ensure_directories is called
        self._data_dir_path = self.app_root / "data"
        self._log_dir_path = self.app_root / "logs"
        self._ssl_dir_path = self.app_root / "ssl" # Consistent with other direct app_root paths
        
        # Call _ensure_directories to create all necessary folders on initialization
        self._ensure_directories()

    # --- Core application paths ---
    @property
    def data_dir(self) -> Path:
        return self._data_dir_path

    @property
    def database_file(self) -> Path:
        return self.data_dir / "customers.db"

    @property
    def static_dir(self) -> Path:
        return self.app_root / "static"

    @property
    def templates_dir(self) -> Path:
        return self.app_root / "templates"

    # --- SSL certificate paths ---
    @property
    def ssl_dir(self) -> Path:
        # Use the internally managed path, allowing override via env var
        return Path(os.environ.get('SSL_CERT_DIR', self._ssl_dir_path))

    @property
    def ssl_cert_file(self) -> Path:
        return Path(os.environ.get('SSL_CERT_PATH', self.ssl_dir / "cert.pem"))

    @property
    def ssl_key_file(self) -> Path:
        return Path(os.environ.get('SSL_KEY_PATH', self.ssl_dir / "key.pem"))

    # --- Backup paths ---
    @property
    def backup_dir(self) -> Path:
        return Path(os.environ.get('BACKUP_DIR', self.data_dir / "backups"))

    @property
    def temp_dir(self) -> Path: # General temporary directory within data_dir
        return self.data_dir / "temp"

    @property
    def archive_backup_dir(self) -> Path:
        return self.backup_dir / "archive"

    # --- GPG paths ---
    @property
    def gpg_home_dir(self) -> Path:
        # CRITICAL CHANGE: GPG home directory is now isolated within app's data folder
        return Path(os.environ.get('GPG_HOME_DIR', self.data_dir / "gpg"))

    @property
    def gpg_keys_dir(self) -> Path:
        # This property might not be strictly necessary as gnupg manages its own structure
        # within gpg_home_dir, but keeping it for consistency if you use it elsewhere.
        return self.gpg_home_dir / "keys"

    # --- Logging paths ---
    @property
    def log_dir(self) -> Path:
        return self._log_dir_path

    @property
    def log_file(self) -> Path:
        return self.log_dir / "app.log"

    @property
    def error_log_file(self) -> Path:
        return self.log_dir / "error.log"

    @property
    def backup_log_file(self) -> Path:
        return self.log_dir / "backup.log"

    @property
    def gpg_log_file(self) -> Path: # ADDED: GPG specific log file
        return self.log_dir / "gpg_backup.log"

    # --- Utility methods ---
    def _ensure_directories(self):
        """Ensures all necessary directories exist."""
        # Create core directories first, as others depend on them
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        dirs_to_create = [
            self.backup_dir,
            self.temp_dir,
            self.archive_backup_dir,
            self.ssl_dir,
            self.static_dir,
            self.templates_dir,
            self.gpg_home_dir # Ensure GPG home dir is created
        ]
        for directory in dirs_to_create:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"Warning: Cannot create directory {directory} - permission denied")
            except Exception as e:
                print(f"Warning: Failed to create directory {directory}: {str(e)}")

    def validate_paths(self) -> Dict[str, bool]:
        """Validates the existence of critical files and directories."""
        results = {
            'app_root_exists': self.app_root.is_dir(),
            'data_dir_exists': self.data_dir.is_dir(),
            'backup_dir_exists': self.backup_dir.is_dir(),
            'log_dir_exists': self.log_dir.is_dir(),
            'ssl_dir_exists': self.ssl_dir.is_dir(),
            'static_dir_exists': self.static_dir.is_dir(),
            'templates_dir_exists': self.templates_dir.is_dir(),
            'gpg_home_dir_exists': self.gpg_home_dir.is_dir(),
            'temp_dir_exists': self.temp_dir.is_dir(), # Added for completeness
            'archive_backup_dir_exists': self.archive_backup_dir.is_dir() # Added for completeness
        }
        
        files_to_check = {
            'database_file': self.database_file,
            'log_file': self.log_file,
            'error_log_file': self.error_log_file,
            'backup_log_file': self.backup_log_file,
            'gpg_log_file': self.gpg_log_file, # Corrected line
            'ssl_cert_file': self.ssl_cert_file,
            'ssl_key_file': self.ssl_key_file
        }
        results.update({f"{k}_exists": v.exists() for k, v in files_to_check.items()})
        return results

    def get_backup_filename(self, backup_type="regular", timestamp=None) -> str:
        # This method is fine as is
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{backup_type}_{timestamp}.db"

    def get_gpg_backup_filename(self, original_filename: str) -> str:
        # This method is fine as is
        return f"{original_filename}.gpg"

    def cleanup_old_backups(self, max_age_days=30) -> int:
        # This method is fine as is
        cutoff = datetime.now() - timedelta(days=max_age_days)
        count = 0
        if not self.backup_dir.exists():
            return 0
        try:
            for f in self.backup_dir.glob("backup_*.db*"):
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink()
                    count += 1
        except Exception as e:
            print(f"Error during backup cleanup: {e}")
        return count