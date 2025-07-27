from pathlib import Path

class DatabaseBackup:
    def __init__(self, config):
        self.config = config

    def create_backup(self):
        import logging
        try:
            backup_dir = Path(self.config['BACKUP_DIR'])
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / 'backup.sql'
            backup_path.write_text('-- SQL BACKUP DATA --')
            logging.info(f"Backup created at: {backup_path}")
            return backup_path
        except Exception as e:
            logging.error(f"Error in create_backup: {e}")
            raise
