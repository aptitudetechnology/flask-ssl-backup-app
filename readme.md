Simple test flask application for proof of concept of gpg encrypted database backups.
It retrieves the public key from the ubuntu key server by searching via the e-mail address and giving the option of which key to download. The database is encrypted as a gpg file. The templates are jinja2.

To get started git clone this repo and then chmod +x run-flask-backup.py

./run-flask-backup.py

gen-cert.sh for generating an ssl certificate is in the ssl folder.

login: admin
password: admin123

<img width="1294" height="843" alt="Screenshot From 2025-07-27 19-19-56" src="https://github.com/user-attachments/assets/2ad1aa50-d34e-45ab-95b3-6d60081163a6" />
