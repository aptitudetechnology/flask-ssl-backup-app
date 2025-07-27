import subprocess
from pathlib import Path
import logging # Import logging
from typing import List, Dict, Any

# Assuming your config is accessible for logging paths etc.
from config import get_config 

class GPGBackup:
    def __init__(self, gpg_recipient: str):
        self.recipient = gpg_recipient
        self.config = get_config() # Initialize config to access paths and log level
        self.logger = self._setup_logging() # Setup logging for this class
        self.keyserver = "keyserver.ubuntu.com" # Use the working keyserver


    def _setup_logging(self):
        """Setup logging for GPG operations"""
        logger = logging.getLogger('gpg_backup')
        logger.setLevel(getattr(logging, self.config.LOG_LEVEL))

        if not logger.handlers:
            handler = logging.FileHandler(self.config.paths.gpg_log_file)
            formatter = logging.Formatter(self.config.LOG_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger


    def search_keys(self, email: str) -> List[Dict[str, Any]]:
        """
        Searches for GPG public keys on the configured keyserver for the given email.
        Parses the GPG output to return a list of dictionaries.
        """
        self.logger.info(f"Searching GPG keys for email: {email} on keyserver: {self.keyserver}")
        try:
            # Command to search for keys
            # --with-colons provides machine-readable output which is easier to parse
            command = [
                "gpg", "--keyserver", self.keyserver,
                "--search-keys", "--with-colons", email
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=False) # text=True decodes output

            if result.returncode != 0:
                self.logger.error(f"GPG search failed (return code {result.returncode}): {result.stderr.strip()}")
                if "no user ID matching" in result.stderr:
                    self.logger.info(f"No GPG keys found for {email} on {self.keyserver}.")
                return []

            # Parse the output
            # GPG --with-colons output format is complex, we'll extract keyid and uids
            found_keys = []
            for line in result.stdout.splitlines():
                if line.startswith("pub:"):
                    parts = line.split(":")
                    if len(parts) >= 5: # Ensure enough parts for keyid and date
                        key_id_full = parts[4] # Full key ID/fingerprint part
                        # Take the last 8 or 16 hex chars for the common key ID display
                        key_id_short = key_id_full[-16:] if len(key_id_full) >= 16 else key_id_full

                        # Attempt to get creation date if available (part 9)
                        created_date = None
                        if len(parts) >= 10 and parts[9].isdigit():
                            try:
                                created_date = datetime.fromtimestamp(int(parts[9])).isoformat()
                            except ValueError:
                                pass # Malformed timestamp

                        # Placeholder for UIDs, will be filled in a separate iteration
                        found_keys.append({
                            'key_id': key_id_short,
                            'fingerprint': key_id_full, # This might be the full fingerprint if provided
                            'uids': [], # To be populated by uid: lines
                            'created': created_date,
                            'type': parts[1], # e.g., 'pub'
                            'bits': parts[2] # e.g., '2048'
                        })
                elif line.startswith("uid:"):
                    parts = line.split(":")
                    if len(parts) >= 10 and found_keys: # Ensure enough parts and there's a key to attach to
                        uid_string = parts[9] # e.g., "Christopher Caston <chris@caston.id.au>"
                        found_keys[-1]['uids'].append(uid_string)
            
            self.logger.info(f"Successfully searched keys for {email}. Found {len(found_keys)} entries.")
            return found_keys

        except Exception as e:
            self.logger.error(f"An unexpected error occurred during GPG key search: {e}", exc_info=True)
            return []

    def import_key(self, key_id: str) -> Dict[str, Any]:
        """
        Imports a GPG public key from a keyserver.
        Returns a dictionary with import results.
        """
        self.logger.info(f"Attempting to import GPG key: {key_id} from keyserver: {self.keyserver}")
        try:
            command = [
                "gpg", "--keyserver", self.keyserver,
                "--recv-keys", key_id
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                self.logger.info(f"Successfully imported GPG key {key_id}. Output: {result.stdout.strip()}")
                return {'success': True, 'message': f"Key {key_id} imported successfully."}
            else:
                error_message = result.stderr.strip() or "Unknown error during import."
                self.logger.error(f"Failed to import GPG key {key_id} (return code {result.returncode}): {error_message}")
                return {'success': False, 'error': f"Failed to import key: {error_message}"}

        except Exception as e:
            self.logger.error(f"An unexpected error occurred during GPG key import: {e}", exc_info=True)
            return {'success': False, 'error': f"An error occurred during key import: {e}"}

    def encrypt_file(self, input_path: Path, output_path: Path):
        self.logger.info(f"Encrypting file: {input_path} to {output_path} for recipient: {self.recipient}")
        try:
            result = subprocess.run([
                "gpg", "--yes", "--output", str(output_path),
                "--encrypt", "--recipient", self.recipient,
                str(input_path)
            ], capture_output=True, text=True, check=True) # check=True will raise CalledProcessError on failure

            self.logger.info(f"GPG encryption successful for {input_path}.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"GPG encryption failed for {input_path}: {e.stderr.strip()}")
            raise RuntimeError(f"GPG encryption failed: {e.stderr.strip()}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during encryption: {e}", exc_info=True)
            raise RuntimeError(f"Encryption error: {e}")

    def decrypt_file(self, input_path: Path, output_path: Path):
        self.logger.info(f"Decrypting file: {input_path} to {output_path}")
        try:
            result = subprocess.run([
                "gpg", "--yes", "--output", str(output_path),
                "--decrypt", str(input_path)
            ], capture_output=True, text=True, check=True)

            self.logger.info(f"GPG decryption successful for {input_path}.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"GPG decryption failed for {input_path}: {e.stderr.strip()}")
            raise RuntimeError(f"GPG decryption failed: {e.stderr.strip()}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during decryption: {e}", exc_info=True)
            raise RuntimeError(f"Decryption error: {e}")