from datetime import datetime, timezone

from passlib.hash import argon2

from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    account_number = db.Column(db.String(10), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    profile = db.relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = argon2.hash(password)

    def check_password(self, password):
        return argon2.verify(password, self.password_hash)


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    profile_picture = db.Column(db.String(500), nullable=True)
    card_number = db.Column(db.String(32), nullable=True)
    card_name = db.Column(db.String(120), nullable=True)
    card_type = db.Column(db.String(20), nullable=True)
    dr_no = db.Column(db.String(50), nullable=True)
    floor = db.Column(db.String(50), nullable=True)
    street = db.Column(db.String(120), nullable=True)
    area = db.Column(db.String(120), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    state = db.Column(db.String(120), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="profile")
