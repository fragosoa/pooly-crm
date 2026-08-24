from functools import wraps

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

import db


def admin_required(fn):
    """Same JWT pooly-core issues, plus an is_admin check against the shared
    users table. 401 for missing/invalid token, 403 for a valid token
    belonging to a non-admin user."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        username = get_jwt_identity()
        if not db.is_user_admin(username):
            return jsonify({"msg": "Admin access required"}), 403
        return fn(*args, **kwargs)

    return wrapper
