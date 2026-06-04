from marshmallow import ValidationError, fields, validate, validates_schema

from app import ma
from app.main.api.model import Contact, Profile, User


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


class ContactSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Contact
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


class AccountNumberSearchSchema(ma.Schema):
    account_number = fields.String(
        required=True,
        validate=[
            validate.Length(equal=10),
            validate.Regexp(
                r"^7\d{9}$",
                error="Account number must start with 7 and contain exactly 10 digits.",
            ),
        ],
    )


class SaveContactSchema(AccountNumberSearchSchema):
    alias_name = fields.String(
        required=True,
        validate=[
            validate.Length(min=1, max=120),
            validate.Regexp(r".*\S.*", error="Alias name cannot be blank."),
        ],
    )


class MessagingAuthorizationSchema(ma.Schema):
    sender_user_id = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1),
    )
    recipient_account_number = fields.String(
        required=True,
        validate=[
            validate.Length(equal=10),
            validate.Regexp(
                r"^7\d{9}$",
                error="Recipient account number must start with 7 and contain exactly 10 digits.",
            ),
        ],
    )


class PresenceVisibilityPolicySchema(ma.Schema):
    owner_user_id = fields.Integer(
        strict=True,
        validate=validate.Range(min=1),
        load_default=None,
    )
    viewer_user_id = fields.Integer(
        strict=True,
        validate=validate.Range(min=1),
        load_default=None,
    )
    candidate_user_ids = fields.List(
        fields.Integer(
            strict=True,
            validate=validate.Range(min=1),
        ),
        required=True,
        validate=validate.Length(max=500),
    )

    @validates_schema
    def validate_scope(self, data, **kwargs):
        if bool(data.get("owner_user_id")) == bool(data.get("viewer_user_id")):
            raise ValidationError(
                {
                    "presence": [
                        "Exactly one of owner_user_id or viewer_user_id is required."
                    ]
                }
            )


class StoryAudiencePolicySchema(ma.Schema):
    owner_user_id = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1),
    )
    audience_account_numbers = fields.List(
        fields.String(
            validate=[
                validate.Length(equal=10),
                validate.Regexp(
                    r"^7\d{9}$",
                    error="Account number must start with 7 and contain exactly 10 digits.",
                ),
            ],
        ),
        load_default=None,
    )


class GroupMemberResolveSchema(ma.Schema):
    owner_user_id = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1),
    )
    member_account_numbers = fields.List(
        fields.String(
            validate=[
                validate.Length(equal=10),
                validate.Regexp(
                    r"^7\d{9}$",
                    error="Account number must start with 7 and contain exactly 10 digits.",
                ),
            ],
        ),
        required=True,
        validate=validate.Length(min=1, max=100),
    )


class StoryVisibilityPolicySchema(ma.Schema):
    owner_user_id = fields.Integer(
        strict=True,
        validate=validate.Range(min=1),
        load_default=None,
    )
    owner_account_number = fields.String(
        validate=[
            validate.Length(equal=10),
            validate.Regexp(
                r"^7\d{9}$",
                error="Owner account number must start with 7 and contain exactly 10 digits.",
            ),
        ],
        load_default=None,
    )
    viewer_user_id = fields.Integer(
        strict=True,
        validate=validate.Range(min=1),
        load_default=None,
    )
    viewer_account_number = fields.String(
        validate=[
            validate.Length(equal=10),
            validate.Regexp(
                r"^7\d{9}$",
                error="Viewer account number must start with 7 and contain exactly 10 digits.",
            ),
        ],
        load_default=None,
    )

    @validates_schema
    def validate_identifiers(self, data, **kwargs):
        if not data.get("owner_user_id") and not data.get("owner_account_number"):
            raise ValidationError(
                {"owner": ["Owner user id or account number is required."]}
            )

        if not data.get("viewer_user_id") and not data.get("viewer_account_number"):
            raise ValidationError(
                {"viewer": ["Viewer user id or account number is required."]}
            )


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
contact_schema = ContactSchema()
