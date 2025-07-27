#!/usr/bin/env python3
"""
Flask Backup Application Quick Start Script
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Quick start for Flask Backup Application"""
    
    print("🔒 Flask Backup Application")
    print("=" * 50)
    
    # Check if we're in the right directory
    app_file = Path('app.py')
    if not app_file.exists():
        print("❌ Error: app.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Check if virtual environment exists
    venv_path = Path('.venv')
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        result = subprocess.run([sys.executable, '-m', 'venv', '.venv'])
        if result.returncode != 0:
            print("❌ Failed to create virtual environment. Ensure your system's Python 3 is complete (e.g., 'sudo apt install python3-venv' on Ubuntu).")
            sys.exit(1)
        print("✅ Virtual environment created")
    
    # Determine the correct pip and python paths
    if os.name == 'nt':  # Windows
        pip_path = Path('.venv/Scripts/pip')
        python_path = Path('.venv/Scripts/python')
    else:  # Unix/Linux/MacOS
        pip_path = Path('.venv/bin/pip')
        python_path = Path('.venv/bin/python')
    
    # Upgrade pip and setuptools within the venv
    print("⬆️ Upgrading pip and setuptools in the virtual environment...")
    result = subprocess.run([str(pip_path), 'install', '--upgrade', 'pip', 'setuptools'])
    if result.returncode == 0:
        print("✅ pip and setuptools upgraded successfully")
    else:
        print("❌ Failed to upgrade pip and setuptools. This might cause dependency installation issues.")
    
    # Install dependencies
    requirements_file = Path('requirements.txt')
    if requirements_file.exists():
        print("📥 Installing dependencies from requirements.txt...")
        result = subprocess.run([str(pip_path), 'install', '-r', 'requirements.txt'])
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
        else:
            print("❌ Failed to install dependencies. Check the error messages above.")
            sys.exit(1)
    else:
        print("⚠️ No requirements.txt found. Skipping dependency installation.")
    
    # Check for SSL certificates directory
    ssl_dir = Path('ssl')
    if ssl_dir.exists():
        cert_script = ssl_dir / 'gen-cert.sh'
        if cert_script.exists():
            print("🔐 SSL certificate generator found at ssl/gen-cert.sh")
            print("💡 Run it manually if you need SSL certificates: ./ssl/gen-cert.sh")
    
    # Create necessary directories if they don't exist
    backup_dirs = ['static/css', 'static/js', 'templates/backup/modals', 'tests', 'utils']
    for dir_path in backup_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Check for database initialization
    models_file = Path('models.py')
    if models_file.exists():
        print("📊 Database models found. Make sure to initialize your database if needed.")
    
    # Set environment variables
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['FLASK_DEBUG'] = '1'  # Enable debug mode for development
    
    # Check for config file
    config_file = Path('config.py')
    if config_file.exists():
        print("⚙️ Configuration file found")
    else:
        print("⚠️ No config.py found. Make sure to create one with your settings.")
    
    print("\n🎯 Starting Flask Backup Application...")
    print("📍 The application will be available at: http://localhost:5000")
    print("🔧 Features available:")
    print("   • Database backup and restore")
    print("   • GPG encryption for backups")
    print("   • Customer management")
    print("   • SSL support (if configured)")
    print("\n💡 Press Ctrl+C to stop the server")
    print("-" * 50)

    # Ensure admin user exists before starting the app
    admin_script = Path('scripts/create_admin.py')
    if admin_script.exists():
        print("👤 Ensuring admin user exists...")
        result = subprocess.run([str(python_path), str(admin_script)])
        if result.returncode == 0:
            print("✅ Admin user check complete")
        else:
            print("⚠️ Admin user creation script failed. Check output above.")

    # Run the Flask application
    try:
        subprocess.run([str(python_path), 'app.py'])
    except KeyboardInterrupt:
        print("\n👋 Flask Backup Application stopped. Thank you!")
    except FileNotFoundError:
        print("❌ Error: Could not find the Python executable in the virtual environment.")
        print("Try deleting the .venv folder and running this script again.")
        sys.exit(1)

def check_pathlib_integration():
    """Check if pathlib integration is complete"""
    files_to_check = ['config.py', 'backup.py', 'app.py', 'backup_gpg.py']
    pathlib_files = []
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'from pathlib import Path' in content or 'import pathlib' in content:
                        pathlib_files.append(file_path)
            except Exception:
                pass
    
    if pathlib_files:
        print(f"✅ Pathlib integration found in: {', '.join(pathlib_files)}")
    else:
        print("💡 Consider integrating pathlib for better file handling")

if __name__ == '__main__':
    # Optional: Check pathlib integration status
    check_pathlib_integration()
    main()