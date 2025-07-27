 tree
.
├── app.py
├── app.py.bak
├── backup_gpg.py
├── backup_gpg.py.bak
├── backup_gpg.py.bak2
├── backup_gpg.py.bak3
├── backup.py
├── backup.py.bak
├── blueprints
│   ├── backup_bp.py
│   ├── backup_bp.py.bak
│   ├── backup.py
│   └── __init__.py
├── config.py
├── config.py.bak
├── config.py.bak1
├── models.py
├── models.py.bak
├── paths.py
├── paths.py.bak
├── readme.md
├── requirements.txt
├── routes.py
├── routes.py.bak
├── routes.py.bak1
├── run-flask-backup.py
├── scripts
│   └── create_admin.py
├── ssl
│   └── gen-cert.sh
├── static
│   ├── css
│   │   └── main.css
│   └── js
│       ├── gpg-backup-modal.js
│       ├── gpg-backup-modal.js.bak
│       └── main.js
├── templates
│   ├── backup
│   │   ├── backupmodals
│   │   │   └── gpg-modal.html
│   │   └── index.html
│   ├── base.html
│   ├── customers.html
│   ├── edit_customer.html
│   └── login.html
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

12 directories, 45 files

    Key Requirements:
1. Flask app with SSL support and SQLite3 customer database
2. GPG backup system that searches Ubuntu keyserver for public keys using https://gnupg.readthedocs.io/en/latest/ - but don't try to code this now just know that it's coming in future versions. For now just focus on the customer and backup.