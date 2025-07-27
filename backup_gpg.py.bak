# backup_gpg.py
import subprocess
from pathlib import Path

class GPGBackup:
    def __init__(self, gpg_recipient: str):
        self.recipient = gpg_recipient

    def encrypt_file(self, input_path: Path, output_path: Path):
        result = subprocess.run([
            "gpg", "--yes", "--output", str(output_path),
            "--encrypt", "--recipient", self.recipient,
            str(input_path)
        ], capture_output=True)

        if result.returncode != 0:
            raise RuntimeError(f"GPG encryption failed: {result.stderr.decode()}")

    def decrypt_file(self, input_path: Path, output_path: Path):
        result = subprocess.run([
            "gpg", "--yes", "--output", str(output_path),
            "--decrypt", str(input_path)
        ], capture_output=True)

        if result.returncode != 0:
            raise RuntimeError(f"GPG decryption failed: {result.stderr.decode()}")
