# Vaultify Employee Page

**Private Internal Software – Not for Public Distribution**

Vaultify Employee Page is a secure internal portal built exclusively for verified Vaultify employees. It enables staff communication, user management, and controlled access through a unified interface.

## Features

- **Secure Login & Registration**
  - Unified auth page (`auth.html`)
  - Admin approval required for all new registrations
  - One-time approval links sent via email with **token-based authorization**

- **Token-Based Authorization**
  - One-time-use tokens sent to both admin and requester via email
  - Tokens validated via GET requests
  - Auto-expire after first use or 24 hours
  - Prevents replay attacks and unauthorized access

- **Chat System ("Channel")**
  - Logged-in employees can send/receive messages
  - Supports file attachments up to 100MB

- **Profile Management**
  - Users can view their own name, email, and basic info

- **Admin Approval Panel**
  - Superusers can approve or reject new registration requests
  - Tokenized links expire after single use

- **Tabbed Landing Page**
  - Single-page interface using Bootstrap:
    - Channel
    - Profile
    - Approval Page (only for superusers)

## Tech Stack

- **Backend:** Flask (App Factory Pattern)
- **Database:** Supabase PostgreSQL (SQLAlchemy)
- **Email:** Brevo SMTP (Flask-Mail)
- **Frontend:** Bootstrap 5
- **Auth:** Custom token-based approval & login system

## Token Authorization Workflow

1. **Registration Request**
   - New user enters name and email on the unified auth page.
   - Token-based approval links are emailed to the admin.

2. **Admin Approval**
   - Admin clicks approve/reject link with a one-time token.
   - Token is validated and invalidated upon use.
   - User is marked as approved or rejected.

3. **User Access**
   - Upon approval, user receives a one-time token link for login.
   - The token is invalidated immediately after use.

## Legal

This software is proprietary and intended solely for internal use by Vaultify employees.  
**Do not distribute, copy, or reuse without explicit written consent.**

---

Internal Contact: `utsavamistry30@gmail.com`
