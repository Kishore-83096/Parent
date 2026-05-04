from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from app.main.api.schema import user_schema
from app.main.api.services import (
    authenticate_user,
    change_user_password,
    delete_user_account,
    get_profile_payload,
    get_user_profile,
    remove_user_profile_picture,
    register_user,
    update_user_profile,
)


api_bp = Blueprint("parent_api", __name__)


@api_bp.post("/auth/register")
def register():
    return register_user(request.get_json() or {})


@api_bp.post("/auth/login")
def login():
    result, status_code = authenticate_user(request.get_json() or {})
    if status_code != 200:
        return result, status_code

    user = result
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
        "user": user_schema.dump(user),
    }


@api_bp.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    return {"access_token": create_access_token(identity=user_id)}


@api_bp.post("/auth/change-password")
@jwt_required()
def change_password():
    return change_user_password(int(get_jwt_identity()), request.get_json() or {})


@api_bp.get("/profile/")
@jwt_required()
def get_profile():
    return get_user_profile(int(get_jwt_identity()))


@api_bp.put("/profile/")
@jwt_required()
def update_profile():
    return update_user_profile(int(get_jwt_identity()), get_profile_payload())


@api_bp.delete("/account")
@jwt_required()
def delete_account():
    return delete_user_account(int(get_jwt_identity()), request.get_json() or {})


@api_bp.delete("/profile/picture")
@jwt_required()
def delete_profile_picture():
    return remove_user_profile_picture(int(get_jwt_identity()))
