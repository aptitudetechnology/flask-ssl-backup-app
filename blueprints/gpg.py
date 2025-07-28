from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from flask_login import login_required
import logging

gpg_bp = Blueprint('gpg', __name__, url_prefix='/gpg')

@gpg_bp.route('/')
@login_required
def index():
    """Main GPG key management page"""
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            flash('GPG system not available', 'error')
            return render_template('gpg/index.html', keys=[])
        
        # Get all local keys
        keys = gpg_backup.list_local_keys()
        current_app.logger.info(f"Found {len(keys)} GPG keys in keyring")
        
        return render_template('gpg/index.html', keys=keys)
        
    except Exception as e:
        current_app.logger.error(f"Error loading GPG keys: {str(e)}", exc_info=True)
        flash(f'Error loading GPG keys: {str(e)}', 'error')
        return render_template('gpg/index.html', keys=[])

@gpg_bp.route('/keys')
@login_required
def list_keys():
    """API endpoint to get all keys as JSON"""
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG system not available'}), 500
        
        keys = gpg_backup.list_local_keys()
        return jsonify({'success': True, 'keys': keys})
        
    except Exception as e:
        current_app.logger.error(f"Error listing GPG keys: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



@gpg_bp.route('/import', methods=['POST'])
@login_required
def import_key():
    """Import a GPG key from keyserver"""
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG system not available'}), 500
        
        data = request.get_json()
        key_id = data.get('key_id')
        email = data.get('email')
        
        if not key_id:
            return jsonify({'success': False, 'error': 'Key ID is required'}), 400
        
        current_app.logger.info(f"Importing GPG key: {key_id}")
        import_result = gpg_backup.import_key(key_id)
        
        if not import_result.get('success'):
            current_app.logger.error(f"GPG key import failed: {import_result}")
            return jsonify({
                'success': False,
                'error': import_result.get('error', 'Failed to import GPG key'),
                'details': import_result.get('details', '')
            }), 400
        
        # If email provided, validate the key
        if email:
            try:
                from utils.gpg_backup import validate_gpg_key_for_email
                validation_result = validate_gpg_key_for_email(email)
                
                if not validation_result['valid']:
                    current_app.logger.warning(f"Validation failed for imported key {key_id} and email {email}")
                    return jsonify({
                        'success': False,
                        'error': validation_result.get('error', 'Key validation failed'),
                        'details': f'The imported key for {email} cannot be used for encryption',
                        'validation_failed': True
                    }), 400
                
                key_info = validation_result.get('key_info', {})
                current_app.logger.info(f"Key imported and validated for {email}")
                
                return jsonify({
                    'success': True,
                    'message': 'Key imported and validated successfully',
                    'key_info': {
                        'key_id': key_info.get('key_id'),
                        'email': email,
                        'expires': key_info.get('expires'),
                        'created': key_info.get('created'),
                        'fingerprint': key_info.get('fingerprint')
                    }
                })
                
            except Exception as validation_error:
                current_app.logger.error(f"Key validation error: {validation_error}")
                return jsonify({
                    'success': False,
                    'error': f'Key validation failed: {str(validation_error)}',
                    'details': 'The key was imported but failed validation checks',
                    'validation_failed': True
                }), 400
        
        return jsonify({
            'success': True,
            'message': 'Key imported successfully',
            'key_info': {'key_id': key_id}
        })
        
    except Exception as e:
        current_app.logger.error(f"GPG key import failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to import GPG key',
            'details': str(e)
        }), 500

@gpg_bp.route('/key/<key_id>')
@login_required
def key_details(key_id):
    """Get detailed information about a specific key"""
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            flash('GPG system not available', 'error')
            return redirect(url_for('gpg.index'))
        
        # Try to find the key by ID in local keyring
        keys = gpg_backup.list_local_keys()
        key_info = None
        
        for key in keys:
            if key.get('keyid') == key_id or key.get('fingerprint') == key_id:
                key_info = key
                break
        
        if not key_info:
            flash(f'Key {key_id} not found in local keyring', 'error')
            return redirect(url_for('gpg.index'))
        
        # Get additional details if we have an email
        email = None
        if key_info.get('uids'):
            # Extract email from first UID
            uid = key_info['uids'][0] if isinstance(key_info['uids'], list) else key_info['uids']
            if '<' in uid and '>' in uid:
                email = uid.split('<')[1].split('>')[0]
        
        enhanced_info = None
        if email:
            try:
                enhanced_info = gpg_backup.get_key_info_for_template(email)
            except Exception as e:
                current_app.logger.warning(f"Could not get enhanced info for {email}: {e}")
        
        return render_template('gpg/key_details.html', 
                             key_info=key_info, 
                             enhanced_info=enhanced_info,
                             email=email)
        
    except Exception as e:
        current_app.logger.error(f"Error getting key details for {key_id}: {str(e)}", exc_info=True)
        flash(f'Error loading key details: {str(e)}', 'error')
        return redirect(url_for('gpg.index'))

@gpg_bp.route('/key/<key_id>/json')
@login_required
def key_details_json(key_id):
    """Get key details as JSON"""
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG system not available'}), 500
        
        keys = gpg_backup.list_local_keys()
        key_info = None
        
        for key in keys:
            if key.get('keyid') == key_id or key.get('fingerprint') == key_id:
                key_info = key
                break
        
        if not key_info:
            return jsonify({'success': False, 'error': 'Key not found'}), 404
        
        return jsonify({'success': True, 'key_info': key_info})
        
    except Exception as e:
        current_app.logger.error(f"Error getting key details JSON for {key_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@gpg_bp.route('/delete/<key_id>', methods=['POST'])
@login_required
def delete_key(key_id):
    """Delete a GPG key from the keyring"""
    # TODO: Implement key deletion functionality
    # This will require adding a delete_key method to your GPGBackup class
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG system not available'}), 500
        
        # Check if delete method exists
        if not hasattr(gpg_backup, 'delete_key'):
            return jsonify({
                'success': False, 
                'error': 'Key deletion not implemented yet'
            }), 501
        
        current_app.logger.info(f"Deleting GPG key: {key_id}")
        delete_result = gpg_backup.delete_key(key_id)
        
        if delete_result.get('success'):
            return jsonify({
                'success': True,
                'message': f'Key {key_id} deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': delete_result.get('error', 'Failed to delete key')
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error deleting key {key_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@gpg_bp.route('/upload', methods=['POST'])
@login_required
def upload_key():
    """Upload and import a GPG key from file"""
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG system not available'}), 500
        
        if 'key_file' not in request.files:
            return jsonify({'success': False, 'error': 'No key file provided'}), 400
        
        key_file = request.files['key_file']
        if key_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save file temporarily and import
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.asc') as tmp_file:
            key_file.save(tmp_file.name)
            
            current_app.logger.info(f"Importing GPG key from file: {key_file.filename}")
            import_result = gpg_backup.import_key_from_file(tmp_file.name)
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            if import_result.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Key imported successfully from file',
                    'filename': key_file.filename
                })
            else:
                return jsonify({
                    'success': False,
                    'error': import_result.get('error', 'Failed to import key from file')
                }), 400
                
    except Exception as e:
        current_app.logger.error(f"Error uploading key: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500