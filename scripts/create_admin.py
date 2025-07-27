"""
Script to create an admin user with username 'admin' and password 'admin123'.
Run this script from the project root: python scripts/create_admin.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import db, User
from config import get_config
from flask import Flask

# Setup Flask app and config
config = get_config()
app = Flask(__name__)
app.config.update(config.get_flask_config())
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config.paths.database_file}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if User.query.filter_by(username='admin').first():
        print("Admin user already exists.")
    else:
        admin = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_active=True,
            is_admin=True
        )
        admin.set_password('admin123')  # Assumes User model has set_password method

        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created: username='admin', password='admin123'")
