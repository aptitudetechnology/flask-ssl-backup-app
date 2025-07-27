from flask import Blueprint

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

# ... your route definitions ...