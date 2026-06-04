from hmac import compare_digest

from flask import Blueprint, current_app, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required

from app.main.api.schema import user_schema
from app.main.api.services import (
    authenticate_user,
    authorize_messaging_pair,
    authorize_story_visibility_policy,
    block_saved_contact,
    change_user_password,
    create_messaging_token,
    delete_saved_contact,
    delete_user_account,
    get_profile_payload,
    get_saved_contact_detail,
    get_saved_contacts,
    get_user_profile,
    ghost_saved_contact,
    remove_user_profile_picture,
    register_user,
    resolve_group_member_contacts,
    resolve_presence_visibility_policy,
    resolve_story_audience_policy,
    save_searched_contact,
    search_user_by_account_number,
    unghost_saved_contact,
    unblock_saved_contact,
    update_saved_contact_alias,
    update_user_profile,
)


api_bp = Blueprint("parent_api", __name__)


def is_internal_service_request():
    expected_token = current_app.config.get("INTERNAL_SERVICE_TOKEN") or ""
    provided_token = request.headers.get("X-Internal-Service-Token", "")

    return bool(expected_token) and compare_digest(provided_token, expected_token)


@api_bp.post("/internal/messaging/authorize")
def authorize_messaging():
    if not is_internal_service_request():
        return {"message": "Unauthorized internal service request."}, 401

    return authorize_messaging_pair(request.get_json() or {})


@api_bp.post("/internal/presence/visibility")
def resolve_presence_visibility():
    if not is_internal_service_request():
        return {"message": "Unauthorized internal service request."}, 401

    return resolve_presence_visibility_policy(request.get_json() or {})


@api_bp.post("/internal/stories/audience")
def resolve_story_audience():
    if not is_internal_service_request():
        return {"message": "Unauthorized internal service request."}, 401

    return resolve_story_audience_policy(request.get_json() or {})


@api_bp.post("/internal/groups/members/resolve")
def resolve_group_members():
    if not is_internal_service_request():
        return {"message": "Unauthorized internal service request."}, 401

    return resolve_group_member_contacts(request.get_json() or {})


@api_bp.post("/internal/stories/visibility")
def authorize_story_visibility():
    if not is_internal_service_request():
        return {"message": "Unauthorized internal service request."}, 401

    return authorize_story_visibility_policy(request.get_json() or {})


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


@api_bp.post("/messaging/token")
@jwt_required()
def messaging_token():
    return create_messaging_token(int(get_jwt_identity()))


@api_bp.post("/auth/change-password")
@jwt_required()
def change_password():
    return change_user_password(int(get_jwt_identity()), request.get_json() or {})


@api_bp.get("/profile/")
@jwt_required()
def get_profile():
    return get_user_profile(int(get_jwt_identity()))


@api_bp.post("/users/search")
@jwt_required()
def search_users():
    return search_user_by_account_number(request.get_json() or {})


@api_bp.get("/contacts")
@jwt_required()
def get_contacts():
    return get_saved_contacts(int(get_jwt_identity()))


@api_bp.get("/contacts/<account_number>")
@jwt_required()
def get_contact_detail(account_number):
    return get_saved_contact_detail(int(get_jwt_identity()), account_number)


@api_bp.post("/contacts")
@jwt_required()
def save_contact():
    return save_searched_contact(int(get_jwt_identity()), request.get_json() or {})


@api_bp.patch("/contacts/alias")
@jwt_required()
def update_contact_alias():
    return update_saved_contact_alias(int(get_jwt_identity()), request.get_json() or {})


@api_bp.post("/contacts/block")
@jwt_required()
def block_contact():
    return block_saved_contact(int(get_jwt_identity()), request.get_json() or {})


@api_bp.post("/contacts/unblock")
@jwt_required()
def unblock_contact():
    return unblock_saved_contact(int(get_jwt_identity()), request.get_json() or {})


@api_bp.post("/contacts/ghost")
@jwt_required()
def ghost_contact():
    return ghost_saved_contact(int(get_jwt_identity()), request.get_json() or {})


@api_bp.post("/contacts/unghost")
@jwt_required()
def unghost_contact():
    return unghost_saved_contact(int(get_jwt_identity()), request.get_json() or {})


@api_bp.delete("/contacts")
@jwt_required()
def delete_contact():
    return delete_saved_contact(int(get_jwt_identity()), request.get_json() or {})


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
