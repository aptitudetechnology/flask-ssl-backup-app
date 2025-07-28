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

        compress = backup_format in ('zip', 'gz')

        # --- Step 1: Create raw backup ---
        backup_file_path = backup_manager.create_backup(
            format='gz' if compress else 'db',
            include_attachments=False
        )

        if not backup_file_path or not backup_file_path.exists():
            db.session.rollback()
            return jsonify({'success': False, 'error': 'Backup creation failed.'}), 500

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
                encrypted_file_path = gpg_backup.create_encrypted_backup(
                    input_filepath=backup_file_path,
                    recipient_email=gpg_email
                )
                if encrypted_file_path and encrypted_file_path.exists():
                    # Delete original unencrypted file
                    backup_file_path.unlink()

                    # Update database record
                    final_download_path = encrypted_file_path
                    backup_record.filename = encrypted_file_path.name
                    backup_record.file_size = encrypted_file_path.stat().st_size
                    db.session.commit()
                else:
                    raise Exception("GPG encryption failed: No encrypted file returned.")

            except Exception as e:
                current_app.logger.error(f"GPG encryption error: {str(e)}")
                # Cleanup and report error to user
                if backup_file_path.exists():
                    backup_file_path.unlink()
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'error': 'Encryption failed. Backup was not saved.'
                }), 500

        # --- Step 4: Return download URL for the final file ---
        return jsonify({
            'success': True,
            'job_id': 'direct_download',
            'completed': True,
            'download_url': url_for('backup.download_backup', backup_name=final_download_path.name)
        })

    except Exception as e:
        current_app.logger.error(f"Backup failed: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
