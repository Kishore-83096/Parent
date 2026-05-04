from marshmallow import ValidationError, fields, validate, validates_schema

from app import ma
from app.main.api.model import Profile, User


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
    confirm_password = fields.String(required=True)
    first_name = fields.String(load_default=None)
    last_name = fields.String(load_default=None)

    @validates_schema
    def validate_passwords(self, data, **kwargs):
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError({"confirm_password": ["Passwords do not match."]})


class LoginSchema(ma.Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)


class DeleteAccountSchema(ma.Schema):
    username = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(required=True)


class ChangePasswordSchema(ma.Schema):
    username = fields.String(required=True)
    email = fields.Email(required=True)
    current_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=validate.Length(min=8))


user_schema = UserSchema()
profile_schema = ProfileSchema()
