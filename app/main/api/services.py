from io import BytesIO
from secrets import randbelow
from urllib.parse import urlparse
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from PIL import Image
from flask import current_app, request
from marshmallow import ValidationError
from werkzeug.utils import secure_filename

from app import db
from app.main.api.model import Profile, User
from app.main.api.schema import (
    ChangePasswordSchema,
    DeleteAccountSchema,
    LoginSchema,
    ProfileSchema,
    RegisterSchema,
    profile_schema,
    user_schema,
)


register_schema = RegisterSchema()
login_schema = LoginSchema()
delete_account_schema = DeleteAccountSchema()
change_password_schema = ChangePasswordSchema()
profile_update_schema = ProfileSchema(partial=True)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_PROFILE_IMAGE_SIZE = 50 * 1024


def generate_account_number():
    while True:
        account_number = f"7{randbelow(1_000_000_000):09d}"
        if not User.query.filter_by(account_number=account_number).first():
            return account_number


def register_user(payload):
    try:
        data = register_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    username = data["username"].lower()
    email = f"{username}@epost.com"

    if User.query.filter_by(username=username).first():
        return {"message": "Username is already registered."}, 409

    if User.query.filter_by(email=email).first():
        return {"message": "Email is already registered."}, 409

    user = User(username=username, email=email, account_number=generate_account_number())
    user.set_password(data["password"])
    user.profile = Profile(first_name=data.get("first_name"), last_name=data.get("last_name"))

    db.session.add(user)
    db.session.commit()

    return {"message": "User registered successfully.", "user": user_schema.dump(user)}, 201


def authenticate_user(payload):
    try:
        data = login_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    user = User.query.filter_by(username=data["username"].lower()).first()
    if not user or not user.check_password(data["password"]):
        return {"message": "Invalid username or password."}, 401

    return user, 200


def get_user_profile(user_id):
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {"message": "Profile not found."}, 404

    return profile_schema.dump(profile), 200


def update_user_profile(user_id, payload):
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        user = db.session.get(User, user_id)
        if not user:
            return {"message": "User not found."}, 404
        profile = Profile(user_id=user.id)
        db.session.add(profile)

    upload_error = save_profile_picture(profile, payload)
    if upload_error:
        return {"message": upload_error}, 400

    try:
        data = profile_update_schema.load(payload, instance=profile)
    except ValidationError as error:
        return {"errors": error.messages}, 400

    db.session.add(data)
    db.session.commit()

    return profile_schema.dump(data), 200


def get_profile_payload():
    if request.is_json:
        return request.get_json() or {}

    return request.form.to_dict()


def save_profile_picture(profile, payload):
    file = request.files.get("profile_picture")
    if not file or not file.filename:
        return None

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return "Profile picture must be a jpg, jpeg, png, or webp file."

    upload_file, public_id, upload_error = build_profile_picture_upload(file, extension)
    if upload_error:
        return upload_error

    cloudinary.config(secure=True)
    result = cloudinary.uploader.upload(
        upload_file,
        folder=current_app.config["CLOUDINARY_PROFILE_FOLDER"],
        public_id=public_id,
        resource_type="image",
        overwrite=False,
    )

    delete_cloudinary_image(profile.profile_picture)
    payload["profile_picture"] = result["secure_url"]
    return None


def remove_user_profile_picture(user_id):
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {"message": "Profile not found."}, 404

    if not profile.profile_picture:
        return {"message": "Profile picture not found."}, 404

    deleted, delete_error = delete_cloudinary_image(profile.profile_picture)
    if not deleted:
        return {"message": delete_error}, 502

    profile.profile_picture = None
    db.session.add(profile)
    db.session.commit()

    return {"message": "Profile picture removed successfully."}, 200


def delete_user_account(user_id, payload):
    try:
        data = delete_account_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    user = db.session.get(User, user_id)
    if not user:
        return {"message": "User not found."}, 404

    username = data["username"].lower()
    email = data["email"].lower()
    if user.username != username or user.email.lower() != email or not user.check_password(data["password"]):
        return {"message": "Username, email, or password is incorrect."}, 403

    profile = user.profile
    if profile:
        if profile.profile_picture:
            deleted, delete_error = delete_cloudinary_image(profile.profile_picture)
            if not deleted:
                return {"message": delete_error}, 502

        user.profile = None
        db.session.flush()

    db.session.delete(user)
    db.session.commit()

    return {"message": "Account deleted successfully."}, 200


def change_user_password(user_id, payload):
    try:
        data = change_password_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    user = db.session.get(User, user_id)
    if not user:
        return {"message": "User not found."}, 404

    username = data["username"].lower()
    email = data["email"].lower()
    if user.username != username or user.email.lower() != email or not user.check_password(data["current_password"]):
        return {"message": "Username, email, or current password is incorrect."}, 403

    if user.check_password(data["new_password"]):
        return {"message": "New password must be different from the current password."}, 400

    user.set_password(data["new_password"])
    db.session.add(user)
    db.session.commit()

    return {"message": "Password changed successfully."}, 200


def build_profile_picture_upload(file, extension):
    content = file.read()
    file.stream.seek(0)

    if len(content) <= MAX_PROFILE_IMAGE_SIZE:
        buffer = BytesIO(content)
        buffer.name = f"{uuid4().hex}.{extension}"
        return buffer, uuid4().hex, None

    compressed = compress_image_to_size(content, extension)
    if compressed is None:
        return None, None, "Unable to compress profile picture uplaod a new profil pic less than 350kb of size."

    compressed.name = f"{uuid4().hex}.{extension}"
    return compressed, uuid4().hex, None


def compress_image_to_size(content, extension):
    try:
        image = Image.open(BytesIO(content))
    except Exception:
        return None

    output_format = get_output_format(image, extension)
    image = normalize_image_mode(image, output_format)

    if output_format == "PNG":
        compressed = compress_png(image)
    else:
        compressed = compress_lossy_image(image, output_format)

    if compressed is None or compressed.getbuffer().nbytes > MAX_PROFILE_IMAGE_SIZE:
        return None

    compressed.seek(0)
    return compressed


def compress_lossy_image(image, output_format):
    working_image = image.copy()

    for scale in (1.0, 0.85, 0.7, 0.55, 0.4, 0.3):
        resized_image = resize_image(working_image, scale)
        for quality in (85, 75, 65, 55, 45, 35, 25):
            buffer = BytesIO()
            save_kwargs = {"format": output_format, "optimize": True}
            if output_format in {"JPEG", "WEBP"}:
                save_kwargs["quality"] = quality
            resized_image.save(buffer, **save_kwargs)
            if buffer.getbuffer().nbytes <= MAX_PROFILE_IMAGE_SIZE:
                buffer.seek(0)
                return buffer

    return None


def compress_png(image):
    working_image = image.copy()

    for scale in (1.0, 0.85, 0.7, 0.55, 0.4, 0.3):
        resized_image = resize_image(working_image, scale)
        buffer = BytesIO()
        resized_image.save(buffer, format="PNG", optimize=True)
        if buffer.getbuffer().nbytes <= MAX_PROFILE_IMAGE_SIZE:
            buffer.seek(0)
            return buffer

    return None


def resize_image(image, scale):
    if scale >= 1.0:
        return image.copy()

    width = max(1, int(image.width * scale))
    height = max(1, int(image.height * scale))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def get_output_format(image, extension):
    if extension == "jpg":
        return "JPEG"
    if extension == "jpeg":
        return "JPEG"
    if extension == "webp":
        return "WEBP"
    if extension == "png":
        return "PNG"
    if image.format in {"JPEG", "PNG", "WEBP"}:
        return image.format
    return "JPEG"


def normalize_image_mode(image, output_format):
    if output_format == "JPEG" and image.mode in {"RGBA", "LA", "P"}:
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha_image = image.convert("RGBA")
        background.paste(alpha_image, mask=alpha_image.getchannel("A"))
        return background

    if output_format in {"JPEG", "WEBP"} and image.mode not in {"RGB", "RGBA"}:
        return image.convert("RGB")

    return image


def delete_cloudinary_image(profile_picture_url):
    public_id = extract_cloudinary_public_id(profile_picture_url)
    if not public_id:
        return False, "Unable to identify the Cloudinary profile picture to delete."

    cloudinary.config(secure=True)
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
    except Exception:
        current_app.logger.exception("Cloudinary profile picture deletion failed.")
        return False, "Unable to delete profile picture from Cloudinary. Account was not deleted."

    if result.get("result") in {"ok", "not found", "not_found"}:
        return True, None

    current_app.logger.warning("Cloudinary delete returned unexpected response: %s", result)
    return False, "Unable to confirm profile picture deletion. Account was not deleted."


def extract_cloudinary_public_id(profile_picture_url):
    if not profile_picture_url:
        return None

    parsed_url = urlparse(profile_picture_url)
    path = parsed_url.path or ""
    marker = "/upload/"
    if marker not in path:
        return None

    upload_path = path.split(marker, 1)[1]
    parts = [part for part in upload_path.split("/") if part]
    while parts and (parts[0].startswith("v") and parts[0][1:].isdigit() or "," in parts[0]):
        parts.pop(0)

    if not parts:
        return None

    last_part = parts[-1]
    if "." in last_part:
        parts[-1] = last_part.rsplit(".", 1)[0]

    return "/".join(parts)
