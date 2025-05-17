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
    __tablename__ = "auth_links"

    token = db.Column(db.String(255), primary_key=True)
    user_email = db.Column(db.String(120), db.ForeignKey('users.email'), nullable=False)
    used = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=False)

class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(120), db.ForeignKey('users.email'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
