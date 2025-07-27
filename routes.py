from flask import (
    render_template, request, jsonify, session, redirect, url_for,
    flash, current_app # Added current_app
)
from functools import wraps
from pathlib import Path
import sqlite3
from datetime import datetime
from models import db, User, BackupRecord, CustomerService  # Import models
# backup, backup_gpg, config are now accessed via current_app.extensions or current_app.config

# --- Helper Functions and Decorators (Consider moving login_required to a common module) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Register core routes (you can integrate these directly into app.py or keep them here) ---
# This function's signature changes because managers are no longer passed directly
def register_core_routes(app): # Removed config, db, backup_manager, gpg_backup from params

    @app.route('/')
    def index():
        """Home page"""
        return render_template('base.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login with modern SQLAlchemy"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            if username and password:
                user = User.query.filter_by(username=username).first()
                if user and user.check_password(password):  # Assuming this method exists
                    session['user_id'] = user.id
                    session['username'] = user.username
                    flash('Login successful', 'success')
                    return redirect(url_for('customers'))
                else:
                    flash('Invalid credentials', 'error')
            else:
                flash('Please provide username and password', 'error')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """User logout"""
        session.clear()
        flash('Logged out successfully', 'info')
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """User dashboard with backup statistics"""
        try:
            # Access managers and config from current_app.extensions and current_app.config
            backup_manager = current_app.extensions.get('backup_manager')
            app_config = current_app.config.get('APP_CONFIG')

            backup_stats = {}
            recent_backups = []
            if backup_manager:
                backup_stats = backup_manager.get_backup_stats()
                recent_backups = backup_manager.list_backups()[:5]
            
            db_info = {}
            if app_config and app_config.paths and app_config.paths.database_file:
                 db_info = get_database_info(app_config.paths.database_file)
            
            health_status = check_system_health(app_config) # Pass app_config if needed

            return render_template('dashboard.html',
                                   backup_stats=backup_stats,
                                   recent_backups=recent_backups,
                                   db_info=db_info,
                                   health_status=health_status)

        except Exception as e:
            current_app.logger.error(f"Dashboard error: {str(e)}")
            flash('Error loading dashboard', 'error')
            return render_template('dashboard.html',
                                   backup_stats={},
                                   recent_backups=[],
                                   db_info={},
                                   health_status={})

    @app.route('/customers', methods=['GET', 'POST'])
    @login_required
    def customers():
        """Customer list page and add customer handler"""
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            company = request.form.get('company')
            notes = request.form.get('notes')
            # Basic validation
            if not name or not email:
                flash('Name and email are required.', 'danger')
            elif CustomerService.get_customer_by_email(email):
                flash('A customer with this email already exists.', 'warning')
            else:
                CustomerService.create_customer(
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                    company=company,
                    notes=notes
                )
                flash('Customer added successfully!', 'success')
            return redirect(url_for('customers'))
        # GET: show list
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        if search:
            customer_list = CustomerService.search_customers(search)
        else:
            active_only = (status != 'inactive')
            customer_list = CustomerService.get_all_customers(active_only=active_only)
        return render_template('customers.html', customers=customer_list)

    @app.route('/customers/<int:customer_id>/delete', methods=['POST'])
    @login_required
    def delete_customer(customer_id):
        success = CustomerService.delete_customer(customer_id, soft_delete=True)
        if success:
            flash('Customer deactivated successfully.', 'success')
        else:
            flash('Customer not found.', 'danger')
        return redirect(url_for('customers'))

    @app.route('/api/customers/<int:customer_id>')
    @login_required
    def api_get_customer(customer_id):
        customer = CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        return jsonify(customer.to_dict())

# --- Helper functions remaining in this file ---
def get_database_info(database_file: Path):
    """Return simple info about the database"""
    try:
        conn = sqlite3.connect(str(database_file))
        cursor = conn.cursor()

        cursor.execute('SELECT count(*) FROM sqlite_master WHERE type="table"')
        table_count = cursor.fetchone()[0]

        cursor.execute('SELECT count(*) FROM sqlite_master WHERE type="index"')
        index_count = cursor.fetchone()[0]

        conn.close()

        return {'tables': table_count, 'indexes': index_count}

    except Exception as e:
        # Log the error, but don't prevent the app from running
        if current_app:
            current_app.logger.error(f"Error getting database info: {e}")
        return {'error': str(e)}


def check_system_health(config):
    """Placeholder for system health checks"""
    # Example: check free disk space, backup directory permissions, etc.
    if not config:
        return {'status': 'UNKNOWN', 'details': 'Configuration not available'}
    
    # You can add actual checks here using config.paths, etc.
    # For now, keeping it simple.
    return {'status': 'OK', 'details': 'All systems nominal'}
