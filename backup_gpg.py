# /home/chris/flask-ssl-backup-app/backup_gpg.py

import subprocess
import os
import logging
from pathlib import Path
from typing import Optional, List

# No need to import config or app_paths globally here if passed via __init__
# from config import app_paths, get_config

class GPGBackup:
    def __init__(self, config=None):
        """
        Initializes GPG backup utility.
        'config' is expected to be Flask's app.config dictionary.
        """
        self.config = config # This will now be Flask's app.config

        # --- FIX: Retrieve AppPaths instance correctly from config ---
        self.app_paths = self.config.get('APP_PATHS')
        if not self.app_paths:
            raise ValueError("AppPaths instance not found in Flask app config. "
                             "Ensure app.config['APP_PATHS'] is set in your app factory.")

        # --- FIX: Access GPG_HOME_DIR from the AppPaths instance ---
        # And ensure it's a Path object
        self.gpg_home_dir = self.app_paths.gpg_home_dir
        self.backup_dir = self.app_paths.backup_dir # Ensure backup_dir is also accessed correctly

        # Ensure GPG home directory exists
        self.gpg_home_dir.mkdir(parents=True, exist_ok=True)

        # --- Access other GPG-related settings from config ---
        self.gpg_binary_path = self.config.get('GPG_BINARY_PATH', 'gpg')
        self.gpg_keyserver = self.config.get('GPG_KEYSERVER', 'hkps://keys.openpgp.org')
        self.recipient_email = self.config.get('GPG_RECIPIENT_EMAIL') # Assume this is in your config

        self.logger = self._setup_logging()
        self.logger.info(f"GPGBackup initialized. GPG Home: {self.gpg_home_dir}, Binary: {self.gpg_binary_path}")


    def _setup_logging(self):
        """Setup logging for GPG backup operations."""
        logger = logging.getLogger('gpg_backup')
        log_level_str = self.config.get('LOG_LEVEL', 'INFO')
        logger.setLevel(getattr(logging, log_level_str.upper(), logging.INFO))

        if not logger.handlers:
            # Use app_paths for log file
            handler = logging.FileHandler(self.app_paths.gpg_log_file) # Assuming AppPaths has gpg_log_file
            log_format = self.config.get('LOG_FORMAT', '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
            formatter = logging.Formatter(log_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.addHandler(logging.StreamHandler())
        return logger

    def _run_gpg_command(self, args: List[str], input_data: Optional[bytes] = None) -> subprocess.CompletedProcess:
        """Helper to run GPG commands."""
        command = [
            str(self.gpg_binary_path),
            '--homedir', str(self.gpg_home_dir),
            '--batch', '--yes' # Non-interactive, auto-confirm
        ] + args
        self.logger.debug(f"Running GPG command: {' '.join(command)}")
        try:
            process = subprocess.run(
                command,
                input=input_data,
                capture_output=True,
                text=True, # Decode stdout/stderr as text
                check=True # Raise CalledProcessError for non-zero exit codes
            )
            self.logger.debug(f"GPG stdout: {process.stdout.strip()}")
            if process.stderr:
                self.logger.warning(f"GPG stderr: {process.stderr.strip()}")
            return process
        except subprocess.CalledProcessError as e:
            self.logger.error(f"GPG command failed: {e}")
            self.logger.error(f"GPG stdout: {e.stdout.strip()}")
            self.logger.error(f"GPG stderr: {e.stderr.strip()}")
            raise
        except FileNotFoundError:
            self.logger.error(f"GPG binary not found at {self.gpg_binary_path}. Please check your configuration.")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while running GPG: {e}")
            raise

    def import_key(self, key_data: str) -> bool:
        """Imports a public key from string data."""
        try:
            self._run_gpg_command(['--import'], input_data=key_data.encode('utf-8'))
            self.logger.info("GPG public key imported successfully.")
            return True
        except Exception:
            self.logger.error("Failed to import GPG public key.")
            return False

    def receive_key_from_keyserver(self, key_id: str) -> bool:
        """Receives a public key from a configured keyserver."""
        try:
            self._run_gpg_command(['--keyserver', self.gpg_keyserver, '--recv-keys', key_id])
            self.logger.info(f"GPG public key {key_id} received from keyserver {self.gpg_keyserver}.")
            return True
        except Exception:
            self.logger.error(f"Failed to receive GPG public key {key_id} from keyserver {self.gpg_keyserver}.")
            return False

    def encrypt_file(self, input_file_path: Path, output_file_path: Optional[Path] = None, recipient: Optional[str] = None) -> Optional[Path]:
        """
        Encrypts a file using GPG.

        Args:
            input_file_path: The path to the file to encrypt.
            output_file_path: The desired path for the encrypted output. If None,
                              it will be input_file_path with a .gpg extension in backup_dir.
            recipient: The email address or key ID of the recipient. Defaults to self.recipient_email.

        Returns:
            The path to the encrypted file, or None if encryption failed.
        """
        if not input_file_path.exists():
            self.logger.error(f"Input file for encryption not found: {input_file_path}")
            return None

        actual_recipient = recipient or self.recipient_email
        if not actual_recipient:
            self.logger.error("No GPG recipient specified for encryption.")
            return None

        if output_file_path is None:
            # Construct default output path in the backup directory
            output_file_path = self.backup_dir / (input_file_path.name + '.gpg')

        args = ['--encrypt', '--recipient', actual_recipient, '--output', str(output_file_path), str(input_file_path)]

        try:
            self._run_gpg_command(args)
            self.logger.info(f"File encrypted successfully: {output_file_path}")
            return output_file_path
        except Exception:
            self.logger.error(f"Failed to encrypt file: {input_file_path}")
            # Clean up potentially partial or corrupted output file
            if output_file_path.exists():
                try:
                    output_file_path.unlink()
                except OSError as e:
                    self.logger.warning(f"Could not delete partial encrypted file {output_file_path}: {e}")
            return None

    def decrypt_file(self, input_file_path: Path, output_file_path: Optional[Path] = None) -> Optional[Path]:
        """
        Decrypts a GPG encrypted file.

        Args:
            input_file_path: The path to the .gpg file to decrypt.
            output_file_path: The desired path for the decrypted output. If None,
                              it will be input_file_path with .gpg suffix removed in temp_dir.

        Returns:
            The path to the decrypted file, or None if decryption failed.
        """
        if not input_file_path.exists():
            self.logger.error(f"Input file for decryption not found: {input_file_path}")
            return None

        if not input_file_path.suffix == '.gpg':
            self.logger.warning(f"File {input_file_path} does not have a .gpg extension. Attempting to decrypt anyway.")

        if output_file_path is None:
            # Construct default output path in the temporary directory
            base_name = input_file_path.name
            if base_name.endswith('.gpg'):
                base_name = base_name[:-4] # Remove .gpg suffix
            output_file_path = self.app_paths.temp_dir / base_name # Use app_paths.temp_dir

        args = ['--decrypt', '--output', str(output_file_path), str(input_file_path)]

        try:
            self._run_gpg_command(args)
            self.logger.info(f"File decrypted successfully: {output_file_path}")
            return output_file_path
        except Exception:
            self.logger.error(f"Failed to decrypt file: {input_file_path}")
            if output_file_path.exists():
                try:
                    output_file_path.unlink()
                except OSError as e:
                    self.logger.warning(f"Could not delete partial decrypted file {output_file_path}: {e}")
            return None

    def export_public_key(self, key_id: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Exports a public key to a file.
        """
        if output_path is None:
            output_path = self.gpg_home_dir / f"{key_id}_public.asc"

        args = ['--armor', '--export', key_id, '--output', str(output_path)]
        try:
            self._run_gpg_command(args)
            self.logger.info(f"Public key {key_id} exported to {output_path}")
            return output_path
        except Exception:
            self.logger.error(f"Failed to export public key {key_id}.")
            return None

    def export_private_key(self, key_id: str, output_path: Optional[Path] = None, passphrase: Optional[str] = None) -> Optional[Path]:
        """
        Exports a private key to a file. Requires a passphrase.
        """
        if output_path is None:
            output_path = self.gpg_home_dir / f"{key_id}_private.asc"

        args = ['--armor', '--export-secret-key', key_id, '--output', str(output_path)]
        if passphrase:
            # Passphrase can be provided via --passphrase-fd 0 and stdin, or --passphrase-file
            # For simplicity, if not directly user-facing, you might use a file or env var.
            # For interactive/secure use, consider pinentry.
            self.logger.warning("Exporting private key with direct passphrase is insecure. Consider pinentry.")
            args.extend(['--passphrase', passphrase])
        else:
            self.logger.error("Passphrase is required for private key export.")
            return None

        try:
            self._run_gpg_command(args)
            self.logger.info(f"Private key {key_id} exported to {output_path}")
            return output_path
        except Exception:
            self.logger.error(f"Failed to export private key {key_id}.")
            return None

    def list_keys(self, secret: bool = False) -> List[str]:
        """
        Lists public or private keys.
        Returns a list of key IDs or fingerprints.
        """
        args = ['--list-keys']
        if secret:
            args = ['--list-secret-keys']

        try:
            result = self._run_gpg_command(args)
            keys = []
            for line in result.stdout.splitlines():
                if line.strip().startswith('pub') or line.strip().startswith('sec'):
                    # Extract fingerprint from line, it's usually the second line after pub/sec
                    # Example: pub   rsa4096 2023-01-01 [SC]
                    #              DEADBEEF1234567890ABCDEF1234567890ABCDEF
                    next_line_index = result.stdout.splitlines().index(line) + 1
                    if next_line_index < len(result.stdout.splitlines()):
                        fingerprint_line = result.stdout.splitlines()[next_line_index].strip()
                        if fingerprint_line:
                            keys.append(fingerprint_line.replace(' ', '')) # Remove spaces from fingerprint
            return keys
        except Exception:
            self.logger.error("Failed to list GPG keys.")
            return []


# Example usage for standalone testing (if this file is run directly)
if __name__ == "__main__":
    # Create a dummy config object that mimics Flask's app.config for testing
    class DummyConfigDict(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            from paths import AppPaths # Import AppPaths here for CLI context
            self['APP_PATHS'] = AppPaths()
            self['GPG_BINARY_PATH'] = os.environ.get('GPG_BINARY_PATH', '/usr/bin/gpg')
            self['GPG_KEYSERVER'] = os.environ.get('GPG_KEYSERVER', 'hkps://keys.openpgp.org')
            self['GPG_RECIPIENT_EMAIL'] = os.environ.get('GPG_RECIPIENT_EMAIL') # Set this env var for testing
            self['LOG_LEVEL'] = 'DEBUG'
            self['LOG_FORMAT'] = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'

    cli_config = DummyConfigDict()

    # Create dummy files for testing
    test_data_dir = cli_config['APP_PATHS'].data_dir / "test_gpg"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    test_file_path = test_data_dir / "test_document.txt"
    test_encrypted_path = test_data_dir / "test_document.txt.gpg"
    test_decrypted_path = test_data_dir / "test_document_decrypted.txt"

    with test_file_path.open("w") as f:
        f.write("This is a test document for GPG encryption.")

    print(f"Test file created: {test_file_path}")

    gpg_manager = GPGBackup(config=cli_config)

    # --- Test GPG Operations ---
    recipient_email = cli_config['GPG_RECIPIENT_EMAIL']
    if not recipient_email:
        print("Set GPG_RECIPIENT_EMAIL environment variable to test encryption/decryption.")
        sys.exit(1)

    print("\n--- Listing Keys ---")
    public_keys = gpg_manager.list_keys()
    secret_keys = gpg_manager.list_keys(secret=True)
    print(f"Public Keys: {public_keys}")
    print(f"Secret Keys: {secret_keys}")

    # Check if recipient key exists, if not, try to receive it
    if recipient_email not in public_keys: # This check might be simplified for demo
        print(f"\nRecipient key '{recipient_email}' not found. Attempting to receive from keyserver...")
        # For a real email, GPG might fetch it by email. For a key ID, use the ID.
        # This part assumes GPG_RECIPIENT_EMAIL is also a key ID or linked to a key on keyserver.
        # Otherwise, you might need to manually import a key.
        if not gpg_manager.receive_key_from_keyserver(recipient_email):
             print(f"Could not receive key for {recipient_email}. Please ensure it's on the keyserver or import manually.")
             # Fallback to importing a dummy key or skip encryption test
             sys.exit(1) # Exit if key not found and cannot be received

    print(f"\n--- Encrypting {test_file_path.name} ---")
    encrypted_file = gpg_manager.encrypt_file(test_file_path, recipient=recipient_email)
    if encrypted_file:
        print(f"Encrypted to: {encrypted_file}")
    else:
        print("Encryption failed.")

    if encrypted_file:
        print(f"\n--- Decrypting {encrypted_file.name} ---")
        decrypted_file = gpg_manager.decrypt_file(encrypted_file)
        if decrypted_file:
            print(f"Decrypted to: {decrypted_file}")
            with decrypted_file.open("r") as f:
                print(f"Decrypted content: '{f.read().strip()}'")
            # Verify content
            with test_file_path.open("r") as f_orig, decrypted_file.open("r") as f_dec:
                if f_orig.read() == f_dec.read():
                    print("Decrypted content matches original.")
                else:
                    print("Decrypted content DOES NOT match original.")
        else:
            print("Decryption failed.")

    # Clean up test files
    for f in [test_file_path, test_encrypted_path, test_decrypted_path]:
        if f.exists():
            f.unlink()
    if test_data_dir.exists() and not list(test_data_dir.iterdir()): # Only remove if empty
        test_data_dir.rmdir()
    print("\nTest files cleaned up.")