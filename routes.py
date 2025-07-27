from flask import (
    render_template, request, jsonify, session, redirect, url_for,
    flash, send_file
)
from functools import wraps
from pathlib import Path
import sqlite3
from datetime import datetime
from models import db, User, BackupRecord, CustomerService  # Import models
from backup import DatabaseBackup
from backup_gpg import GPGBackup
from config import get_config  # Import configuration   


def register_routes(app, config, db, backup_manager, gpg_backup):
    @app.route('/backup/', strict_slashes=False)
    @login_required
    def backup_page_slash():
        return redirect(url_for('backup_page'))

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route('/backup')
    @login_required
    def backup_page():
        return render_template('backup.html')

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

    @app.route('/backup/create', methods=['POST'])
    @login_required
    def create_backup_route():
        """Create database backup"""
        try:
            backup_type = request.form.get('backup_type', 'regular')
            description = request.form.get('description', '')
            user_id = session.get('user_id')

            backup_file = backup_manager.create_backup(
                backup_type=backup_type,
                description=description,
                user_id=user_id
            )

            backup_record = BackupRecord(
                filename=backup_file.name,
                backup_type=backup_type,
                description=description,
                user_id=user_id,
                file_size=backup_file.stat().st_size if backup_file.exists() else 0
            )
            db.session.add(backup_record)
            db.session.commit()

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
            db.session.rollback()
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
            backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
            if not backup_record:
                flash('Backup record not found', 'error')
                return redirect(url_for('dashboard'))

            backup_path = config.paths.backup_dir / backup_name

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

            backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
            if not backup_record:
                return jsonify({'success': False, 'error': 'Backup record not found'}), 404

            backup_path = config.paths.backup_dir / backup_name

            if not str(backup_path.resolve()).startswith(str(config.paths.backup_dir.resolve())):
                return jsonify({'success': False, 'error': 'Invalid backup file'}), 400

            if not backup_path.exists():
                return jsonify({'success': False, 'error': 'Backup file not found'}), 404

            current_backup = backup_manager.create_backup(
                backup_type='pre_restore',
                description=f'Pre-restore backup before restoring {backup_name}',
                user_id=session.get('user_id')
            )

            success = backup_manager.restore_backup(backup_path)

            if success:
                with app.app_context():
                    db.create_all()

                flash(f'Database restored from {backup_name}', 'success')
                return jsonify({
                    'success': True,
                    'message': f'Restored from backup {backup_name}'
                })
            else:
                flash('Restore failed', 'error')
                return jsonify({'success': False, 'error': 'Restore failed'}), 500

        except Exception as e:
            app.logger.error(f"Restore failed: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500


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
        return {'error': str(e)}


def check_system_health(config):
    """Placeholder for system health checks"""
    # Example: check free disk space, backup directory permissions, etc.
    return {'status': 'OK', 'details': 'All systems nominal'}
