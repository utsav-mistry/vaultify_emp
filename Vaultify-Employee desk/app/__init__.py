import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from dotenv import load_dotenv
from .utils import init_supabase
from .extensions import db, mail, migrate

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "default_secret")

    # Database configuration (Supabase PostgreSQL URL)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("POSTGRES_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
    app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
    app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "True") == "True"
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    from . import models
    migrate.init_app(app, db)

    # Register routes
    from .routes import main
    app.register_blueprint(main)

    return app
