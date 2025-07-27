with app.app_context():
    db.create_all()
    if User.query.filter_by(username='admin').first():
        print("Admin user already exists.")
    else:
        admin = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_active=True,
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created: username='admin', password='admin123'")
