from secrets import randbelow

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app import db
from app.models import Profile, User
from app.schemas import LoginSchema, RegisterSchema, user_schema


auth_bp = Blueprint("auth", __name__)
register_schema = RegisterSchema()
login_schema = LoginSchema()


def generate_account_number():
    while True:
        account_number = f"7{randbelow(1_000_000_000):09d}"
        if not User.query.filter_by(account_number=account_number).first():
            return account_number


@auth_bp.post("/register")
def register():
    try:
        data = register_schema.load(request.get_json() or {})
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


@auth_bp.post("/login")
def login():
    try:
        data = login_schema.load(request.get_json() or {})
    except ValidationError as error:
        return {"errors": error.messages}, 400

    user = User.query.filter_by(username=data["username"].lower()).first()
    if not user or not user.check_password(data["password"]):
        return {"message": "Invalid username or password."}, 401

    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
        "user": user_schema.dump(user),
    }


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    return {"access_token": create_access_token(identity=user_id)}
