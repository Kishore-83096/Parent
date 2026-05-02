from marshmallow import fields, validate

from app import ma
from app.models import Profile, User


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ("password_hash",)


class ProfileSchema(ma.SQLAlchemyAutoSchema):
    card_type = fields.String(validate=validate.OneOf(["credit", "debit"]))

    class Meta:
        model = Profile
        load_instance = True
        include_fk = True


class RegisterSchema(ma.Schema):
    username = fields.String(
        required=True,
        validate=[
            validate.Length(min=3, max=80),
            validate.Regexp(
                r"^[A-Za-z0-9_]+$",
                error="Username can contain only letters, numbers, and underscores.",
            ),
        ],
    )
    password = fields.String(required=True, validate=validate.Length(min=8))
    first_name = fields.String(load_default=None)
    last_name = fields.String(load_default=None)


class LoginSchema(ma.Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)


user_schema = UserSchema()
profile_schema = ProfileSchema()
