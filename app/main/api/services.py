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
from app.main.api.cache import (
    get_cached_contacts,
    get_cached_profile,
    invalidate_contacts_cache,
    invalidate_profile_cache,
    set_cached_contacts,
    set_cached_profile,
)
from app.main.api.model import Contact, Profile, User
from app.main.api.schema import (
    AccountNumberSearchSchema,
    ChangePasswordSchema,
    DeleteAccountSchema,
    LoginSchema,
    ProfileSchema,
    RegisterSchema,
    SaveContactSchema,
    profile_schema,
    user_schema,
)


register_schema = RegisterSchema()
login_schema = LoginSchema()
account_number_search_schema = AccountNumberSearchSchema()
save_contact_schema = SaveContactSchema()
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
    cached_profile = get_cached_profile(user_id)
    if cached_profile is not None:
        return cached_profile, 200

    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {"message": "Profile not found."}, 404

    profile_data = profile_schema.dump(profile)
    set_cached_profile(user_id, profile_data)
    return profile_data, 200


def search_user_by_account_number(payload):
    try:
        data = account_number_search_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    user = User.query.filter_by(account_number=data["account_number"]).first()
    if not user:
        return {"message": "Phone number not in Parrot."}, 404

    return build_person_search_result(user), 200


def build_person_search_result(user):
    return {
        "first_name": user.profile.first_name if user.profile else None,
        "last_name": user.profile.last_name if user.profile else None,
        "username": user.username,
    }


def get_saved_contacts(owner_user_id):
    cached_contacts = get_cached_contacts(owner_user_id)
    if cached_contacts is not None:
        return {"contacts": cached_contacts}, 200

    owner = db.session.get(User, owner_user_id)
    if not owner:
        return {"message": "User not found."}, 404

    return {"contacts": refresh_saved_contacts_cache(owner.id)}, 200


def save_searched_contact(owner_user_id, payload):
    try:
        data = save_contact_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    owner = db.session.get(User, owner_user_id)
    if not owner:
        return {"message": "User not found."}, 404

    contact_user = User.query.filter_by(account_number=data["account_number"]).first()
    if not contact_user:
        return {"message": "Phone number not in Parrot."}, 404

    if contact_user.id == owner.id:
        return {"message": "You cannot save your own account as a contact."}, 400

    alias_name = data["alias_name"].strip()
    contact = Contact.query.filter_by(owner_user_id=owner.id, contact_user_id=contact_user.id).first()
    if contact:
        contact.alias_name = alias_name
        message = "Contact alias updated successfully."
        status_code = 200
    else:
        contact = Contact(owner_user_id=owner.id, contact_user_id=contact_user.id, alias_name=alias_name)
        message = "Contact saved successfully."
        status_code = 201

    db.session.add(contact)
    db.session.commit()
    refresh_saved_contacts_cache(owner.id)

    return {"message": message, "contact": build_saved_contact_result(contact)}, status_code


def update_saved_contact_alias(owner_user_id, payload):
    try:
        data = save_contact_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    contact, error_response, status_code = get_saved_contact_by_account_number(
        owner_user_id,
        data["account_number"],
    )
    if error_response:
        return error_response, status_code

    contact.alias_name = data["alias_name"].strip()
    db.session.add(contact)
    db.session.commit()
    refresh_saved_contacts_cache(owner_user_id)

    return {
        "message": "Contact alias updated successfully.",
        "contact": build_saved_contact_result(contact),
    }, 200


def block_saved_contact(owner_user_id, payload):
    return set_saved_contact_blocked(owner_user_id, payload, True)


def unblock_saved_contact(owner_user_id, payload):
    return set_saved_contact_blocked(owner_user_id, payload, False)


def set_saved_contact_blocked(owner_user_id, payload, blocked):
    try:
        data = account_number_search_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    contact, error_response, status_code = get_saved_contact_by_account_number(
        owner_user_id,
        data["account_number"],
    )
    if error_response:
        return error_response, status_code

    contact.blocked = blocked
    db.session.add(contact)
    db.session.commit()
    refresh_saved_contacts_cache(owner_user_id)

    message = "Contact blocked successfully." if blocked else "Contact unblocked successfully."
    return {"message": message, "contact": build_saved_contact_result(contact)}, 200


def delete_saved_contact(owner_user_id, payload):
    try:
        data = account_number_search_schema.load(payload or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    contact, error_response, status_code = get_saved_contact_by_account_number(
        owner_user_id,
        data["account_number"],
    )
    if error_response:
        return error_response, status_code

    db.session.delete(contact)
    db.session.commit()
    refresh_saved_contacts_cache(owner_user_id)

    return {"message": "Contact deleted successfully."}, 200


def get_saved_contact_by_account_number(owner_user_id, account_number):
    owner = db.session.get(User, owner_user_id)
    if not owner:
        return None, {"message": "User not found."}, 404

    contact_user = User.query.filter_by(account_number=account_number).first()
    if not contact_user:
        return None, {"message": "Phone number not in Parrot."}, 404

    contact = Contact.query.filter_by(owner_user_id=owner.id, contact_user_id=contact_user.id).first()
    if not contact:
        return None, {"message": "Contact not found."}, 404

    return contact, None, None


def build_saved_contact_result(contact):
    return {
        "alias_name": contact.alias_name,
        "account_number": contact.contact_user.account_number,
        "blocked": contact.blocked,
        "first_name": contact.contact_user.profile.first_name if contact.contact_user.profile else None,
        "last_name": contact.contact_user.profile.last_name if contact.contact_user.profile else None,
        "username": contact.contact_user.username,
    }


def get_saved_contacts_query(owner_user_id):
    return Contact.query.filter_by(owner_user_id=owner_user_id).order_by(Contact.alias_name.asc(), Contact.id.asc())


def refresh_saved_contacts_cache(owner_user_id):
    contacts_data = [build_saved_contact_result(contact) for contact in get_saved_contacts_query(owner_user_id).all()]
    set_cached_contacts(owner_user_id, contacts_data)
    return contacts_data


def invalidate_contact_caches_for_contact_user(contact_user_id):
    owner_ids = db.session.query(Contact.owner_user_id).filter_by(contact_user_id=contact_user_id).distinct().all()
    for owner_id, in owner_ids:
        invalidate_contacts_cache(owner_id)


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
    invalidate_contact_caches_for_contact_user(user_id)

    profile_data = profile_schema.dump(data)
    set_cached_profile(user_id, profile_data)
    return profile_data, 200


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
    set_cached_profile(user_id, profile_schema.dump(profile))

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

    affected_contact_owner_ids = [
        owner_id
        for owner_id, in db.session.query(Contact.owner_user_id)
        .filter_by(contact_user_id=user.id)
        .distinct()
        .all()
    ]

    Contact.query.filter_by(owner_user_id=user.id).delete(synchronize_session=False)
    Contact.query.filter_by(contact_user_id=user.id).delete(synchronize_session=False)

    db.session.delete(user)
    db.session.commit()
    invalidate_profile_cache(user_id)
    invalidate_contacts_cache(user_id)
    for owner_id in affected_contact_owner_ids:
        invalidate_contacts_cache(owner_id)

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
