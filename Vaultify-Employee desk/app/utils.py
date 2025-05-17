import secrets
from flask_mail import Message
from flask import current_app
from .extensions import db, mail 
from .models import User, AuthToken, Chat

def init_supabase():
    pass

def generate_token():
    return secrets.token_urlsafe(32)

# -----------------------------
# Email Handling
# -----------------------------

def send_email(to_email, subject, html_content):
    try:
        msg = Message(subject, recipients=[to_email], html=html_content)
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed: {e}")
        return False

def send_admin_request_email(name, email, approve_url, discard_url):
    subject = "New Vaultify Access Request"
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; }}
            .container {{ background-color: #fff; max-width: 600px; margin: 30px auto; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); }}
            .header {{ text-align: center; font-size: 20px; font-weight: bold; color: #333; margin-bottom: 20px; }}
            .details {{ font-size: 16px; color: #555; line-height: 1.5; margin-bottom: 30px; }}
            .actions {{ text-align: center; }}
            .button {{ padding: 10px 20px; border-radius: 5px; text-decoration: none; color: #fff; font-weight: bold; margin: 0 10px; display: inline-block; }}
            .approve {{ background-color: #28a745; }}
            .discard {{ background-color: #dc3545; }}
            .footer {{ font-size: 12px; color: #888; text-align: center; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">📨 Vaultify Access Request</div>
            <div class="details">
                <p><strong>Name:</strong> {name}<br><strong>Email:</strong> {email}</p>
            </div>
            <div class="actions">
                <a href="{approve_url}" class="button approve">Approve</a>
                <a href="{discard_url}" class="button discard">Discard</a>
            </div>
            <div class="footer">
                This request was generated automatically by Vaultify.
            </div>
        </div>
    </body>
    </html>
    """
    return send_email("utsavamistry30@gmail.com", subject, body)

def send_approval_status_mail(email, approved=True, login_url=None):
    if approved and login_url:
        subject = "Vaultify Access Approved"
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f9f9f9; }}
                .container {{ max-width: 600px; margin: 30px auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1); text-align: center; }}
                h3 {{ color: #28a745; }}
                p {{ color: #333; font-size: 16px; }}
                .button {{ display: inline-block; padding: 10px 20px; margin-top: 15px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h3>Your request has been approved</h3>
                <p>Welcome to Vaultify! You can now access the platform using the link below:</p>
                <a href="{login_url}" class="button">Login to Vaultify</a>
                <p class="footer">{login_url}</p>
            </div>
        </body>
        </html>
        """
    else:
        subject = "Vaultify Access Denied"
        body = """
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f9f9f9; }}
                .container {{ max-width: 600px; margin: 30px auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1); text-align: center; }}
                h3 {{ color: #dc3545; }}
                p {{ color: #555; font-size: 16px; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h3>We're sorry</h3>
                <p>Your request for Vaultify access has been denied at this time.</p>
                <p class="footer">If you believe this was a mistake, please contact the administrator.</p>
            </div>
        </body>
        </html>
        """
    return send_email(email, subject, body)

# -----------------------------
# DB Actions
# -----------------------------

def insert_user(email, name, hashed_password):
    user = User(email=email, name=name, password=hashed_password)
    db.session.add(user)
    db.session.commit()
    return user

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def approve_user(email, designation):
    user = get_user_by_email(email)
    if user:
        user.approved = True
        user.designation = designation
        db.session.commit()

def discard_user(email):
    AuthToken.query.filter_by(user_email=email).delete()
    User.query.filter_by(email=email).delete()
    db.session.commit()

def get_pending_users():
    return User.query.filter_by(approved=False).all()

def insert_auth_token(token, email):
    entry = AuthToken(token=token, user_email=email)
    db.session.add(entry)
    db.session.commit()
    return entry

def get_auth_token(token):
    return AuthToken.query.filter_by(token=token).first()

def mark_token_used(token, approved=None):
    auth = get_auth_token(token)
    if auth:
        auth.used = True
        if approved is not None:
            auth.approved = approved
        db.session.commit()

def insert_chat(sender_id, message, file_data=None):
    file_url = file_data["url"] if file_data else None
    chat = Chat(sender_id=sender_id, message=message, file_url=file_url)
    db.session.add(chat)
    db.session.commit()
    return chat

def get_all_chats():
    return db.session.query(Chat).order_by(Chat.timestamp.asc()).all()

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
