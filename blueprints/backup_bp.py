from flask import Blueprint, render_template, request, send_file, jsonify, current_app, flash, session
from flask import redirect, url_for
from pathlib import Path

backup_bp = Blueprint('backup_bp', __name__, url_prefix='/backup')

# Example: Main backup page
@backup_bp.route('/', methods=['GET'])
def backup_index():
    return render_template('backup/index.html')

# Example: Create backup (POST)
@backup_bp.route('/create', methods=['POST'])
def create_backup():
    backup_manager = current_app.extensions.get('backup_manager')
    if not backup_manager:
        return jsonify({'success': False, 'error': 'Backup manager not available'}), 500
    backup_file = backup_manager.create_backup()
    if not backup_file:
        return jsonify({'success': False, 'error': 'Backup creation failed'}), 500
    return send_file(str(backup_file), as_attachment=True, download_name=backup_file.name)

@backup_bp.route('/list', methods=['GET'])
def list_backups():
    backup_manager = current_app.extensions.get('backup_manager')
    if not backup_manager:
        return jsonify({'success': False, 'error': 'Backup manager not available'}), 500
    backups = backup_manager.list_backups()
    # You can render a template or return JSON; here we render a template
    return render_template('backup/list.html', backups=backups)

# Add other routes (download, restore, gpg/search, gpg/import) as needed
