from uuid import uuid4

import cloudinary
import cloudinary.uploader
from flask import Blueprint, current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from werkzeug.utils import secure_filename

from app import db
from app.models import Profile, User
from app.schemas import ProfileSchema, profile_schema


profile_bp = Blueprint("profile", __name__)
profile_update_schema = ProfileSchema(partial=True)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


@profile_bp.get("/")
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {"message": "Profile not found."}, 404

    return profile_schema.dump(profile)


@profile_bp.put("/")
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        user = db.session.get(User, user_id)
        if not user:
            return {"message": "User not found."}, 404
        profile = Profile(user_id=user.id)
        db.session.add(profile)

    payload = get_profile_payload()
    upload_error = save_profile_picture(payload)
    if upload_error:
        return {"message": upload_error}, 400

    try:
        data = profile_update_schema.load(payload, instance=profile)
    except ValidationError as error:
        return {"errors": error.messages}, 400

    db.session.add(data)
    db.session.commit()

    return profile_schema.dump(data)


def get_profile_payload():
    if request.is_json:
        return request.get_json() or {}

    return request.form.to_dict()


def save_profile_picture(payload):
    file = request.files.get("profile_picture")
    if not file or not file.filename:
        return None

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return "Profile picture must be a jpg, jpeg, png, or webp file."

    cloudinary.config(secure=True)
    result = cloudinary.uploader.upload(
        file,
        folder=current_app.config["CLOUDINARY_PROFILE_FOLDER"],
        public_id=uuid4().hex,
        resource_type="image",
        overwrite=False,
    )

    payload["profile_picture"] = result["secure_url"]
    return None


@profile_bp.delete("/")
@jwt_required()
def delete_profile():
    user_id = int(get_jwt_identity())
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {"message": "Profile not found."}, 404

    db.session.delete(profile)
    db.session.commit()

    return {"message": "Profile deleted successfully."}
