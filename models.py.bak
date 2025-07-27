from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import sqlite3
import os
import json
from typing import List, Dict, Optional, Any

db = SQLAlchemy()

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

class DatabaseManager:
    """Database management utilities."""
    
    @staticmethod
    def init_database(app):
        """Initialize database with tables."""
        with app.app_context():
            db.create_all()
    
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
        """Get database statistics."""
        try:
            from flask import current_app
            db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            stats = {
                'total_customers': Customer.query.count(),
                'active_customers': Customer.query.filter_by(active=True).count(),
                'inactive_customers': Customer.query.filter_by(active=False).count(),
                'database_size': os.path.getsize(db_path) if os.path.exists(db_path) else 0,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat() if os.path.exists(db_path) else None
            }
            
            return stats
        except Exception as e:
            print(f"Failed to get database stats: {e}")
            return {}