from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from .models import *
from .utils import *
from datetime import timedelta, datetime
import os

main = Blueprint("main", __name__)

UPLOAD_FOLDER = "app/static/uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "utsavamistry30@gmail.com")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
TOKEN_EXPIRY_HOURS = 24

# -------------------------
# AUTH + REGISTER
# -------------------------

@main.route("/", methods=["GET", "POST"])
def auth():
    if "email" in session:
        return redirect(url_for("main.landing"))

    if request.method == "POST":
        action = request.form.get("action")
        email = request.form["email"]
        password = request.form["password"]

        if action == "login":
            user = get_user_by_email(email)
            if user and user.approved:
                if check_password_hash(user.password, password):
                    session["email"] = email
                    return redirect(url_for("main.landing"))
                else:
                    flash("Incorrect password.")
            elif user:
                flash("Request submitted. Awaiting admin approval.")
            else:
                flash("No user found. Please request access.")

        elif action == "register":
            name = request.form["name"]
            user = get_user_by_email(email)
            if user:
                flash("User already exists or pending approval.")
            else:
                hashed_password = generate_password_hash(password)
                insert_user(email, name, hashed_password)

                approval_token = generate_token()
                insert_auth_token(approval_token, email)

                approve_url = url_for("main.approve_token", token=approval_token, _external=True)
                discard_url = url_for("main.discard_token", token=approval_token, _external=True)

                admin_email_sent = send_admin_request_email(name, email, approve_url, discard_url)
                user_email_sent = send_approval_status_mail(email, approved=False)

                if not admin_email_sent or not user_email_sent:
                    flash("Failed to send notification emails. Please contact admin.")
                    return render_template("auth.html")

                flash("Registration request sent. Await approval.")

    return render_template("auth.html")

# -------------------------
# One-time Token Login
# -------------------------

@main.route("/login/<token>")
def token_login(token):
    auth_link = get_auth_token(token)
    if not auth_link or auth_link.used or not auth_link.approved:
        return "Invalid or expired login token."

    if datetime.utcnow() - auth_link.created_at > timedelta(hours=TOKEN_EXPIRY_HOURS):
        return "Login token expired."

    session["email"] = auth_link.user_email
    mark_token_used(token, approved=True)

    return redirect(url_for("main.landing"))

# -------------------------
# Admin Approve / Discard
# -------------------------

@main.route("/approve/<token>")
def approve_token(token):
    auth_link = get_auth_token(token)
    if not auth_link or auth_link.used:
        return "Invalid or already used approval link."
    return render_template("approve_input.html", email=auth_link.user_email, token=token)

@main.route("/approve/submit", methods=["POST"])
def submit_approval():
    token = request.form["token"]
    email = request.form["email"]
    designation = request.form["designation"]

    approve_user(email, designation)
    mark_token_used(token, approved=True)

    # Generate new login token
    login_token = generate_token()
    insert_auth_token(login_token, email)

    login_url = url_for("main.token_login", token=login_token, _external=True)
    send_approval_status_mail(email, approved=True, login_url=login_url)

    return "User approved and notified."

@main.route("/discard/<token>")
def discard_token(token):
    auth_link = get_auth_token(token)
    if not auth_link or auth_link.used:
        return "Invalid or already used discard link."

    email = auth_link.user_email
    discard_user(email)
    mark_token_used(token, approved=False)

    send_approval_status_mail(email, approved=False)
    return "User discarded and notified."

# -------------------------
# Logout
# -------------------------

@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.auth"))

# -------------------------
# Landing Page
# -------------------------

@main.route("/landing")
def landing():
    if "email" not in session:
        return redirect(url_for("main.auth"))

    email = session["email"]
    user = get_user_by_email(email)

    chats = get_all_chats()
    for chat in chats:
        if chat.timestamp:
            chat.timestamp += timedelta(hours=5, minutes=30)

    pending_requests = get_pending_users() if user.designation == "superuser" else []
    return render_template("landing.html", user=user, chats=chats, requests=pending_requests)

# -------------------------
# Send Message via Chat
# -------------------------

@main.route("/send_message", methods=["POST"])
def send_message():
    if "email" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        email = session["email"]
        user = get_user_by_email(email)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        message = request.form.get("message", "").strip()
        file = request.files.get("file")

        if not message and not file:
            return jsonify({"success": False, "error": "Message or file required"}), 400

        file_data = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            if not allowed_file(filename):
                return jsonify({"success": False, "error": "File type not allowed"}), 400

            file.seek(0, os.SEEK_END)
            if file.tell() > MAX_FILE_SIZE:
                return jsonify({"success": False, "error": "File too large (max 100MB)"}), 400
            file.seek(0)

            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            file_url = url_for('static', filename=f'uploads/{filename}', _external=True)
            file_data = {"url": file_url, "name": filename}

        chat = insert_chat(user.id, message, file_data)
        if not chat:
            return jsonify({"success": False, "error": "Failed to save message"}), 500

        return jsonify({
            "success": True,
            "message": {
                "content": message,
                "file": file_data,
                "sender": chat.sender.name,
                "timestamp": chat.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
