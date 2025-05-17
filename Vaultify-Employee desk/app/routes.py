from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from .models import *
from .utils import *
import os
from datetime import timedelta, datetime

main = Blueprint("main", __name__)

UPLOAD_FOLDER = "app/static/uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "utsavamistry30@gmail.com")


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

                token = generate_token()
                insert_auth_token(token, email)

                approve_url = url_for("main.approve_token", token=token, _external=True)
                discard_url = url_for("main.discard_token", token=token, _external=True)
                login_url = url_for("main.login_token", token=token, _external=True)

                admin_email_sent = send_admin_request_email(name, email, approve_url, discard_url)
                user_email_sent = send_approval_status_mail(email, approved=False)

                if not admin_email_sent or not user_email_sent:
                    flash("Failed to send notification emails. Please contact admin.")
                    return render_template("auth.html")

                flash("Registration request sent. Await approval.")

    return render_template("auth.html")

# -------------------------
# One-time token login
# -------------------------

@main.route('/login/<token>', methods=['GET'])
def login_token(token):
    token_entry = get_auth_token(token)

    # Check if token exists
    if not token_entry:
        flash("Invalid token.", "danger")
        return redirect(url_for("auth"))

    # Check if token already used or expired
    if token_entry.used:
        flash("This token has already been used.", "danger")
        return redirect(url_for("main.auth"))

    if datetime.utcnow() > token_entry.created_at + timedelta(minutes=1440):
        flash("This token has expired.", "danger")
        return redirect(url_for("main.auth"))

    # Get the associated user
    user = User.query.filter_by(email=token_entry.user_email).first()
    if not user or not user.approved:
        flash("User not approved or does not exist.", "danger")
        return redirect(url_for("main.auth"))

    # Log the user in (save in session)
    session['user_id'] = user.id
    token_entry.used = True
    db.session.commit()

    flash("Logged in successfully!", "success")
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

    login_url = url_for("main.token_login", token=token, _external=True)
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

@main.route("/landing", methods=["GET"])
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
# AJAX Chat Message Submission
# -------------------------

from flask import jsonify  # Add this import

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

        # Validate input
        if not message and not file:
            return jsonify({"success": False, "error": "Message or file required"}), 400

        file_data = None
        if file and file.filename:
            # Validate file
            filename = secure_filename(file.filename)
            if not allowed_file(filename):
                return jsonify({"success": False, "error": "File type not allowed"}), 400

            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            if file_size > MAX_FILE_SIZE:
                return jsonify({"success": False, "error": "File too large (max 100MB)"}), 400
            file.seek(0)

            # Save file
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            file_url = url_for('static', filename=f'uploads/{filename}', _external=True)
            file_data = {"url": file_url, "name": filename}

        # Create chat entry
        chat = insert_chat(user.id, message, file_data)
        if not chat:
            return jsonify({"success": False, "error": "Failed to save message"}), 500

        # Return JSON response
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
