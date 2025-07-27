# backup_gpg.py

import gnupg
import logging
from pathlib import Path
import os
from typing import Optional

class GPGBackup:
    def __init__(self, config):
        self.config = config
        self.gpg_home_dir = config.paths.gpg_home_dir
        self.gnupg_bin_path = config.GPG_BINARY_PATH # Make sure this is correctly set in your config.py
        self.gpg = self._initialize_gpg()
        self.logger = self._setup_logging()

    def _initialize_gpg(self):
        # Ensure the GPG home directory exists
        self.gpg_home_dir.mkdir(parents=True, exist_ok=True)
        return gnupg.GPG(gnupghome=str(self.gpg_home_dir), binary=self.gnupg_bin_path)

    def _setup_logging(self):
        # Setup specific logger for GPG operations
        logger = logging.getLogger('gpg_backup_logger')
        logger.setLevel(self.config.LOG_LEVEL)
        if not logger.handlers: # Prevent adding multiple handlers if called multiple times
            handler = logging.FileHandler(self.config.paths.gpg_log_file)
            formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.addHandler(logging.StreamHandler()) # Also log to console
        return logger

    def create_encrypted_backup(self, input_filepath: Path, recipient_email: str) -> Optional[Path]: # Add this method
        """
        Encrypts the given file using the recipient's public GPG key.
        Returns the path to the encrypted file or None on failure.
        """
        if not input_filepath.exists():
            self.logger.error(f"Input file for GPG encryption not found: {input_filepath}")
            return None

        if not recipient_email:
            self.logger.error("GPG recipient email not provided for encryption.")
            return None

        output_filepath = self.config.paths.backup_dir / self.config.paths.get_gpg_backup_filename(input_filepath.name)

        self.logger.info(f"Encrypting {input_filepath} for {recipient_email} to {output_filepath}")

        # Search for the key if not already present
        if not self.gpg.list_keys(False, keys=recipient_email):
            self.logger.info(f"Recipient key for {recipient_email} not found locally. Attempting to search and import from keyserver.")
            search_result = self.gpg.search_keys(recipient_email, keyserver=self.config.GPG_KEYSERVER)
            if search_result:
                fingerprints = [key['fingerprint'] for key in search_result]
                self.logger.info(f"Found keys: {fingerprints}. Importing first key.")
                import_result = self.gpg.recv_keys(self.config.GPG_KEYSERVER, *fingerprints[:1]) # Import only the first found key
                if import_result.results:
                    self.logger.info(f"Key imported: {import_result.results[0].get('fingerprint', 'N/A')}")
                else:
                    self.logger.warning(f"Failed to import key for {recipient_email}: {import_result.stderr or import_result.status}")
                    return None
            else:
                self.logger.warning(f"No public GPG key found for {recipient_email} on keyserver: {self.config.GPG_KEYSERVER}")
                return None

        try:
            with open(input_filepath, 'rb') as f:
                status = self.gpg.encrypt_file(f, recipients=[recipient_email], output=str(output_filepath), always_trust=True)

            if status.ok:
                self.logger.info(f"GPG encryption successful: {output_filepath}")
                return output_filepath
            else:
                self.logger.error(f"GPG encryption failed for {input_filepath.name}: {status.stderr}")
                return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during GPG encryption: {e}")
            return None

    # You might also have methods like 'decrypt_backup' or 'import_key' here
    # Example for importing key from file
    def import_key_from_file(self, key_filepath: Path) -> bool:
        """
        Imports a public GPG key from a file.
        """
        if not key_filepath.exists():
            self.logger.error(f"Key file not found: {key_filepath}")
            return False
        try:
            with open(key_filepath, 'rb') as f:
                import_result = self.gpg.import_keys(f.read())
            if import_result.count > 0:
                self.logger.info(f"Successfully imported {import_result.count} key(s) from {key_filepath}")
                return True
            else:
                self.logger.warning(f"No keys imported from {key_filepath}: {import_result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error importing key from file {key_filepath}: {e}")
            return False

    # Example for searching and importing a key from a keyserver
    def search_and_import_key(self, email: str) -> bool:
        """
        Searches for a public key on a keyserver and imports it.
        """
        try:
            self.logger.info(f"Searching for GPG keys for email: {email} on keyserver: {self.config.GPG_KEYSERVER}")
            search_result = self.gpg.search_keys(email, keyserver=self.config.GPG_KEYSERVER)

            if search_result:
                fingerprints = [key['fingerprint'] for key in search_result]
                self.logger.info(f"Found {len(fingerprints)} key(s) for {email}. Importing...")
                import_result = self.gpg.recv_keys(self.config.GPG_KEYSERVER, *fingerprints)

                if import_result.results:
                    self.logger.info(f"Successfully imported {import_result.count} key(s).")
                    return True
                else:
                    self.logger.warning(f"Failed to import keys: {import_result.stderr}")
                    return False
            else:
                self.logger.warning(f"No keys found for {email} on keyserver {self.config.GPG_KEYSERVER}")
                return False
        except Exception as e:
            self.logger.error(f"Error searching/importing GPG key: {e}")
            return False