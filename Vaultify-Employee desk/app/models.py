from .extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    designation = db.Column(db.String(120), default="")

class AuthToken(db.Model):
    __tablename__ = 'auth_links'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    used = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=None)  # True / False / None
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self, expiry_minutes=1440):  # 24 hours default
        return self.used or (datetime.utcnow() > self.created_at + timedelta(minutes=expiry_minutes))

class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(120), db.ForeignKey('users.email'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
