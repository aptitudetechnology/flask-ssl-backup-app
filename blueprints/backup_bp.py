from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from functools import wraps
from utils.gpg_backup import GPGBackup

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

@backup_bp.before_app_first_request
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
        # 1. Create the regular backup file (must use real DatabaseBackup)
        from utils.backup import DatabaseBackup
        db_backup = DatabaseBackup(current_app.config)
        backup_path = db_backup.create_backup()  # Should return a Path object

        # 2. Check if encryption is requested
        encrypt = request.form.get('encrypt') == 'true'
        recipient_email = request.form.get('recipient_email')

        if encrypt and recipient_email:
            gpg_backup = GPGBackup(current_app.config)
            encrypted_path = gpg_backup.create_encrypted_backup(backup_path, recipient_email)
            if encrypted_path:
                return jsonify({'success': True, 'backup': str(encrypted_path.name)})
            else:
                return jsonify({'success': False, 'error': 'Encryption failed'}), 500
        else:
            return jsonify({'success': True, 'backup': str(backup_path.name)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@backup_bp.route('/list', methods=['GET'])
@login_required
def list_backups():
    """List available backups - placeholder"""
    return jsonify({
        'success': True,
        'backups': []
    })

@backup_bp.route('/gpg/search', methods=['POST'])
@login_required
def gpg_search_keys():
    """Search for GPG keys - placeholder"""
    return jsonify({
        'success': False,
        'error': 'GPG search not yet implemented'
    })

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