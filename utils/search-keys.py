
import sys
import logging
from pathlib import Path
from config import get_config
from gpg_backup import GPGBackup

def main():
    if len(sys.argv) < 2:
        print("Usage: python search-keys.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    config = get_config()
    gpg_backup = GPGBackup(config)

    keys = gpg_backup.search_keys(email)
    if not keys:
        print(f"No keys found for {email}.")
        sys.exit(0)

    print(f"Found {len(keys)} key(s) for {email}:")
    for key in keys:
        print(f"  Key ID: {key.get('key_id')}")
        print(f"  UIDs: {key.get('uids')}")
        print(f"  Created: {key.get('created')}")
        print(f"  Length: {key.get('length')}")
        print(f"  Algo: {key.get('algo')}")
        if 'fingerprint' in key:
            print(f"  Fingerprint: {key['fingerprint']}")
        print()

if __name__ == "__main__":
    main()
