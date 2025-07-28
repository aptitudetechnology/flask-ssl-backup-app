from flask import (
    Blueprint, render_template, request, jsonify, session, redirect, url_for,
    flash, send_file, current_app # Import current_app
)
from flask_login import login_required
from pathlib import Path
import sqlite3
from datetime import datetime
backup_bp = Blueprint('backup', __name__)


# Import models directly assuming they are initialized with your app
# In a larger app, you might pass db to blueprints or get it via current_app
from models import db, User, BackupRecord, CustomerService 

# We will get config, backup_manager, gpg_backup from current_app.extensions
# which you'll set up in your main app.py/init.py

# Define the blueprint
backup_bp = Blueprint('backup', __name__, url_prefix='/backup')



# --- Routes for Backup Blueprint ---

@backup_bp.route('/', strict_slashes=False)
@login_required
def backup_page_slash():
    # Redirect to the non-trailing-slash version
    return redirect(url_for('backup.backup_page'))

@backup_bp.route('')
@login_required
def backup_page():
    # Fetch last backup and previous backups here if needed for direct rendering
    # The current backup/index.html might still rely on this.
    # For now, just render the template.
    # Note: Your original 'backup_page' in routes.py didn't fetch data, 
    # but your HTML shows {% if last_backup_timestamp %}, etc.
    # If this page needs data, it should be fetched here.
    
    # Placeholder for data if needed on the /backup page itself
    last_backup_timestamp = None 
    previous_backups = []
    
    try:
        # Assuming these managers are set on current_app.extensions
        backup_manager = current_app.extensions.get('backup_manager')
        if backup_manager:
            recent_records = BackupRecord.query.order_by(BackupRecord.created_at.desc()).first()
            if recent_records:
                last_backup_timestamp = recent_records.created_at
            
            # For "Previous Backups" table in backup-restore.html
            previous_backups = []
            records = BackupRecord.query.order_by(BackupRecord.created_at.desc()).limit(10).all() # Limit to 10 for example
            for record in records:
                backup_path = backup_manager.app_paths.backup_dir / record.filename
                previous_backups.append({
                    'filename': record.filename,
                    'size': f"{record.file_size / (1024*1024):.2f} MB" if record.file_size else 'N/A', # Convert bytes to MB
                    'date': record.created_at,
                    'download_url': url_for('backup.download_backup', backup_name=record.filename) # Use blueprint name
                })

    except Exception as e:
        current_app.logger.error(f"Error loading backup page data: {e}")
        flash('Error loading backup information.', 'error')

    return render_template('backup/index.html', 
                           last_backup_timestamp=last_backup_timestamp,
                           previous_backups=previous_backups)


@backup_bp.route('/create', methods=['POST'])
@login_required
def create_backup_route():
    """Create database backup, optionally GPG-encrypted"""
    try:
        backup_manager = current_app.extensions.get('backup_manager')
        gpg_backup = current_app.extensions.get('utility_gpg_backup')

        if not backup_manager:
            return jsonify({'success': False, 'error': 'Backup manager not initialized'}), 500

        # --- Read form inputs ---
        backup_format = request.form.get('format', 'zip')
        include_attachments = 'include_attachments' in request.form
        encrypt_gpg = 'encrypt_gpg' in request.form
        gpg_email = request.form.get('gpg_email')

        # --- Validate GPG encryption requirements BEFORE creating backup ---
        if encrypt_gpg:
            if not gpg_backup:
                return jsonify({
                    'success': False, 
                    'error': 'GPG encryption not available. Please contact administrator.'
                }), 500
            
            if not gpg_email:
                return jsonify({
                    'success': False, 
                    'error': 'Email address is required for GPG encryption.'
                }), 400
            
            # Check if GPG backup class has the validation method
            if not hasattr(gpg_backup, 'has_public_key'):
                current_app.logger.error("GPGBackup class missing has_public_key method")
                return jsonify({
                    'success': False, 
                    'error': 'GPG key validation not available. Please contact administrator.'
                }), 500
            
            # Validate that public key exists for the email
            try:
                key_exists = gpg_backup.has_public_key(gpg_email)
                if not key_exists:
                    return jsonify({
                        'success': False, 
                        'error': f'No public key found for {gpg_email}. Please search for and import the key first.'
                    }), 400
                
                current_app.logger.info(f"GPG key validation passed for {gpg_email}")
                
            except Exception as key_check_error:
                current_app.logger.error(f"GPG key validation failed: {str(key_check_error)}", exc_info=True)
                return jsonify({
                    'success': False, 
                    'error': 'Unable to validate GPG key. Please try again or contact administrator.'
                }), 500

        compress = backup_format in ('zip', 'gz')

        # --- Step 1: Create raw backup ---
        current_app.logger.info(f"Creating backup with format: {backup_format}, compression: {compress}")
        backup_file_path = backup_manager.create_backup(
            format='gz' if compress else 'db',
            include_attachments=include_attachments
        )

        if not backup_file_path or not backup_file_path.exists():
            current_app.logger.error(f"Backup creation failed: {backup_file_path}")
            db.session.rollback()
            return jsonify({'success': False, 'error': 'Backup creation failed.'}), 500

        current_app.logger.info(f"Raw backup created: {backup_file_path}")

        # --- Step 2: Record initial backup entry ---
        backup_record = BackupRecord(
            filename=backup_file_path.name,
            backup_type='encrypted' if encrypt_gpg else 'regular',
            description='Customer database backup' + (' (GPG encrypted)' if encrypt_gpg else ''),
            user_id=session.get('user_id'),
            file_size=backup_file_path.stat().st_size
        )
        db.session.add(backup_record)
        db.session.commit()

        # --- Step 3: If GPG encryption is requested ---
        final_download_path = backup_file_path  # Default: unencrypted file
        if encrypt_gpg and gpg_backup and gpg_email:
            try:
                current_app.logger.info(f"Starting GPG encryption for {gpg_email}")
                
                encrypted_file_path = gpg_backup.create_encrypted_backup(
                    input_filepath=backup_file_path,
                    recipient_email=gpg_email
                )
                
                # Debug logging to understand what create_encrypted_backup returns
                current_app.logger.info(f"Encryption result: {encrypted_file_path}")
                current_app.logger.info(f"File exists: {encrypted_file_path.exists() if encrypted_file_path else 'N/A'}")
                
                if not encrypted_file_path or not encrypted_file_path.exists():
                    raise Exception("GPG encryption failed: No encrypted file returned.")

                # Delete original unencrypted file
                current_app.logger.info(f"Deleting original unencrypted file: {backup_file_path}")
                backup_file_path.unlink()

                # Update database record with encrypted file info
                final_download_path = encrypted_file_path
                backup_record.filename = encrypted_file_path.name
                backup_record.file_size = encrypted_file_path.stat().st_size
                db.session.commit()
                
                current_app.logger.info(f"GPG encryption completed successfully: {encrypted_file_path}")

            except Exception as e:
                current_app.logger.error(f"GPG encryption error: {str(e)}", exc_info=True)
                
                # Cleanup: remove the unencrypted backup file and database record
                try:
                    if backup_file_path.exists():
                        backup_file_path.unlink()
                        current_app.logger.info(f"Cleaned up failed backup file: {backup_file_path}")
                except Exception as cleanup_error:
                    current_app.logger.error(f"Failed to cleanup backup file: {cleanup_error}")
                
                # Rollback database changes
                db.session.rollback()
                
                # Return detailed error to help with debugging
                error_message = 'Encryption failed. Backup was not saved.'
                if 'no public key' in str(e).lower():
                    error_message = f'No public key found for {gpg_email}. Please import the key first.'
                elif 'gpg' in str(e).lower():
                    error_message = f'GPG encryption error: {str(e)}'
                
                return jsonify({
                    'success': False,
                    'error': error_message
                }), 500

        # --- Step 4: Return download URL for the final file ---
        current_app.logger.info(f"Backup creation completed successfully: {final_download_path}")
        return jsonify({
            'success': True,
            'job_id': 'direct_download',
            'completed': True,
            'download_url': url_for('backup.download_backup', backup_name=final_download_path.name),
            'filename': final_download_path.name,
            'encrypted': encrypt_gpg
        })

    except Exception as e:
        current_app.logger.error(f"Backup failed: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Backup creation failed: {str(e)}'}), 500


@backup_bp.route('/validate-key', methods=['POST'])
@login_required
def validate_gpg_key():
    """
    Validate that a GPG public key exists for the given email.
    Used by frontend to enable/disable backup button.
    """
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG not available'}), 500

        data = request.get_json()
        email = data.get('email') if data else request.form.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email address required'}), 400

        if not hasattr(gpg_backup, 'has_public_key'):
            return jsonify({'success': False, 'error': 'Key validation not available'}), 500

        key_exists = gpg_backup.has_public_key(email)
        
        key_info = None
        if key_exists and hasattr(gpg_backup, 'get_key_info'):
            try:
                key_info = gpg_backup.get_key_info(email)
            except Exception as e:
                current_app.logger.warning(f"Could not get key info for {email}: {e}")

        return jsonify({
            'success': True,
            'key_exists': key_exists,
            'email': email,
            'key_info': key_info
        })

    except Exception as e:
        current_app.logger.error(f"Key validation failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@backup_bp.route('/list')
@login_required
def list_backups():
    """List available backups with database records"""
    try:
        backup_records = BackupRecord.query.order_by(BackupRecord.created_at.desc()).all()
        backup_data = []

        backup_manager = current_app.extensions.get('backup_manager')
        if not backup_manager:
            return jsonify({'success': False, 'error': 'Backup manager not initialized'}), 500

        for record in backup_records:
            backup_path = backup_manager.app_paths.backup_dir / record.filename
            backup_info = {
                'id': record.id,
                'filename': record.filename,
                'path': str(backup_path),
                'size': backup_path.stat().st_size if backup_path.exists() else record.file_size,
                'created': record.created_at.isoformat(),
                'type': record.backup_type,
                'description': record.description,
                'exists': backup_path.exists(),
                'download_url': url_for('backup.download_backup', backup_name=record.filename) # Use blueprint name
            }
            backup_data.append(backup_info)

        return jsonify({
            'success': True,
            'backups': backup_data
        })

    except Exception as e:
        current_app.logger.error(f"Failed to list backups: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@backup_bp.route('/download/<backup_name>')
@login_required
def download_backup(backup_name):
    """Download backup file"""
    try:
        backup_manager = current_app.extensions.get('backup_manager')
        if not backup_manager:
            flash('Backup manager not initialized', 'error')
            return redirect(url_for('dashboard')) # Redirect to dashboard or main backup page

        backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
        if not backup_record:
            flash('Backup record not found', 'error')
            return redirect(url_for('dashboard'))

        backup_path = backup_manager.app_paths.backup_dir / backup_name

        # Security check: Ensure the path is within the designated backup directory
        if not str(backup_path.resolve()).startswith(str(backup_manager.app_paths.backup_dir.resolve())):
            flash('Invalid backup file path detected.', 'error')
            return redirect(url_for('dashboard'))

        if not backup_path.exists():
            flash('Backup file not found on server storage.', 'error')
            return redirect(url_for('dashboard'))

        return send_file(
            str(backup_path),
            as_attachment=True,
            download_name=backup_name,
            mimetype='application/gzip' if backup_path.suffix == '.gz' else 'application/octet-stream'
        )

    except Exception as e:
        current_app.logger.error(f"Backup download failed: {str(e)}", exc_info=True)
        flash('Download failed due to an internal error.', 'error')
        return redirect(url_for('dashboard'))


@backup_bp.route('/restore', methods=['POST'])
@login_required
def restore_backup():
    """Restore database from backup"""
    try:
        backup_manager = current_app.extensions.get('backup_manager')
        if not backup_manager:
            return jsonify({'success': False, 'error': 'Backup manager not initialized'}), 500

        backup_name = request.form.get('backup_name')
        if not backup_name:
            # Handle file upload for restore from backup-restore.html
            uploaded_file = request.files.get('backup_file_upload') # Assuming 'backup_file_upload' is the name
            if uploaded_file and uploaded_file.filename != '':
                # Save the uploaded file temporarily
                temp_restore_path = backup_manager.app_paths.backup_dir / uploaded_file.filename
                uploaded_file.save(temp_restore_path)
                backup_path = temp_restore_path
                current_app.logger.info(f"Uploaded file for restore: {temp_restore_path}")
            else:
                return jsonify({'success': False, 'error': 'No backup file or name specified'}), 400
        else:
            # Handle restore by name from a list of previous backups
            backup_record = BackupRecord.query.filter_by(filename=backup_name).first()
            if not backup_record:
                return jsonify({'success': False, 'error': 'Backup record not found'}), 404
            backup_path = backup_manager.app_paths.backup_dir / backup_name

        if not str(backup_path.resolve()).startswith(str(backup_manager.app_paths.backup_dir.resolve())):
            return jsonify({'success': False, 'error': 'Invalid backup file path detected.'}), 400

        if not backup_path.exists():
            return jsonify({'success': False, 'error': 'Backup file not found on server storage.'}), 404

        # Create a pre-restore backup (important safety measure)
        # Fixed: Use correct method signature for create_backup
        current_backup = backup_manager.create_backup(
            format='gz',
            backup_type='pre_restore'
        )
        if not current_backup:
            return jsonify({'success': False, 'error': 'Failed to create pre-restore backup'}), 500

        success = backup_manager.restore_backup(backup_path)

        # After restore, ensure database tables are created if the backup was empty or corrupting
        if success:
            with current_app.app_context():
                db.create_all() # Re-create tables based on models if they got dropped during restore

            flash(f'Database restored from {backup_path.name}', 'success')
            return jsonify({
                'success': True,
                'message': f'Restored from backup {backup_path.name}'
            })
        else:
            flash('Restore failed.', 'error')
            return jsonify({'success': False, 'error': 'Restore failed.'}), 500

    except Exception as e:
        current_app.logger.error(f"Restore failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# --- GPG Routes ---

@backup_bp.route('/gpg/search', methods=['POST'])
@login_required
def gpg_search_keys():
    """
    Searches for GPG public keys on a keyserver.
    Expects JSON body: {"email": "user@example.com"}
    Returns JSON: {"success": true, "keys": [...]} or {"success": false, "error": "..."}
    """
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG Backup manager not initialized'}), 500

        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'success': False, 'error': 'Email address is required for GPG key search.'}), 400

        if not hasattr(gpg_backup, 'search_keys'):
            return jsonify({'success': False, 'error': 'GPG key search not available'}), 500

        current_app.logger.info(f"Searching for GPG keys for email: {email}")
        keys = gpg_backup.search_keys(email)
        
        # 'keys' should be a list of dictionaries with 'key_id', 'uids', 'created'
        return jsonify({'success': True, 'keys': keys})

    except Exception as e:
        current_app.logger.error(f"GPG key search failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to search GPG keys: {str(e)}'}), 500


@backup_bp.route('/gpg/import', methods=['POST'])
@login_required
def gpg_import_key():
    """
    Imports a GPG public key from a keyserver.
    Expects JSON body: {"key_id": "0xABCDEF1234567890"}
    Returns JSON: {"success": true, "message": "Key imported."} or {"success": false, "error": "..."}
    """
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG Backup manager not initialized'}), 500

        data = request.get_json()
        key_id = data.get('key_id')

        if not key_id:
            return jsonify({'success': False, 'error': 'Key ID is required for GPG key import.'}), 400

        if not hasattr(gpg_backup, 'import_key'):
            return jsonify({'success': False, 'error': 'GPG key import not available'}), 500

        current_app.logger.info(f"Importing GPG key: {key_id}")
        import_result = gpg_backup.import_key(key_id)

        if import_result.get('success'):
            current_app.logger.info(f"GPG key imported successfully: {key_id}")
            return jsonify({'success': True, 'message': import_result.get('message', 'GPG key imported successfully.')})
        else:
            current_app.logger.error(f"GPG key import failed: {import_result}")
            return jsonify({
                'success': False, 
                'error': import_result.get('error', 'Failed to import GPG key.'), 
                'details': import_result.get('details', '')
            }), 500

    except Exception as e:
        current_app.logger.error(f"GPG key import failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to import GPG key: {str(e)}'}), 500


# --- Dashboard helper functions (can be moved to a dashboard blueprint or common utils) ---
# These were in your original routes.py but not directly part of the backup blueprint,
# so they remain here for completeness, but ideally would be in their own module/blueprint.

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