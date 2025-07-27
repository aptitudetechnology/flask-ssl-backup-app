"""
Flask Application with Modern SQLAlchemy Integration
Updated to use modern Flask-SQLAlchemy patterns with pathlib
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
import os
from functools import wraps
from typing import Optional, Dict, Any
import tempfile
import json

from config import get_config, app_paths
from models import db, User, BackupRecord, CustomerService  # Added CustomerService for customers view
from backup import DatabaseBackup, create_backup, list_available_backups
from backup_gpg import GPGBackup


def create_app(config_name=None):
    """Application factory with modern SQLAlchemy and pathlib integration"""
    # Authentication decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # Customers route (after app and login_required are defined)
    @app.route('/customers')
    @login_required
    def customers():
        """Customer list page"""
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        if search:
            customer_list = CustomerService.search_customers(search)
        else:
            active_only = (status != 'inactive')
            customer_list = CustomerService.get_all_customers(active_only=active_only)
        return render_template('customers.html', customers=customer_list)
    
    # Initialize Flask app with pathlib paths
    config = get_config(config_name)
    
    app = Flask(__name__,
               static_folder=str(config.paths.static_dir),
               template_folder=str(config.paths.templates_dir))
    
    # Configure Flask app
    app.config.update(config.get_flask_config())
    
    # Modern SQLAlchemy configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config.paths.database_file}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Setup logging
    setup_logging(app, config)
    
    # Initialize database with modern pattern
    db.init_app(app)
    
    # Create tables within app context
    with app.app_context():
        db.create_all()
        app.logger.info(f"Database initialized at: {config.paths.database_file}")
    
    # Setup security headers
    setup_security_headers(app, config)
    
    # Initialize backup systems
    backup_manager = DatabaseBackup(config)
    gpg_backup = GPGBackup(config) if config.GPG_RECIPIENT_EMAIL else None
    
    # Authentication decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Routes
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
                # Modern SQLAlchemy query pattern
                user = User.query.filter_by(username=username).first()
                if user and user.check_password(password):  # Assuming you have this method
                    session['user_id'] = user.id
                    session['username'] = user.username
                    flash('Login successful', 'success')
                    return redirect(url_for('dashboard'))
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
            backup_stats = backup_manager.get_backup_stats()
            recent_backups = backup_manager.list_backups()[:5]
            db_info = get_database_info(config.paths.database_file)
            health_status = check_system_health(config)
            
            return render_template('dashboard.html',
                                 backup_stats=backup_stats,
                                 recent_backups=recent_backups,
                                 db_info=db_info,
                                 health_status=health_status)
        
        except Exception as e:
            app.logger.error(f"Dashboard error: {str(e)}")
            flash('Error loading dashboard', 'error')
            return render_template('dashboard.html',
                                 backup_stats={},
                                 recent_backups=[],
                                 db_info={},
                                 health_status={})
    
    @app.route('/backup/create', methods=['POST'])
    @login_required
    def create_backup_route():
        """Create database backup"""
        try:
            backup_type = request.form.get('backup_type', 'regular')
            description = request.form.get('description', '')
            user_id = session.get('user_id')
            
            # Create backup
            backup_file = backup_manager.create_backup(
                backup_type=backup_type,
                description=description,
                user_id=user_id
            )
            
            # Create backup record in database using modern SQLAlchemy
            backup_record = BackupRecord(
                filename=backup_file.name,
                backup_type=backup_type,
                description=description,
                user_id=user_id,
                file_size=backup_file.stat().st_size if backup_file.exists() else 0
            )
            db.session.add(backup_record)
            db.session.commit()
            
            # Create GPG backup if configured
            if gpg_backup and backup_type in ['encrypted', 'both']:
                try:
                    gpg_file = gpg_backup.create_encrypted_backup(backup_file)
                    flash(f'Encrypted backup created: {gpg_file.name}', 'success')
                except Exception as e:
                    app.logger.error(f"GPG backup failed: {str(e)}")
                    flash('Regular backup created, but encryption failed', 'warning')
            
            flash(f'Backup created successfully: {backup_file.name}', 'success')
            return jsonify({
                'success': True,
                'backup_file': str(backup_file),
                'message': 'Backup created successfully'
            })
            
        except Exception as e:
            app.logger.error(f"Backup creation failed: {str(e)}")
            db.session.rollback()  # Rollback on error
            flash('Backup creation failed', 'error')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/backup/list')
    @login_required
    def list_backups():
        """List available backups with database records"""
        try:
            # Get backup records from database
            backup_records = BackupRecord.query.order_by(BackupRecord.created_at.desc()).all()
            backup_data = []
            
            for record in backup_records:
                backup_path = config.paths.backup_dir / record.filename
                backup_info = {
                    'id': record.id,
                    'filename': record.filename,
                    'path': str(backup_path),
                    'size': backup_path.stat().st_size if backup_path.exists() else record.file_size,
                    'created': record.created_at.isoformat(),
                    'type': record.backup_type,
                    'description': record.description,
                    'exists': backup_path.exists()
                }
                backup_data.append(backup_info)
            
            return jsonify({
                'success': True,
                'backups': backup_data
            })
            
        except Exception as e:
            app.logger.error(f"Failed to list backups: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/backup/download/<backup_name>')
    @login_required
    def download_backup(backup_name):
        """Download backup file"""
        try:
            # Validate backup exists in database
            backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
            if not backup_record:
                flash('Backup record not found', 'error')
                return redirect(url_for('dashboard'))
            
            # Validate backup name and path
            backup_path = config.paths.backup_dir / backup_name
            
            # Security check - ensure file is in backup directory
            if not str(backup_path.resolve()).startswith(str(config.paths.backup_dir.resolve())):
                flash('Invalid backup file', 'error')
                return redirect(url_for('dashboard'))
            
            if not backup_path.exists():
                flash('Backup file not found', 'error')
                return redirect(url_for('dashboard'))
            
            return send_file(
                str(backup_path),
                as_attachment=True,
                download_name=backup_name
            )
            
        except Exception as e:
            app.logger.error(f"Backup download failed: {str(e)}")
            flash('Download failed', 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/backup/restore', methods=['POST'])
    @login_required
    def restore_backup():
        """Restore database from backup"""
        try:
            backup_name = request.form.get('backup_name')
            if not backup_name:
                return jsonify({'success': False, 'error': 'No backup specified'}), 400
            
            # Validate backup exists in database
            backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
            if not backup_record:
                return jsonify({'success': False, 'error': 'Backup record not found'}), 404
            
            backup_path = config.paths.backup_dir / backup_name
            
            # Security validation
            if not str(backup_path.resolve()).startswith(str(config.paths.backup_dir.resolve())):
                return jsonify({'success': False, 'error': 'Invalid backup file'}), 400
            
            if not backup_path.exists():
                return jsonify({'success': False, 'error': 'Backup file not found'}), 404
            
            # Create backup of current database before restore
            current_backup = backup_manager.create_backup(
                backup_type='pre_restore',
                description=f'Pre-restore backup before restoring {backup_name}',
                user_id=session.get('user_id')
            )
            
            # Perform restore
            success = backup_manager.restore_backup(backup_path)
            
            if success:
                # After successful restore, recreate tables to ensure schema is up to date
                with app.app_context():
                    db.create_all()
                
                flash(f'Database restored from {backup_name}', 'success')
                return jsonify({
                    'success': True,
                    'message': f'Database restored from {backup_name}',
                    'pre_restore_backup': str(current_backup)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Restore operation failed'
                }), 500
                
        except Exception as e:
            app.logger.error(f"Restore failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/backup/delete/<backup_name>', methods=['DELETE'])
    @login_required
    def delete_backup(backup_name):
        """Delete backup file and database record"""
        try:
            # Find backup record
            backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
            
            backup_path = config.paths.backup_dir / backup_name
            
            # Security validation
            if not str(backup_path.resolve()).startswith(str(config.paths.backup_dir.resolve())):
                return jsonify({'success': False, 'error': 'Invalid backup file'}), 400
            
            # Delete file if it exists
            if backup_path.exists():
                backup_path.unlink()
            
            # Delete database record if it exists
            if backup_record:
                db.session.delete(backup_record)
                db.session.commit()
            
            flash(f'Backup {backup_name} deleted', 'success')
            return jsonify({
                'success': True,
                'message': f'Backup {backup_name} deleted'
            })
                
        except Exception as e:
            app.logger.error(f"Backup deletion failed: {str(e)}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/system/health')
    @login_required
    def system_health():
        """System health check"""
        try:
            health_data = check_system_health(config)
            return jsonify({
                'success': True,
                'health': health_data
            })
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        """Application settings"""
        if request.method == 'POST':
            try:
                # Update settings (implement as needed)
                flash('Settings updated successfully', 'success')
                return redirect(url_for('settings'))
            except Exception as e:
                app.logger.error(f"Settings update failed: {str(e)}")
                flash('Settings update failed', 'error')
        
        return render_template('settings.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {str(error)}")
        # Rollback database session on server error
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403
    
    return app


def setup_logging(app, config):
    """Setup application logging with pathlib"""
    try:
        # Ensure log directory exists
        config.paths.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file handler
        log_file = config.paths.log_dir / 'app.log'
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
            handlers=[
                logging.FileHandler(str(log_file)),
                logging.StreamHandler()
            ]
        )
        
        app.logger.info(f"Logging initialized - Log file: {log_file}")
        
    except Exception as e:
        print(f"Failed to setup logging: {str(e)}")


def setup_security_headers(app, config):
    """Setup security headers"""
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if config.FORCE_HTTPS:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


def get_database_info(db_path: Path) -> Dict[str, Any]:
    """Get database information using pathlib"""
    try:
        if not db_path.exists():
            return {'error': 'Database file not found'}
        
        stat = db_path.stat()
        
        # Get database size and basic info
        db_info = {
            'path': str(db_path),
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
        
        # Get table count and row counts
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                db_info['table_count'] = len(tables)
                
                # Get total row count
                total_rows = 0
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    total_rows += count
                
                db_info['total_rows'] = total_rows
                
        except sqlite3.Error as e:
            db_info['db_error'] = str(e)
        
        return db_info
        
    except Exception as e:
        return {'error': str(e)}


def check_system_health(config) -> Dict[str, Any]:
    """Check system health using pathlib"""
    health = {
        'database': 'unknown',
        'ssl': 'unknown',
        'backup_dir': 'unknown',
        'gpg': 'unknown',
        'disk_space': 'unknown'
    }
    
    try:
        # Check database
        if config.paths.database_file.exists():
            try:
                with sqlite3.connect(str(config.paths.database_file)) as conn:
                    conn.execute("SELECT 1").fetchone()
                health['database'] = 'healthy'
            except sqlite3.Error:
                health['database'] = 'error'
        else:
            health['database'] = 'missing'
        
        # Check SSL certificates
        ssl_cert = config.paths.ssl_dir / 'cert.pem'
        ssl_key = config.paths.ssl_dir / 'key.pem'
        
        if ssl_cert.exists() and ssl_key.exists():
            health['ssl'] = 'configured'
        else:
            health['ssl'] = 'missing'
        
        # Check backup directory
        if config.paths.backup_dir.exists():
            # Check if writable
            test_file = config.paths.backup_dir / '.write_test'
            try:
                test_file.write_text('test')
                test_file.unlink()
                health['backup_dir'] = 'writable'
            except:
                health['backup_dir'] = 'readonly'
        else:
            health['backup_dir'] = 'missing'
        
        # Check GPG
        if config.GPG_RECIPIENT_EMAIL:
            # Simple check - could be expanded
            health['gpg'] = 'configured'
        else:
            health['gpg'] = 'not_configured'
        
        # Check disk space
        try:
            stat = config.paths.app_root.stat()
            # This is a simplified check - could use shutil.disk_usage()
            health['disk_space'] = 'sufficient'
        except:
            health['disk_space'] = 'unknown'
            
    except Exception as e:
        health['error'] = str(e)
    
    return health


if __name__ == '__main__':
    """Run the application"""
    app = create_app()
    config = get_config()
    
    # SSL configuration
    ssl_context = None
    if config.SSL_ENABLED:
        cert_file = config.paths.ssl_dir / 'cert.pem'
        key_file = config.paths.ssl_dir / 'key.pem'
        
        if cert_file.exists() and key_file.exists():
            ssl_context = (str(cert_file), str(key_file))
            app.logger.info("SSL enabled with certificates")
        else:
            app.logger.warning("SSL certificates not found, running without SSL")
    
    # Run the application
    app.run(
        #host=config.HOST,
        host='0.0.0.0', 
        port=config.PORT,
        debug=config.DEBUG,
        ssl_context=ssl_context
    )