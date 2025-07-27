.
├── app.py
├── backup_gpg.py
├── backup.py
├── config.py
├── models.py
├── readme.md
├── requirements.txt
├── ssl
│   └── gen-cert.sh
├── static
│   ├── css
│   │   └── style.css
│   └── js
│       ├── gpg-backup-modal.js
│       └── main.js
├── templates
│   ├── backup
│   │   ├── index.html
│   │   └── modals
│   │       └── gpg-modal.html
│   ├── backup.html
│   ├── base.html
│   └── customers.html
├── tests
│   ├── __init__.py
│   ├── test_app.py
│   ├── test_backup.py
│   └── test_gpg.py
└── utils
    ├── database.py
    ├── encryption.py
    ├── __init__.py
    └── validators.py


    Key Requirements:
1. Flask app with SSL support and SQLite3 customer database
2. GPG backup system that searches Ubuntu keyserver for public keys using https://gnupg.readthedocs.io/en/latest/ - but don't try to code this now just know that it's coming in future versions. For now just focus on the customer and backup.