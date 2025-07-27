from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json
from typing import List, Dict, Optional, Any

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with backup records
    backup_records = db.relationship('BackupRecord', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password: str):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user instance to dictionary (excluding sensitive data)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        """Authenticate user with username and password."""
        user = cls.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            user.update_last_login()
            return user
        return None
    
    @classmethod
    def create_user(cls, username: str, email: str, password: str, 
                   first_name: str = None, last_name: str = None, 
                   is_admin: bool = False) -> 'User':
        """Create a new user."""
        user = cls(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


class BackupRecord(db.Model):
    """Model for tracking database backups."""
    
    __tablename__ = 'backup_records'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    backup_type = db.Column(db.String(50), nullable=False)  # 'regular', 'encrypted', 'pre_restore', etc.
    description = db.Column(db.Text, nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)  # Size in bytes
    file_path = db.Column(db.String(500), nullable=True)  # Full path to backup file
    checksum = db.Column(db.String(64), nullable=True)  # SHA256 checksum for integrity
    is_encrypted = db.Column(db.Boolean, default=False)
    compression_type = db.Column(db.String(20), nullable=True)  # 'gzip', 'zip', etc.
    status = db.Column(db.String(20), default='completed')  # 'in_progress', 'completed', 'failed'
    error_message = db.Column(db.Text, nullable=True)
    
    # Foreign key to user who created the backup
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<BackupRecord {self.filename}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert backup record to dictionary."""
        return {
            'id': self.id,
            'filename': self.filename,
            'backup_type': self.backup_type,
            'description': self.description,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'checksum': self.checksum,
            'is_encrypted': self.is_encrypted,
            'compression_type': self.compression_type,
            'status': self.status,
            'error_message': self.error_message,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'user': self.user.username if self.user else None
        }
    
    def mark_completed(self, file_size: int = None, checksum: str = None):
        """Mark backup as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if file_size:
            self.file_size = file_size
        if checksum:
            self.checksum = checksum
        db.session.commit()
    
    def mark_failed(self, error_message: str):
        """Mark backup as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def create_backup_record(cls, filename: str, backup_type: str, user_id: int = None,
                           description: str = None, file_path: str = None) -> 'BackupRecord':
        """Create a new backup record."""
        record = cls(
            filename=filename,
            backup_type=backup_type,
            description=description,
            file_path=file_path,
            user_id=user_id,
            status='in_progress'
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    @classmethod
    def get_recent_backups(cls, limit: int = 10) -> List['BackupRecord']:
        """Get recent backup records."""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_backup_stats(cls) -> Dict[str, Any]:
        """Get backup statistics."""
        total_backups = cls.query.count()
        successful_backups = cls.query.filter_by(status='completed').count()
        failed_backups = cls.query.filter_by(status='failed').count()
        encrypted_backups = cls.query.filter_by(is_encrypted=True).count()
        
        # Calculate total backup size
        total_size = db.session.query(db.func.sum(cls.file_size)).filter(
            cls.status == 'completed'
        ).scalar() or 0
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'encrypted_backups': encrypted_backups,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size > 0 else 0
        }


class Customer(db.Model):
    """Customer model for storing customer information."""
    
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    company = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert customer instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'company': self.company,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create customer instance from dictionary."""
        customer = cls()
        for key, value in data.items():
            if hasattr(customer, key) and key not in ['id', 'created_at', 'updated_at']:
                setattr(customer, key, value)
        return customer


class CustomerService:
    """Service class for customer database operations."""
    
    @staticmethod
    def create_customer(name: str, email: str, phone: str = None, 
                       address: str = None, company: str = None, 
                       notes: str = None) -> Customer:
        """Create a new customer."""
        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            address=address,
            company=company,
            notes=notes
        )
        db.session.add(customer)
        db.session.commit()
        return customer
    
    @staticmethod
    def get_customer_by_id(customer_id: int) -> Optional[Customer]:
        """Get customer by ID."""
        return Customer.query.get(customer_id)
    
    @staticmethod
    def get_customer_by_email(email: str) -> Optional[Customer]:
        """Get customer by email address."""
        return Customer.query.filter_by(email=email).first()
    
    @staticmethod
    def get_all_customers(active_only: bool = True) -> List[Customer]:
        """Get all customers, optionally filtering by active status."""
        query = Customer.query
        if active_only:
            query = query.filter_by(active=True)
        return query.order_by(Customer.name).all()
    
    @staticmethod
    def update_customer(customer_id: int, **kwargs) -> Optional[Customer]:
        """Update customer information."""
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        
        for key, value in kwargs.items():
            if hasattr(customer, key) and key not in ['id', 'created_at']:
                setattr(customer, key, value)
        
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        return customer
    
    @staticmethod
    def delete_customer(customer_id: int, soft_delete: bool = True) -> bool:
        """Delete customer (soft delete by default)."""
        customer = Customer.query.get(customer_id)
        if not customer:
            return False
        
        if soft_delete:
            customer.active = False
            customer.updated_at = datetime.utcnow()
            db.session.commit()
        else:
            db.session.delete(customer)
            db.session.commit()
        
        return True
    
    @staticmethod
    def search_customers(query: str) -> List[Customer]:
        """Search customers by name, email, or company."""
        search_pattern = f"%{query}%"
        return Customer.query.filter(
            db.or_(
                Customer.name.ilike(search_pattern),
                Customer.email.ilike(search_pattern),
                Customer.company.ilike(search_pattern)
            )
        ).filter_by(active=True).order_by(Customer.name).all()
    
    @staticmethod
    def get_customer_count() -> int:
        """Get total number of active customers."""
        return Customer.query.filter_by(active=True).count()


class UserService:
    """Service class for user operations."""
    
    @staticmethod
    def create_default_admin():
        """Create default admin user if no users exist."""
        if User.query.count() == 0:
            admin = User.create_user(
                username='admin',
                email='admin@localhost',
                password='admin123',
                first_name='System',
                last_name='Administrator',
                is_admin=True
            )
            return admin
        return None
    
    @staticmethod
    def get_all_users(active_only: bool = True) -> List[User]:
        """Get all users."""
        query = User.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(User.username).all()
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username."""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> Optional[User]:
        """Update user information."""
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Handle password separately
        if 'password' in kwargs:
            user.set_password(kwargs.pop('password'))
        
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ['id', 'created_at', 'password_hash']:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return user


class DatabaseManager:
    """Database management utilities."""
    
    @staticmethod
    def init_database(app):
        """Initialize database with tables."""
        with app.app_context():
            db.create_all()
            # Create default admin user
            UserService.create_default_admin()
    
    @staticmethod
    def backup_database(backup_path: str) -> bool:
        """Create a backup of the SQLite database."""
        try:
            from flask import current_app
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            if not os.path.exists(db_path):
                return False
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.dirname(backup_path)
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copy database file
            import shutil
            shutil.copy2(db_path, backup_path)
            return True
            
        except Exception as e:
            print(f"Database backup failed: {e}")
            return False
    
    @staticmethod
    def restore_database(backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            from flask import current_app
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            if not os.path.exists(backup_path):
                return False
            
            # Stop any active connections
            db.session.close()
            
            # Replace current database with backup
            import shutil
            shutil.copy2(backup_path, db_path)
            return True
            
        except Exception as e:
            print(f"Database restore failed: {e}")
            return False
    
    @staticmethod
    def export_customers_json(file_path: str) -> bool:
        """Export all customers to JSON file."""
        try:
            customers = CustomerService.get_all_customers(active_only=False)
            customer_data = [customer.to_dict() for customer in customers]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(customer_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"JSON export failed: {e}")
            return False
    
    @staticmethod
    def import_customers_json(file_path: str) -> bool:
        """Import customers from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                customer_data = json.load(f)
            
            for data in customer_data:
                # Check if customer already exists
                existing = CustomerService.get_customer_by_email(data.get('email'))
                if not existing:
                    customer = Customer.from_dict(data)
                    db.session.add(customer)
            
            db.session.commit()
            return True
        except Exception as e:
            print(f"JSON import failed: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            from flask import current_app
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            stats = {
                # Customer stats
                'total_customers': Customer.query.count(),
                'active_customers': Customer.query.filter_by(active=True).count(),
                'inactive_customers': Customer.query.filter_by(active=False).count(),
                
                # User stats
                'total_users': User.query.count(),
                'active_users': User.query.filter_by(is_active=True).count(),
                'admin_users': User.query.filter_by(is_admin=True).count(),
                
                # Backup stats
                'backup_records': BackupRecord.query.count(),
                'successful_backups': BackupRecord.query.filter_by(status='completed').count(),
                'failed_backups': BackupRecord.query.filter_by(status='failed').count(),
                
                # Database file stats
                'database_size': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat() if os.path.exists(db_path) else None
            }
            
            return stats
        except Exception as e:
            print(f"Failed to get database stats: {e}")
            return {}