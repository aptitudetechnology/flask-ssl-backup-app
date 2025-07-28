@backup_bp.route('/gpg/import', methods=['POST'])
@login_required
def gpg_import_key():
    """
    Imports a GPG public key from a keyserver and immediately validates it.
    Expects JSON body: {"key_id": "...", "email": "..."}
    """
    try:
        gpg_backup = current_app.extensions.get('utility_gpg_backup')
        if not gpg_backup:
            return jsonify({'success': False, 'error': 'GPG Backup manager not initialized'}), 500

        data = request.get_json()
        key_id = data.get('key_id')
        email = data.get('email') or session.get('gpg_email')

        if not key_id:
            return jsonify({'success': False, 'error': 'Key ID is required for GPG key import.'}), 400

        if not hasattr(gpg_backup, 'import_key'):
            return jsonify({'success': False, 'error': 'GPG key import not available'}), 500

        current_app.logger.info(f"Importing GPG key: {key_id}")
        import_result = gpg_backup.import_key(key_id)

        if not import_result.get('success'):
            current_app.logger.error(f"GPG key import failed: {import_result}")
            return jsonify({
                'success': False,
                'error': import_result.get('error', 'Failed to import GPG key.'),
                'details': import_result.get('details', '')
            }), 400

        # Optional: store validated email in session
        if email:
            session['gpg_email'] = email

            try:
                from utils.gpg_backup import validate_gpg_key_for_email
                validation_result = validate_gpg_key_for_email(email)

                if not validation_result['valid']:
                    current_app.logger.warning(f"Validation failed for imported key {key_id} and email {email}")
                    return jsonify({
                        'success': False,
                        'error': validation_result.get('error', 'Key validation failed'),
                        'details': f'The imported key for {email} cannot be used for encryption.',
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
                    'details': 'The key was imported but failed validation checks.',
                    'validation_failed': True
                }), 400

        else:
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
