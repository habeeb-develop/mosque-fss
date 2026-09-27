from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g
)

import sqlite3
import os
import json
import hashlib
import hmac
import secrets
import smtplib

from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from dotenv import load_dotenv


# ================================================================
# ENVIRONMENT
# ================================================================

load_dotenv()


# ================================================================
# APPLICATION CONFIGURATION
# ================================================================

app = Flask(__name__)

# IMPORTANT:
# On Render, create a SECRET_KEY environment variable.
# Keep the same value permanently.
SECRET_KEY = os.environ.get("SECRET_KEY", "FsssmcCentralMosque_2026!Secure").strip()

if not SECRET_KEY:
    # A random fallback keeps local development usable.
    # On Render, ALWAYS set SECRET_KEY in Environment Variables.
    SECRET_KEY = secrets.token_hex(32)

app.secret_key = SECRET_KEY

# Session configuration
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Render uses HTTPS.
# Local development remains HTTP.
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("RENDER", "").lower() == "true"
)

app.config["SESSION_COOKIE_NAME"] = "fsssmc_session"
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_DOMAIN"] = None

# Flask may sit behind Render's HTTPS reverse proxy.
app.config["PREFERRED_URL_SCHEME"] = "https"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE = os.path.join(
    DATABASE_DIR,
    "fss.db"
)

os.makedirs(
    DATABASE_DIR,
    exist_ok=True
)

print("DATABASE LOCATION:", DATABASE)


# ================================================================
# PAYSTACK
# ================================================================

PAYSTACK_SECRET_KEY = os.environ.get(
    "PAYSTACK_SECRET_KEY",
    "sk_test_0d971bb72ebed6d23d0471924df87bd5941db555"
).strip()

PAYSTACK_PUBLIC_KEY = os.environ.get(
    "PAYSTACK_PUBLIC_KEY",
    "pk_test_3a23b0594bd9ee4878b78d7d090f4d4a12a62721"
).strip()

PAYSTACK_BASE_URL = os.environ.get(
    "PAYSTACK_BASE_URL",
    "https://api.paystack.co"
).strip()

PAYSTACK_CURRENCY = "NGN"


# ================================================================
# MAILBOXLAYER
# ================================================================

MAILBOXLAYER_ACCESS_KEY = os.environ.get(
    "MAILBOXLAYER_ACCESS_KEY",
    "edb349802dd334a9479417e4b16e060a"
).strip()

MAILBOXLAYER_URL = (
    "http://apilayer.net/api/check"
)


# ================================================================
# SMTP
# ================================================================

SMTP_HOST = os.environ.get(
    "SMTP_HOST",
    "smtp.gmail.com"
).strip()

SMTP_PORT = int(
    os.environ.get(
        "SMTP_PORT",
        "587"
    )
)

SMTP_USERNAME = os.environ.get(
    "SMTP_USERNAME",
    "ojugbelehabeeb06@gmail.com"
).strip()

SMTP_PASSWORD = os.environ.get(
    "SMTP_PASSWORD",
    "clwyraarljdpvgvj"
).strip()

SMTP_FROM = os.environ.get(
    "SMTP_FROM",
    "ojugbelehabeeb06@gmail.com"
).strip() or SMTP_USERNAME

OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6
OTP_RESEND_SECONDS = 60


# ================================================================
# SITE DATA
# ================================================================

DONATION_PURPOSES = [
    "General Mosque Support",
    "Building & Maintenance",
    "Education",
    "Community Service",
    "Zakat",
    "Sadaqah",
    "Other"
]


EXECUTIVE_MEMBERS = [
    {
        "name": "Amir Muritala Adekunle Balogun",
        "role": "Amir"
    },
    {
        "name": "Imam Mustapha Motilola Alli",
        "role": "Imam"
    },
    {
        "name": "Ishaq Aderemi Abimbola",
        "role": "Secretary"
    },
    {
        "name": "Abdul Ganiyu Olayinka Dabiri",
        "role": "Executive Member"
    },
    {
        "name": "Lukman Badiru",
        "role": "Executive Member"
    },
    {
        "name": "Lateef Usman",
        "role": "Executive Member"
    },
    {
        "name": "Prof. Zaid Aderolu",
        "role": "Executive Member"
    },
    {
        "name": "Lasisi Abayomi Lawal",
        "role": "Executive Member"
    },
    {
        "name": "Hassan Muhammad Bello",
        "role": "Executive Member"
    },
    {
        "name": "Engr. Ismail Sanni",
        "role": "Executive Member"
    },
    {
        "name": "Monsuru Oladehide",
        "role": "Executive Member"
    }
]


PAST_EXECUTIVE = [
    {
        "name": "Previous Executive",
        "role": "Past Executive Member"
    }
]


COMMITTEES = [
    {
        "name": "Education Committee",
        "description": (
            "Coordinates Islamic learning, lectures, "
            "classes and educational programmes."
        )
    },
    {
        "name": "Welfare Committee",
        "description": (
            "Supports members and community welfare initiatives."
        )
    },
    {
        "name": "Finance Committee",
        "description": (
            "Supports responsible financial administration "
            "and accountability."
        )
    },
    {
        "name": "Maintenance Committee",
        "description": (
            "Coordinates mosque facilities and maintenance."
        )
    },
    {
        "name": "Youth Committee",
        "description": (
            "Coordinates activities and programmes for young members."
        )
    }
]


JUMMAH_IMAMS = [
    {
        "name": "Ustadh Abdul Granny Adebayo Ejalonibu",
        "role": "Jummah Imam / Khatib"
    }
]


FACILITIES = [
    "Main Prayer Hall",
    "Women's Prayer Area",
    "Islamic Library",
    "Ablution Facilities",
    "Classrooms",
    "Meeting Halls"
]


# ================================================================
# DATABASE HELPERS
# ================================================================

def get_db():

    if "db" not in g:

        g.db = sqlite3.connect(
            DATABASE,
            timeout=30
        )

        g.db.row_factory = sqlite3.Row

        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

        g.db.execute(
            "PRAGMA busy_timeout = 30000"
        )

    return g.db


@app.teardown_appcontext
def close_db(exception=None):

    db = g.pop(
        "db",
        None
    )

    if db is not None:
        db.close()


def column_exists(
    table_name,
    column_name
):

    db = get_db()

    columns = db.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        column["name"] == column_name
        for column in columns
    )


def add_column_if_missing(
    table_name,
    column_name,
    definition
):

    db = get_db()

    if not column_exists(
        table_name,
        column_name
    ):

        db.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )

        db.commit()


def init_db():

    db = get_db()

    # ------------------------------------------------------------
    # ADMINS
    # ------------------------------------------------------------

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # ------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    add_column_if_missing(
        "users",
        "email_verified",
        "INTEGER DEFAULT 0"
    )

    # ------------------------------------------------------------
    # MEMBERS
    # ------------------------------------------------------------

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            post TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # ------------------------------------------------------------
    # DONATIONS
    # ------------------------------------------------------------

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_name TEXT NOT NULL,
            phone TEXT,
            email TEXT NOT NULL,
            amount REAL NOT NULL,
            purpose TEXT NOT NULL,
            payment_reference TEXT UNIQUE NOT NULL,
            payment_method TEXT DEFAULT 'paystack',
            payment_status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TEXT NOT NULL,
            paid_at TEXT
        )
        """
    )

    # ------------------------------------------------------------
    # ANNOUNCEMENTS
    # ------------------------------------------------------------

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            published INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # ------------------------------------------------------------
    # SAFE MIGRATIONS FOR OLDER DATABASES
    # ------------------------------------------------------------

    # Older copies of the project may have created these tables before
    # some fields were added. SQLite lets us add nullable columns without
    # destroying existing records.
    migrations = [
        ("members", "email", "TEXT"),
        ("members", "notes", "TEXT"),
        ("members", "created_at", "TEXT"),
        ("members", "updated_at", "TEXT"),

        ("donations", "phone", "TEXT"),
        ("donations", "email", "TEXT"),
        ("donations", "amount", "REAL"),
        ("donations", "purpose", "TEXT"),
        ("donations", "payment_reference", "TEXT"),
        ("donations", "payment_method", "TEXT DEFAULT 'paystack'"),
        ("donations", "payment_status", "TEXT DEFAULT 'pending'"),
        ("donations", "notes", "TEXT"),
        ("donations", "created_at", "TEXT"),
        ("donations", "paid_at", "TEXT"),

        ("announcements", "published", "INTEGER DEFAULT 1"),
        ("announcements", "created_at", "TEXT"),
        ("announcements", "updated_at", "TEXT"),
    ]

    for table_name, column_name, definition in migrations:
        try:
            add_column_if_missing(
                table_name,
                column_name,
                definition
            )
        except sqlite3.OperationalError as error:
            app.logger.warning(
                "Could not migrate %s.%s: %s",
                table_name,
                column_name,
                error
            )

    # ------------------------------------------------------------
    # INDEXES
    # ------------------------------------------------------------

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_members_phone
        ON members(phone)
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_members_post
        ON members(post)
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_donations_status
        ON donations(payment_status)
        """
    )

    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_donations_created
        ON donations(created_at)
        """
    )

    # ------------------------------------------------------------
    # DEFAULT ADMIN
    # ------------------------------------------------------------

    admin_email = os.environ.get(
        "ADMIN_EMAIL",
        "admin@fsssmc.org"
    ).strip().lower()

    admin_password = os.environ.get(
        "ADMIN_PASSWORD",
        "ChangeThisPassword123!"
    )

    existing_admin = db.execute(
        """
        SELECT id
        FROM admins
        WHERE email = ?
        """,
        (admin_email,)
    ).fetchone()

    if not existing_admin:

        db.execute(
            """
            INSERT INTO admins (
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                admin_email,
                generate_password_hash(
                    admin_password
                ),
                datetime.utcnow().isoformat()
            )
        )

    else:
        # Keep the administrator password synchronized with the Render
        # ADMIN_PASSWORD environment variable. This also fixes the common
        # case where the database was created with an older default password.
        existing_admin_row = db.execute(
            """
            SELECT password_hash
            FROM admins
            WHERE email = ?
            """,
            (admin_email,)
        ).fetchone()

        try:
            password_matches = check_password_hash(
                existing_admin_row["password_hash"],
                admin_password
            )
        except Exception:
            password_matches = False

        if not password_matches:
            db.execute(
                """
                UPDATE admins
                SET password_hash = ?
                WHERE email = ?
                """,
                (
                    generate_password_hash(admin_password),
                    admin_email
                )
            )

    db.commit()


# ================================================================
# AUTHENTICATION HELPERS
# ================================================================

def account_authenticated():

    return bool(
        session.get("user_id")
    )


def admin_authenticated():

    return bool(
        session.get("admin_id")
    )


def admin_required(function):

    @wraps(function)
    def decorated(*args, **kwargs):

        if not admin_authenticated():

            return redirect(
                url_for("admin_login")
            )

        return function(
            *args,
            **kwargs
        )

    return decorated


# ================================================================
# TEMPLATE GLOBALS
# ================================================================

@app.context_processor
def inject_globals():

    return {
        "site_name": "FSSSMC Central Mosque",
        "paystack_public_key": PAYSTACK_PUBLIC_KEY,
        "current_year": datetime.now().year,
        "logged_in": account_authenticated(),
        "current_user_name": session.get(
            "user_name"
        ),
        "current_user_surname": session.get(
            "user_surname"
        ),
        "current_user_email": session.get(
            "user_email"
        )
    }


# ================================================================
# SAFE TEMPLATE RENDERING
# ================================================================

def safe_render(template_name, **context):
    """
    Render a normal template. If a deployment accidentally missed a
    template, return a useful HTML response instead of causing a second
    TemplateNotFound exception inside the 500 handler.
    """
    try:
        return render_template(template_name, **context)
    except Exception as error:
        from jinja2 import TemplateNotFound

        if isinstance(error, TemplateNotFound):
            app.logger.error(
                "MISSING TEMPLATE: %s. "
                "Make sure the templates folder is committed and pushed.",
                template_name
            )
            return (
                f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FSSSMC Central Mosque</title>
<style>
body{{font-family:Arial,sans-serif;background:#f7f8f7;margin:0;padding:40px;color:#17352d}}
.box{{max-width:720px;margin:40px auto;background:white;padding:32px;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.08)}}
h1{{color:#006b57}}code{{background:#eef3f1;padding:3px 7px;border-radius:5px}}
</style>
</head>
<body>
<div class="box">
<h1>FSSSMC Central Mosque</h1>
<p>This page could not be loaded because the template
<code>{template_name}</code> is missing from the deployed project.</p>
<p>Commit and push your complete <code>templates</code> folder to GitHub,
then let Render deploy the new commit.</p>
</div>
</body>
</html>""",
                500
            )
        raise


# ================================================================
# LOGIN GATE
# ================================================================

@app.before_request
def require_login():

    allowed_endpoints = {
        "login",
        "open_registration",
        "register",
        "verify_otp",
        "resend_otp",
        "logout",
        "static",
        "paystack_webhook",
        "paystack_callback",
        "admin_login",
        "page_not_found",
        "internal_error"
    }

    endpoint = request.endpoint

    if endpoint in allowed_endpoints:
        return None

    if endpoint is None:
        return None

    # Admin routes have their own protection.
    if endpoint.startswith("admin_"):
        return None

    # Already logged in.
    if account_authenticated():
        return None

    # Everyone else must log in.
    return redirect(
        url_for(
            "login",
            next=request.path
        )
    )


# ================================================================
# EMAIL VALIDATION
# ================================================================

def basic_email_valid(email):

    email = email.strip().lower()

    if not email:
        return False

    if "@" not in email:
        return False

    if email.count("@") != 1:
        return False

    local, domain = email.split("@")

    if not local or not domain:
        return False

    if "." not in domain:
        return False

    if domain.startswith("."):
        return False

    if domain.endswith("."):
        return False

    return True


def validate_email_with_mailboxlayer(email):

    email = email.strip().lower()

    if not basic_email_valid(email):
        return False

    if not MAILBOXLAYER_ACCESS_KEY:
        return True

    try:

        params = urlencode({
            "access_key": MAILBOXLAYER_ACCESS_KEY,
            "email": email,
            "format": 1
        })

        url = (
            f"{MAILBOXLAYER_URL}?{params}"
        )

        req = Request(
            url,
            headers={
                "User-Agent":
                    "FSSSMC-Membership-System"
            }
        )

        with urlopen(
            req,
            timeout=10
        ) as response:

            raw = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        data = json.loads(raw)

        if data.get("success") is False:
            return True

        if data.get(
            "disposable",
            False
        ) is True:
            return False

        return True

    except Exception as error:

        print(
            "MAILBOXLAYER ERROR:",
            error
        )

        # Fail open if Mailboxlayer itself fails.
        return True


# ================================================================
# OTP
# ================================================================

def generate_otp():

    return "".join(
        secrets.choice(
            "0123456789"
        )
        for _ in range(OTP_LENGTH)
    )


def hash_otp(otp):

    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def clear_otp_session():

    session.pop(
        "otp_hash",
        None
    )

    session.pop(
        "otp_email",
        None
    )

    session.pop(
        "otp_purpose",
        None
    )

    session.pop(
        "otp_expires",
        None
    )

    session.pop(
        "otp_last_sent",
        None
    )


def send_otp_email(
    email,
    otp,
    purpose
):

    if not SMTP_USERNAME or not SMTP_PASSWORD:

        print(
            "SMTP_USERNAME or SMTP_PASSWORD "
            "is missing."
        )

        return False

    if purpose == "registration":

        subject = (
            "FSSSMC Central Mosque - "
            "Verify Your Account"
        )

        message = (
            "Assalamu Alaikum,\n\n"
            "Thank you for creating an account "
            "with FSSSMC Central Mosque.\n\n"
            f"Your verification code is: {otp}\n\n"
            f"This code expires in "
            f"{OTP_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not request this code, "
            "please ignore this email.\n\n"
            "FSSSMC Central Mosque"
        )

    else:

        subject = (
            "FSSSMC Central Mosque - "
            "Login Verification Code"
        )

        message = (
            "Assalamu Alaikum,\n\n"
            "Your login verification code is:\n\n"
            f"{otp}\n\n"
            f"This code expires in "
            f"{OTP_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not request this login, "
            "please ignore this email.\n\n"
            "FSSSMC Central Mosque"
        )

    msg = EmailMessage()

    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = email

    msg.set_content(
        message
    )

    try:

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30
        ) as server:

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            server.send_message(
                msg
            )

        return True

    except Exception as error:

        print(
            "SMTP ERROR:",
            error
        )

        return False


def create_and_send_otp(
    email,
    purpose
):

    otp = generate_otp()

    now = datetime.utcnow()

    expires = (
        now
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )
    )

    session["otp_hash"] = hash_otp(
        otp
    )

    session["otp_email"] = email

    session["otp_purpose"] = purpose

    session["otp_expires"] = (
        expires.timestamp()
    )

    session["otp_last_sent"] = (
        now.timestamp()
    )

    sent = send_otp_email(
        email,
        otp,
        purpose
    )

    if not sent:
        clear_otp_session()

    return sent


# ================================================================
# LOGIN
# ================================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if account_authenticated():

        return redirect(
            url_for("profile")
        )

    if admin_authenticated():

        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "GET":

        return safe_render(
            "login.html"
        )

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not email or not password:

        flash(
            "Please enter your email and password.",
            "error"
        )

        return safe_render(
            "login.html"
        )

    db = get_db()

    # ------------------------------------------------------------
    # ADMIN LOGIN
    # ------------------------------------------------------------

    admin = db.execute(
        """
        SELECT *
        FROM admins
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if admin:

        if check_password_hash(
            admin["password_hash"],
            password
        ):

            session.clear()

            session["admin_id"] = admin["id"]

            session["admin_email"] = (
                admin["email"]
            )

            flash(
                "Admin login successful.",
                "success"
            )

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

        return safe_render(
            "login.html"
        )

    # ------------------------------------------------------------
    # USER LOGIN
    # ------------------------------------------------------------

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if not user:

        flash(
            "Invalid email or password.",
            "error"
        )

        return safe_render(
            "login.html"
        )

    if not check_password_hash(
        user["password_hash"],
        password
    ):

        flash(
            "Invalid email or password.",
            "error"
        )

        return safe_render(
            "login.html"
        )

    # Existing verified accounts can log in directly. This prevents a
    # correct password from being blocked by a temporary SMTP problem.
    if int(user["email_verified"] or 0) == 1:
        session.clear()
        session["user_id"] = int(user["id"])
        session["user_name"] = str(user["name"])
        session["user_surname"] = str(user["surname"])
        session["user_email"] = str(user["email"])
        session.modified = True

        flash(
            f"Login successful. Welcome back, {user['name']}.",
            "success"
        )

        return redirect(url_for("profile"))

    session["pending_login"] = {
        "user_id": user["id"],
        "name": user["name"],
        "surname": user["surname"],
        "email": user["email"]
    }

    sent = create_and_send_otp(
        user["email"],
        "login"
    )

    if not sent:
        session.pop("pending_login", None)
        flash(
            "Your account is not verified yet, and the verification "
            "email could not be sent. Check SMTP_USERNAME and "
            "SMTP_PASSWORD in Render.",
            "error"
        )
        return safe_render("login.html")

    flash(
        "A verification code has been sent to your email.",
        "success"
    )

    return redirect(url_for("verify_otp"))


# ================================================================
# CREATE ACCOUNT ENTRY POINT
# ================================================================

@app.route(
    "/create-account"
)
def open_registration():

    # This route is linked from login.html.
    # It allows registration to be opened without
    # opening /register directly to everybody.

    session["allow_registration"] = True

    return redirect(
        url_for("register")
    )


# ================================================================
# REGISTER
# ================================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if account_authenticated():

        return redirect(
            url_for("profile")
        )

    # ------------------------------------------------------------
    # GET REGISTRATION PAGE
    # ------------------------------------------------------------

    if request.method == "GET":

        if not session.get(
            "allow_registration"
        ):

            return redirect(
                url_for("login")
            )

        session.pop(
            "allow_registration",
            None
        )

        return safe_render(
            "register.html"
        )

    # ------------------------------------------------------------
    # POST REGISTRATION
    # ------------------------------------------------------------

    name = request.form.get(
        "name",
        ""
    ).strip()

    surname = request.form.get(
        "surname",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    if not all([
        name,
        surname,
        email,
        password,
        confirm_password
    ]):

        flash(
            "Please fill in all fields.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    if not basic_email_valid(
        email
    ):

        flash(
            "Please enter a valid email address.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    if len(password) < 6:

        flash(
            "Password must be at least 6 characters.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    if not validate_email_with_mailboxlayer(
        email
    ):

        flash(
            "Please use a valid email address.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    db = get_db()

    existing_user = db.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if existing_user:

        flash(
            "An account with this email already exists. "
            "Please log in instead.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------------
    # STORE REGISTRATION TEMPORARILY
    # ------------------------------------------------------------

    session["pending_registration"] = {
        "name": name,
        "surname": surname,
        "email": email,
        "password_hash": generate_password_hash(
            password
        )
    }

    sent = create_and_send_otp(
        email,
        "registration"
    )

    if not sent:

        session.pop(
            "pending_registration",
            None
        )

        flash(
            "We could not send the verification code. "
            "Please try again.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    flash(
        "A verification code has been sent to your email.",
        "success"
    )

    return redirect(
        url_for("verify_otp")
    )


# ================================================================
# VERIFY OTP
# ================================================================

@app.route(
    "/verify",
    methods=["GET", "POST"]
)
@app.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    otp_email = session.get(
        "otp_email"
    )

    otp_hash = session.get(
        "otp_hash"
    )

    otp_purpose = session.get(
        "otp_purpose"
    )

    otp_expires = session.get(
        "otp_expires"
    )

    if not otp_email or not otp_hash or not otp_purpose:

        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------------
    # CHECK EXPIRATION
    # ------------------------------------------------------------

    if otp_expires:

        try:

            if (
                datetime.utcnow().timestamp()
                > float(otp_expires)
            ):

                clear_otp_session()

                session.pop(
                    "pending_login",
                    None
                )

                session.pop(
                    "pending_registration",
                    None
                )

                flash(
                    "Your verification code has expired.",
                    "error"
                )

                return redirect(
                    url_for("login")
                )

        except (
            ValueError,
            TypeError
        ):

            clear_otp_session()

            return redirect(
                url_for("login")
            )

    # ------------------------------------------------------------
    # SHOW OTP PAGE
    # ------------------------------------------------------------

    if request.method == "GET":

        return safe_render(
            "verify.html",
            email=otp_email,
            purpose=otp_purpose
        )

    # ------------------------------------------------------------
    # RECEIVE OTP
    # ------------------------------------------------------------

    otp = request.form.get(
        "otp",
        ""
    ).strip()

    if (
        len(otp) != OTP_LENGTH
        or not otp.isdigit()
    ):

        flash(
            "Please enter the 6-digit verification code.",
            "error"
        )

        return safe_render(
            "verify.html",
            email=otp_email,
            purpose=otp_purpose
        )

    if not hmac.compare_digest(
        hash_otp(otp),
        otp_hash
    ):

        flash(
            "Incorrect verification code.",
            "error"
        )

        return safe_render(
            "verify.html",
            email=otp_email,
            purpose=otp_purpose
        )

    db = get_db()

    # ============================================================
    # REGISTRATION VERIFICATION
    # ============================================================

    if otp_purpose == "registration":

        pending_registration = session.get(
            "pending_registration"
        )

        if not pending_registration:

            clear_otp_session()

            flash(
                "Registration session expired. "
                "Please create your account again.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        data = dict(
            pending_registration
        )

        existing_user = db.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (data["email"],)
        ).fetchone()

        if existing_user:

            clear_otp_session()

            session.pop(
                "pending_registration",
                None
            )

            flash(
                "An account with this email already exists.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        # --------------------------------------------------------
        # CREATE ACCOUNT
        # --------------------------------------------------------

        cursor = db.execute(
            """
            INSERT INTO users (
                name,
                surname,
                email,
                password_hash,
                created_at,
                email_verified
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["surname"],
                data["email"],
                data["password_hash"],
                datetime.utcnow().isoformat(),
                1
            )
        )

        db.commit()

        user_id = cursor.lastrowid

        # --------------------------------------------------------
        # VERY IMPORTANT
        #
        # DO NOT REDIRECT TO LOGIN HERE.
        #
        # The new account is immediately authenticated.
        # --------------------------------------------------------

        session.clear()

        session["user_id"] = int(
            user_id
        )

        session["user_name"] = str(
            data["name"]
        )

        session["user_surname"] = str(
            data["surname"]
        )

        session["user_email"] = str(
            data["email"]
        )

        # Explicitly mark the session as modified.
        session.modified = True

        flash(
            f"Account created successfully. "
            f"Welcome, {data['name']}.",
            "success"
        )

        # DIRECTLY ENTER THE WEBSITE
        return redirect(
            url_for("profile")
        )

    # ============================================================
    # LOGIN VERIFICATION
    # ============================================================

    if otp_purpose == "login":

        pending_login = session.get(
            "pending_login"
        )

        if not pending_login:

            clear_otp_session()

            flash(
                "Login session expired. "
                "Please log in again.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (
                pending_login["user_id"],
            )
        ).fetchone()

        if not user:

            clear_otp_session()

            session.pop(
                "pending_login",
                None
            )

            flash(
                "User account could not be found.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        db.execute(
            """
            UPDATE users
            SET email_verified = 1
            WHERE id = ?
            """,
            (
                user["id"],
            )
        )

        db.commit()

        session.clear()

        session["user_id"] = int(
            user["id"]
        )

        session["user_name"] = str(
            user["name"]
        )

        session["user_surname"] = str(
            user["surname"]
        )

        session["user_email"] = str(
            user["email"]
        )

        session.modified = True

        flash(
            f"Login successful. "
            f"Welcome back, {user['name']}.",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    clear_otp_session()

    return redirect(
        url_for("login")
    )


# ================================================================
# RESEND OTP
# ================================================================

@app.route(
    "/resend-otp",
    methods=["GET", "POST"]
)
def resend_otp():

    email = session.get(
        "otp_email"
    )

    purpose = session.get(
        "otp_purpose"
    )

    if not email or not purpose:

        flash(
            "There is no active verification request.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    last_sent = session.get(
        "otp_last_sent"
    )

    if last_sent:

        try:

            elapsed = (
                datetime.utcnow().timestamp()
                - float(last_sent)
            )

            if elapsed < OTP_RESEND_SECONDS:

                remaining = int(
                    OTP_RESEND_SECONDS
                    - elapsed
                )

                flash(
                    f"Please wait {remaining} seconds "
                    "before requesting another code.",
                    "error"
                )

                return redirect(
                    url_for("verify_otp")
                )

        except Exception:
            pass

    clear_otp_session()

    sent = create_and_send_otp(
        email,
        purpose
    )

    if not sent:

        flash(
            "We could not send a new verification code.",
            "error"
        )

        return redirect(
            url_for("verify_otp")
        )

    flash(
        "A new verification code has been sent.",
        "success"
    )

    return redirect(
        url_for("verify_otp")
    )


# ================================================================
# LOGOUT
# ================================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ================================================================
# PROFILE
# ================================================================

@app.route("/profile")
def profile():

    if not account_authenticated():

        return redirect(
            url_for("login")
        )

    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    if not user:

        session.clear()

        flash(
            "Your account could not be found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    return safe_render(
        "profile.html",
        user=user
    )


# ================================================================
# HOME
# ================================================================

@app.route("/")
def home():

    return safe_render(
        "index.html"
    )


# ================================================================
# ABOUT
# ================================================================

@app.route("/about")
def about():

    return safe_render(
        "about.html",
        executive_members=EXECUTIVE_MEMBERS,
        facilities=FACILITIES
    )


# ================================================================
# PRAYER
# ================================================================

@app.route("/prayer")
def prayer():

    prayer_times = {
        "Fajr": "04:58",
        "Sunrise": "06:20",
        "Dhuhr": "12:13",
        "Asr": "15:49",
        "Maghrib": "17:52",
        "Isha": "19:11"
    }

    return safe_render(
        "prayer.html",
        prayer_times=prayer_times
    )


# ================================================================
# SERVICES
# ================================================================

@app.route("/services")
def services():

    return safe_render(
        "services.html",
        facilities=FACILITIES
    )


# ================================================================
# EVENTS
# ================================================================

@app.route("/events")
def events():

    return safe_render(
        "events.html"
    )


# ================================================================
# LEARN
# ================================================================

@app.route("/learn")
def learn():

    return safe_render(
        "learn.html"
    )


# ================================================================
# GET INVOLVED
# ================================================================

@app.route("/get-involved")
def get_involved():

    return safe_render(
        "get-involved.html"
    )


# ================================================================
# CONTACT
# ================================================================

@app.route("/contact")
def contact():

    return safe_render(
        "contact.html",
        executive_members=EXECUTIVE_MEMBERS,
        past_executive=PAST_EXECUTIVE,
        committees=COMMITTEES,
        jummah_imams=JUMMAH_IMAMS
    )


# ================================================================
# ANNOUNCEMENTS
# ================================================================

@app.route("/announcements")
def announcements():

    db = get_db()

    rows = db.execute(
        """
        SELECT *
        FROM announcements
        WHERE published = 1
        ORDER BY created_at DESC
        """
    ).fetchall()

    return safe_render(
        "announcements.html",
        announcements=rows
    )


# ================================================================
# MEMBER REGISTRATION
# ================================================================

@app.route(
    "/members/register",
    methods=["GET", "POST"]
)
def member_register():

    if request.method == "GET":

        return safe_render(
            "member_register.html"
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    surname = request.form.get(
        "surname",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    address = request.form.get(
        "address",
        ""
    ).strip()

    post = request.form.get(
        "post",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if not all([
        name,
        surname,
        phone,
        email,
        address,
        post
    ]):

        flash(
            "Please fill in all required fields.",
            "error"
        )

        return redirect(
            url_for("member_register")
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM members
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if existing:

        flash(
            "A member with this email already exists.",
            "error"
        )

        return redirect(
            url_for("member_register")
        )

    now = datetime.utcnow().isoformat()

    try:
        db.execute(
            """
            INSERT INTO members (
                name,
                surname,
                phone,
                email,
                address,
                post,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                surname,
                phone,
                email,
                address,
                post,
                notes,
                now,
                now
            )
        )
        db.commit()

    except sqlite3.IntegrityError as error:
        db.rollback()
        app.logger.exception(
            "MEMBER REGISTRATION DATABASE ERROR: %s",
            error
        )
        flash(
            "This member could not be registered because the database "
            "rejected the information. Check the server log for details.",
            "error"
        )
        return redirect(url_for("member_register"))

    flash(
        "Membership registration submitted successfully.",
        "success"
    )

    return redirect(url_for("profile"))


# ================================================================
# PAYSTACK HELPERS
# ================================================================

def generate_payment_reference():

    return (
        "FSSSMC-"
        + datetime.utcnow().strftime(
            "%Y%m%d%H%M%S"
        )
        + "-"
        + secrets.token_hex(
            5
        ).upper()
    )


def naira_to_kobo(amount):

    try:

        value = Decimal(
            str(amount)
        )

        if value <= 0:
            return None

        return int(
            value * Decimal("100")
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError
    ):

        return None


def paystack_request(
    endpoint,
    method="GET",
    payload=None
):

    if not PAYSTACK_SECRET_KEY:

        return (
            None,
            "Paystack is not configured. Add PAYSTACK_SECRET_KEY "
            "to the Render Environment Variables."
        )

    url = (
        PAYSTACK_BASE_URL.rstrip("/")
        + "/"
        + endpoint.lstrip("/")
    )

    headers = {
        "Authorization":
            "Bearer " + PAYSTACK_SECRET_KEY,
        "Content-Type":
            "application/json",
        "Cache-Control":
            "no-cache"
    }

    data = None

    if payload is not None:

        data = json.dumps(
            payload
        ).encode("utf-8")

    req = Request(
        url,
        data=data,
        headers=headers,
        method=method
    )

    try:

        with urlopen(
            req,
            timeout=30
        ) as response:

            body = response.read().decode(
                "utf-8",
                errors="ignore"
            )

            parsed = json.loads(body)

            if not parsed.get("status", False):
                return (
                    None,
                    parsed.get(
                        "message",
                        "Paystack rejected the request."
                    )
                )

            return parsed, None

    except HTTPError as error:

        try:

            body = error.read().decode(
                "utf-8",
                errors="ignore"
            )

            parsed = json.loads(
                body
            )

            return (
                None,
                parsed.get(
                    "message",
                    "Paystack request failed."
                )
            )

        except Exception:

            return (
                None,
                f"Paystack HTTP error {error.code}."
            )

    except URLError as error:

        return (
            None,
            "Could not connect to Paystack."
        )

    except Exception as error:

        return (
            None,
            str(error)
        )


def initialize_paystack_transaction(
    email,
    amount_kobo,
    reference,
    callback_url,
    metadata=None
):

    payload = {
        "email": email,
        "amount": str(amount_kobo),
        "currency": "NGN",
        "reference": reference,
        "callback_url": callback_url
    }

    if metadata:
        payload["metadata"] = metadata

    return paystack_request(
        "/transaction/initialize",
        "POST",
        payload
    )


def verify_paystack_transaction(
    reference
):

    return paystack_request(
        f"/transaction/verify/{reference}",
        "GET"
    )


def mark_donation_as_paid(
    reference
):

    db = get_db()

    donation = db.execute(
        """
        SELECT *
        FROM donations
        WHERE payment_reference = ?
        """,
        (reference,)
    ).fetchone()

    if not donation:
        return False

    if donation["payment_status"] == "paid":
        return True

    db.execute(
        """
        UPDATE donations
        SET payment_status = ?,
            paid_at = ?
        WHERE payment_reference = ?
        """,
        (
            "paid",
            datetime.utcnow().isoformat(),
            reference
        )
    )

    db.commit()

    return True


# ================================================================
# PAYSTACK WEBHOOK
# ================================================================

@app.route(
    "/paystack/webhook",
    methods=["POST"]
)
def paystack_webhook():

    if not PAYSTACK_SECRET_KEY:
        return "", 200

    signature = request.headers.get(
        "X-Paystack-Signature",
        ""
    )

    payload = request.get_data()

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(
            "utf-8"
        ),
        payload,
        hashlib.sha512
    ).hexdigest()

    if not signature:
        return "", 401

    if not hmac.compare_digest(
        signature,
        expected
    ):
        return "", 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        if data.get(
            "event"
        ) == "charge.success":

            transaction = data.get(
                "data",
                {}
            )

            reference = transaction.get(
                "reference"
            )

            if reference:
                mark_donation_as_paid(
                    reference
                )

        return "", 200

    except Exception:

        return "", 200


# ================================================================
# DONATE
# ================================================================

@app.route(
    "/donate",
    methods=["GET", "POST"]
)
def donate():

    user_email = session.get(
        "user_email",
        ""
    )

    user_name = session.get(
        "user_name",
        ""
    )

    user_surname = session.get(
        "user_surname",
        ""
    )

    if request.method == "GET":

        return safe_render(
            "donate.html",
            donation_purposes=DONATION_PURPOSES,
            user_email=user_email,
            user_name=user_name,
            user_surname=user_surname
        )

    donor_name = request.form.get(
        "donor_name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    amount = request.form.get(
        "amount",
        ""
    ).strip()

    purpose = request.form.get(
        "purpose",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if not donor_name:

        donor_name = (
            f"{user_name} {user_surname}"
        ).strip()

    if not email:
        email = user_email

    if not donor_name or not email:

        flash(
            "Please provide your name and email.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    amount_kobo = naira_to_kobo(
        amount
    )

    if amount_kobo is None:

        flash(
            "Please enter a valid donation amount.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    if purpose not in DONATION_PURPOSES:

        flash(
            "Please select a valid donation purpose.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    reference = generate_payment_reference()

    db = get_db()

    try:
        db.execute(
            """
            INSERT INTO donations (
                donor_name,
                phone,
                email,
                amount,
                purpose,
                payment_reference,
                payment_method,
                payment_status,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                donor_name,
                phone,
                email,
                float(
                    Decimal(str(amount))
                ),
                purpose,
                reference,
                "paystack",
                "pending",
                notes,
                datetime.utcnow().isoformat()
            )
        )

        db.commit()

    except sqlite3.IntegrityError as error:
        db.rollback()
        app.logger.exception(
            "DONATION DATABASE ERROR: %s",
            error
        )
        flash(
            "The donation could not be saved. Please try again.",
            "error"
        )
        return redirect(url_for("donate"))

    callback_url = url_for(
        "paystack_callback",
        _external=True
    )

    metadata = {
        "donor_name": donor_name,
        "phone": phone,
        "purpose": purpose,
        "cancel_action": url_for(
            "donate",
            _external=True
        ),
        "custom_fields": [
            {
                "display_name":
                    "Donor Name",
                "variable_name":
                    "donor_name",
                "value":
                    donor_name
            },
            {
                "display_name":
                    "Purpose",
                "variable_name":
                    "purpose",
                "value":
                    purpose
            }
        ]
    }

    result, error = (
        initialize_paystack_transaction(
            email,
            amount_kobo,
            reference,
            callback_url,
            metadata
        )
    )

    if error or not result:

        db.execute(
            """
            UPDATE donations
            SET payment_status = ?
            WHERE payment_reference = ?
            """,
            (
                "failed",
                reference
            )
        )

        db.commit()

        flash(
            "Payment could not be initialized.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    authorization_url = (
        result
        .get("data", {})
        .get("authorization_url")
    )

    if not authorization_url:

        flash(
            "Paystack did not return a payment link.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    return redirect(
        authorization_url
    )


# ================================================================
# PAYSTACK CALLBACK
# ================================================================

@app.route(
    "/paystack/callback"
)
def paystack_callback():

    reference = request.args.get(
        "reference",
        ""
    ).strip()

    if not reference:

        flash(
            "No payment reference was provided.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    result, error = (
        verify_paystack_transaction(
            reference
        )
    )

    if error or not result:

        flash(
            "Unable to verify the payment.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    transaction = result.get(
        "data",
        {}
    )

    if (
        result.get("status")
        and transaction.get("status")
        == "success"
    ):

        mark_donation_as_paid(
            reference
        )

        flash(
            "Donation payment completed successfully. "
            "Thank you for your support.",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    flash(
        "The donation payment was not completed.",
        "error"
    )

    return redirect(
        url_for("donate")
    )


# ================================================================
# ADMIN LOGIN
# ================================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if admin_authenticated():

        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "GET":

        return safe_render(
            "admin_login.html"
        )

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    db = get_db()

    admin = db.execute(
        """
        SELECT *
        FROM admins
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if not admin or not check_password_hash(
        admin["password_hash"],
        password
    ):

        flash(
            "Invalid administrator credentials.",
            "error"
        )

        return safe_render(
            "admin_login.html"
        )

    session.clear()

    session["admin_id"] = admin["id"]
    session["admin_email"] = admin["email"]

    return redirect(
        url_for("admin_dashboard")
    )


# ================================================================
# ADMIN LOGOUT
# ================================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.clear()

    flash(
        "Administrator logged out.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


# ================================================================
# ADMIN DASHBOARD
# ================================================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    db = get_db()

    user_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        """
    ).fetchone()["count"]

    member_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM members
        """
    ).fetchone()["count"]

    donation_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM donations
        WHERE payment_status = 'paid'
        """
    ).fetchone()["count"]

    donation_total = db.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        ) AS total
        FROM donations
        WHERE payment_status = 'paid'
        """
    ).fetchone()["total"]

    announcement_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM announcements
        WHERE published = 1
        """
    ).fetchone()["count"]

    return safe_render(
        "admin.html",
        user_count=user_count,
        member_count=member_count,
        donation_count=donation_count,
        donation_total=donation_total,
        announcement_count=announcement_count
    )


# ================================================================
# ADMIN MEMBERS
# ================================================================

@app.route(
    "/admin/members"
)
@admin_required
def admin_members():

    db = get_db()

    members = db.execute(
        """
        SELECT *
        FROM members
        ORDER BY created_at DESC
        """
    ).fetchall()

    return safe_render(
        "admin_members.html",
        members=members
    )


@app.route(
    "/admin/members/add",
    methods=["GET", "POST"]
)
@admin_required
def admin_add_member():

    if request.method == "GET":

        return safe_render(
            "admin_member_form.html",
            member=None
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    surname = request.form.get(
        "surname",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    address = request.form.get(
        "address",
        ""
    ).strip()

    post = request.form.get(
        "post",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if not all([
        name,
        surname,
        phone,
        email,
        address,
        post
    ]):

        flash(
            "Please complete all required fields.",
            "error"
        )

        return safe_render(
            "admin_member_form.html",
            member=None
        )

    db = get_db()

    now = datetime.utcnow().isoformat()

    db.execute(
        """
        INSERT INTO members (
            name,
            surname,
            phone,
            email,
            address,
            post,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            surname,
            phone,
            email,
            address,
            post,
            notes,
            now,
            now
        )
    )

    db.commit()

    flash(
        "Member added successfully.",
        "success"
    )

    return redirect(
        url_for("admin_members")
    )


@app.route(
    "/admin/members/<int:member_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def admin_edit_member(
    member_id
):

    db = get_db()

    member = db.execute(
        """
        SELECT *
        FROM members
        WHERE id = ?
        """,
        (member_id,)
    ).fetchone()

    if not member:

        flash(
            "Member not found.",
            "error"
        )

        return redirect(
            url_for("admin_members")
        )

    if request.method == "GET":

        return safe_render(
            "admin_member_form.html",
            member=member
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    surname = request.form.get(
        "surname",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    address = request.form.get(
        "address",
        ""
    ).strip()

    post = request.form.get(
        "post",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    db.execute(
        """
        UPDATE members
        SET name = ?,
            surname = ?,
            phone = ?,
            email = ?,
            address = ?,
            post = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            name,
            surname,
            phone,
            email,
            address,
            post,
            notes,
            datetime.utcnow().isoformat(),
            member_id
        )
    )

    db.commit()

    flash(
        "Member updated successfully.",
        "success"
    )

    return redirect(
        url_for("admin_members")
    )


@app.route(
    "/admin/members/<int:member_id>/delete",
    methods=["GET", "POST"]
)
@admin_required
def admin_delete_member(
    member_id
):

    db = get_db()

    db.execute(
        """
        DELETE FROM members
        WHERE id = ?
        """,
        (member_id,)
    )

    db.commit()

    flash(
        "Member deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin_members")
    )


# ================================================================
# ADMIN DONATIONS
# ================================================================

@app.route(
    "/admin/donations"
)
@admin_required
def admin_donations():

    db = get_db()

    donations = db.execute(
        """
        SELECT *
        FROM donations
        ORDER BY created_at DESC
        """
    ).fetchall()

    return safe_render(
        "admin_donations.html",
        donations=donations
    )


@app.route(
    "/admin/donations/<int:donation_id>/status",
    methods=["POST"]
)
@admin_required
def admin_update_donation_status(
    donation_id
):

    status = request.form.get(
        "payment_status",
        ""
    ).strip().lower()

    if status not in {
        "pending",
        "paid",
        "failed",
        "cancelled"
    }:

        flash(
            "Invalid donation status.",
            "error"
        )

        return redirect(
            url_for("admin_donations")
        )

    paid_at = None

    if status == "paid":

        paid_at = datetime.utcnow().isoformat()

    db = get_db()

    db.execute(
        """
        UPDATE donations
        SET payment_status = ?,
            paid_at = ?
        WHERE id = ?
        """,
        (
            status,
            paid_at,
            donation_id
        )
    )

    db.commit()

    flash(
        "Donation updated successfully.",
        "success"
    )

    return redirect(
        url_for("admin_donations")
    )


@app.route(
    "/admin/donations/<int:donation_id>/delete",
    methods=["GET", "POST"]
)
@admin_required
def admin_delete_donation(
    donation_id
):

    db = get_db()

    db.execute(
        """
        DELETE FROM donations
        WHERE id = ?
        """,
        (donation_id,)
    )

    db.commit()

    flash(
        "Donation deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin_donations")
    )


# ================================================================
# ADMIN ANNOUNCEMENTS
# ================================================================

@app.route(
    "/admin/announcements",
    methods=["GET", "POST"]
)
@admin_required
def admin_announcements():

    db = get_db()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        body = request.form.get(
            "body",
            ""
        ).strip()

        published = (
            1
            if request.form.get(
                "published"
            )
            else 0
        )

        if not title or not body:

            flash(
                "Title and body are required.",
                "error"
            )

            return redirect(
                url_for("admin_announcements")
            )

        now = datetime.utcnow().isoformat()

        db.execute(
            """
            INSERT INTO announcements (
                title,
                body,
                published,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title,
                body,
                published,
                now,
                now
            )
        )

        db.commit()

        flash(
            "Announcement created successfully.",
            "success"
        )

        return redirect(
            url_for("admin_announcements")
        )

    announcements = db.execute(
        """
        SELECT *
        FROM announcements
        ORDER BY created_at DESC
        """
    ).fetchall()

    return safe_render(
        "admin_announcements.html",
        announcements=announcements
    )


@app.route(
    "/admin/announcements/<int:announcement_id>/delete",
    methods=["GET", "POST"]
)
@admin_required
def admin_delete_announcement(
    announcement_id
):

    db = get_db()

    db.execute(
        """
        DELETE FROM announcements
        WHERE id = ?
        """,
        (announcement_id,)
    )

    db.commit()

    flash(
        "Announcement deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin_announcements")
    )


# ================================================================
# ERROR HANDLERS
# ================================================================

@app.errorhandler(404)
def page_not_found(error):

    try:
        return safe_render("404.html"), 404
    except Exception:
        return (
            "<h1>404 - Page Not Found</h1>"
            "<p>FSSSMC Central Mosque</p>"
        ), 404


@app.errorhandler(500)
def internal_error(error):

    try:
        db = g.get("db")

        if db:
            db.rollback()

    except Exception:
        pass

    app.logger.exception(
        "UNHANDLED APPLICATION ERROR: %s",
        error
    )

    try:
        return safe_render("500.html"), 500
    except Exception:
        return (
            "<h1>500 - Server Error</h1>"
            "<p>The server encountered an error. Check Render Live Tail "
            "for the traceback.</p>"
        ), 500


# ================================================================
# INITIALIZE DATABASE
# ================================================================

with app.app_context():
    init_db()


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000"))
    )

