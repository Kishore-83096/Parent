from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.main.api.model import User


def premium_required():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated(*args, **kwargs):
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            if not user or not user.is_premium:
                return {"message": "Premium access required."}, 403
            return fn(*args, **kwargs)

        return decorated

    return wrapper
