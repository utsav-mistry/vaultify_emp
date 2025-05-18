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
        
                approval_token = generate_token()
                login_token = generate_token()
                insert_auth_token(email, approval_token, login_token)
        
                approve_url = url_for("main.approve_token", token=approval_token, _external=True)
                discard_url = url_for("main.discard_token", token=approval_token, _external=True)
                login_url = url_for("main.login_token", token=login_token, _external=True)
        
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
    token_entry = get_auth_token_by_login(token)

    if not token_entry:
        flash("Invalid token.", "danger")
        return redirect(url_for("main.auth"))

    if token_entry.login_used:
        flash("This token has already been used.", "danger")
        return redirect(url_for("main.auth"))

    if datetime.utcnow() > token_entry.created_at + timedelta(minutes=1440):
        flash("This token has expired.", "danger")
        return redirect(url_for("main.auth"))

    user = User.query.filter_by(email=token_entry.user_email).first()
    if not user or not user.approved:
        flash("User not approved or does not exist.", "danger")
        return redirect(url_for("main.auth"))

    session["email"] = user.email
    mark_login_token_used(token)

    flash("Logged in successfully!", "success")
    return redirect(url_for("main.landing"))



# -------------------------
# Admin Approve / Discard
# -------------------------

@main.route("/approve/<token>")
def approve_token(token):
    auth_link = get_auth_token_by_approval(token)
    if not auth_link or auth_link.approval_used:
        return "Invalid or already used approval link."
    return render_template("approve_input.html", email=auth_link.user_email, token=token)


@main.route('/submit_approval', methods=['POST'])
def submit_approval():
    token = request.form.get('token')
    email = request.form.get('email')
    designation = request.form.get('designation')

    auth_token = get_auth_token_by_approval(token)
    if not auth_token or auth_token.approval_used:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for("main.auth"))

    mark_approval_token_used(token, approved=True)
    approve_user(email, designation)

    login_url = url_for("main.login_token", token=auth_token.login_token, _external=True)
    send_approval_status_mail(email, approved=True, login_url=login_url)

    flash("User approved. Login link sent to their email.", "success")
    return redirect(url_for("main.auth"))




@main.route("/discard/<token>")
def discard_token(token):
    auth_token = get_auth_token_by_approval(token)
    if not auth_token or auth_token.approval_used:
        return "Invalid or already used discard link."

    email = auth_token.user_email
    discard_user(email)
    mark_approval_token_used(token, approved=False)

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

    user = get_user_by_email(session["email"])
    if not user:
        session.clear()
        return redirect(url_for("main.auth"))

    chats = get_all_chats()
    for chat in chats:
        if chat.timestamp:
            chat.timestamp += timedelta(hours=5, minutes=30)

    pending_requests = get_pending_users() if user.email == "utsavamistry30@gmail.com" else []

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
        chat = insert_chat(message, file_data, sender_id=user.email)
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

@main.route("/admin_approve_discard", methods=["POST"])
def admin_approve_discard():
    if "email" not in session or session["email"] != ADMIN_EMAIL:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("main.landing"))

    email = request.form.get("email")
    action = request.form.get("action")

    if not email or action not in ["approve", "discard"]:
        flash("Invalid request.", "danger")
        return redirect(url_for("main.landing"))

    user = get_user_by_email(email)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("main.landing"))

    if action == "approve":
        approve_user(email, designation="Emoployee")
        auth_token = AuthToken.query.filter_by(user_email=email).first()
        if auth_token:
            mark_approval_token_used(auth_token.approval_token, approved=True)
            login_url = url_for("main.login_token", token=auth_token.login_token, _external=True)
            send_approval_status_mail(email, approved=True, login_url=login_url)
        flash(f"Approved: {email}", "success")
    elif action == "discard":
        discard_user(email)
        auth_token = get_auth_token_by_email(email)
        if auth_token:
            mark_approval_token_used(auth_token.approval_token, approved=False)
        send_approval_status_mail(email, approved=False)
        flash(f"Discarded: {email}", "warning")

    return redirect(url_for("main.landing"))
