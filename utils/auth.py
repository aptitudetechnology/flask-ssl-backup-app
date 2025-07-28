# This function is registered with Flask-Login to load a user from the session.
# Flask-Login uses this loader to fetch the current user from their user_id,
# which it stores in the session cookie after login.
#
# We define the loader function in utils/auth.py to keep authentication logic
# modular and maintainable. This function is registered with the LoginManager
# instance in app.py (or __init__.py) like so:
#
#     from utils.auth import load_user
#     login_manager.user_loader(load_user)
#
# NOTE: We import the User model inside the function to avoid circular imports.
def load_user(user_id):
    from models import User  # Avoid circular imports
    return User.query.get(int(user_id))
