# paths.py

import os
from pathlib import Path
from typing import Optional, Dict


class AppPaths:
    @property
    def temp_dir(self) -> Path:
        """Temporary directory for backup operations"""
        return self.backup_dir / "temp"
    """Centralized path management using pathlib"""

    def __init__(self, app_root: Optional[Path] = None):
        self.app_root = Path(app_root) if app_root else Path.cwd()
        self._ensure_directories()

    # Core application paths
    @property
    def database_file(self) -> Path:
        return self.app_root / "customers.db"

    @property
    def static_dir(self) -> Path:
        return self.app_root / "static"

    @property
    def templates_dir(self) -> Path:
        return self.app_root / "templates"

    # SSL certificate paths
    @property
    def ssl_dir(self) -> Path:
        return Path(os.environ.get('SSL_CERT_DIR', self.app_root / "ssl"))

    @property
    def ssl_cert_file(self) -> Path:
        return Path(os.environ.get('SSL_CERT_PATH', self.ssl_dir / "cert.pem"))

    @property
    def ssl_key_file(self) -> Path:
        return Path(os.environ.get('SSL_KEY_PATH', self.ssl_dir / "key.pem"))

    # Backup paths
    @property
    def backup_dir(self) -> Path:
        return Path(os.environ.get('BACKUP_DIR', self.app_root / "backups"))

    @property
    def temp_backup_dir(self) -> Path:
        return self.backup_dir / "temp"

    @property
    def archive_backup_dir(self) -> Path:
        return self.backup_dir / "archive"

    # GPG paths
    @property
    def gpg_home_dir(self) -> Path:
        return Path(os.environ.get('GPG_HOME_DIR', Path.home() / ".gnupg"))

    @property
    def gpg_keys_dir(self) -> Path:
        return self.gpg_home_dir / "keys"

    # Logging paths
    @property
    def log_dir(self) -> Path:
        return Path(os.environ.get('LOG_DIR', self.app_root / "logs"))

    @property
    def log_file(self) -> Path:
        return self.log_dir / "app.log"

    @property
    def error_log_file(self) -> Path:
        return self.log_dir / "error.log"

    @property
    def backup_log_file(self) -> Path:
        return self.log_dir / "backup.log"

    # Utility methods
    def _ensure_directories(self):
        dirs = [
            self.backup_dir,
            self.temp_backup_dir,
            self.archive_backup_dir,
            self.log_dir,
            self.ssl_dir,
            self.static_dir,
            self.templates_dir
        ]
        for directory in dirs:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"Warning: Cannot create directory {directory} - permission denied")
            except Exception as e:
                print(f"Warning: Failed to create directory {directory}: {str(e)}")

    def validate_paths(self) -> Dict[str, bool]:
        dirs = {
            'backup_dir': self.backup_dir,
            'log_dir': self.log_dir,
            'ssl_dir': self.ssl_dir,
            'static_dir': self.static_dir,
            'templates_dir': self.templates_dir,
            'gpg_home_dir_exists': self.gpg_home_dir.is_dir() 
        }
        results = {k: v.exists() and v.is_dir() for k, v in dirs.items()}
        files = {
            'ssl_cert': self.ssl_cert_file,
            'ssl_key': self.ssl_key_file,
            'database': self.database_file,
            'gpg_log_file': self.gpg_log_fil
        }
        results.update({f"{k}_exists": v.exists() for k, v in files.items()})
        return results

    def get_backup_filename(self, backup_type="regular", timestamp=None) -> str:
        from datetime import datetime
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{backup_type}_{timestamp}.db"

    def get_gpg_backup_filename(self, original_filename: str) -> str:
        return f"{original_filename}.gpg"

    def cleanup_old_backups(self, max_age_days=30) -> int:
        from datetime import datetime, timedelta
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
