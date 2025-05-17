from .extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    designation = db.Column(db.String(120), default="")

from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

class AuthToken(db.Model):
    __tablename__ = 'auth_links'

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)

    approval_token = db.Column(db.String(64), unique=True, nullable=False)
    approval_used = db.Column(db.Boolean, default=False)

    login_token = db.Column(db.String(64), unique=True, nullable=False)
    login_used = db.Column(db.Boolean, default=False)

    approved = db.Column(db.Boolean, default=None)  # True / False / None
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self, expiry_minutes=1440):
        """Token expired if 24 hrs passed since creation."""
        return datetime.utcnow() > self.created_at + timedelta(minutes=expiry_minutes)

    def is_approval_valid(self):
        return not self.approval_used and not self.is_expired()

    def is_login_valid(self):
        return not self.login_used and not self.is_expired()

class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(120), db.ForeignKey('users.email'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship("User", backref="chats", foreign_keys=[sender_id])
