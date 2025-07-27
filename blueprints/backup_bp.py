from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app, send_file # <-- Import send_file
from functools import wraps
from utils.gpg_backup import GPGBackup
from utils.backup import DatabaseBackup # Import DatabaseBackup directly here for clarity

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

@backup_bp.before_app_request
def ensure_backup_dir_configured():
    import os
    DEFAULT_BACKUP_DIR = '/tmp/flask-backups'
    config = current_app.config

    if not config.get('BACKUP_DIR'):
        backup_dir = os.environ.get('BACKUP_DIR', DEFAULT_BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        config['BACKUP_DIR'] = backup_dir

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@backup_bp.route('/', strict_slashes=False)
@login_required
def backup_page_slash():
    # Redirect to the non-trailing-slash version
    return redirect(url_for('backup.backup_page'))

@backup_bp.route('')
@login_required
def backup_page():
    """Main backup page"""
    # For now, just render a basic backup template
    # You can add data fetching logic here later
    return render_template('backup/index.html',
                           last_backup_timestamp=None,
                           previous_backups=[])

@backup_bp.route('/create', methods=['POST'])
@login_required
def create_backup_route():
    """Create database backup - placeholder"""
    try:
        # 1. Create the regular backup file
        db_backup = DatabaseBackup(current_app.config)
        backup_path = db_backup.create_backup()  # Should return a Path object

        # 2. Check if encryption is requested (match form field names)
        encrypt = request.form.get('encrypt_gpg') == 'on'
        recipient_email = request.form.get('gpg_email')

        if encrypt and recipient_email:
            gpg_backup = GPGBackup(current_app.config)
            encrypted_path = gpg_backup.create_encrypted_backup(backup_path, recipient_email)
            if encrypted_path:
                # === MODIFIED: Use send_file for encrypted backup ===
                return send_file(
                    str(encrypted_path),
                    as_attachment=True,
                    download_name=encrypted_path.name,
                    mimetype='application/pgp-encrypted' # More specific for GPG encrypted files
                )
            else:
                # Try to get the last error from the GPGBackup logger or return a generic message
                import logging
                logger = logging.getLogger('gpg_backup_logger')
                last_error = None
                if logger.handlers:
                    for handler in logger.handlers:
                        if hasattr(handler, 'stream') and hasattr(handler.stream, 'getvalue'):
                            try:
                                last_error = handler.stream.getvalue()
                            except Exception:
                                pass
                return jsonify({'success': False, 'error': last_error or 'Encryption failed'}), 500
        else:
            # === MODIFIED: Use send_file for unencrypted backup ===
            return send_file(
                str(backup_path),
                as_attachment=True,
                download_name=backup_path.name,
                mimetype='application/gzip' if backup_path.suffix == '.gz' else 'application/octet-stream'
            )
    except Exception as e:
        # Log the exception for debugging purposes
        current_app.logger.exception("Error creating backup:")
        return jsonify({'success': False, 'error': str(e)}), 500

@backup_bp.route('/list', methods=['GET'])
@login_required
def list_backups():
    """List available backups - placeholder"""
    # ... (rest of your existing code for other routes) ...
    return jsonify({
        'success': True,
        'backups': []
    })

@backup_bp.route('/gpg/search', methods=['POST'])
@login_required
def gpg_search_keys():
    email = request.json.get('email') if request.is_json else request.form.get('email')
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    from utils.gpg_backup import GPGBackup
    gpg_backup = GPGBackup(current_app.config)
    keys = gpg_backup.search_keys(email)
    return jsonify({'success': True, 'keys': keys})

@backup_bp.route('/download/<backup_name>')
@login_required
def download_backup(backup_name):
    """Download backup file - placeholder"""
    return jsonify({
        'success': False,
        'error': 'Download not yet implemented'
    })

@backup_bp.route('/restore', methods=['POST'])
@login_required
def restore_backup():
    """Restore from backup - placeholder"""
    return jsonify({
        'success': False,
        'error': 'Restore not yet implemented'
    })

@backup_bp.route('/gpg/import', methods=['POST'])
@login_required
def gpg_import_key():
    """Import GPG key - placeholder"""
    return jsonify({
        'success': False,
        'error': 'GPG import not yet implemented'
    })