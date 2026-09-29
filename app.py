from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g,
    render_template_string
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

from email.message import EmailMessage
from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.middleware.proxy_fix import ProxyFix


# ================================================================
# OPTIONAL DOTENV
# ================================================================

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ================================================================
# APPLICATION CONFIGURATION
# ================================================================

app = Flask(__name__)

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "FsssmcCentralMosque_2026!Secure"
).strip()

if not SECRET_KEY:
    SECRET_KEY = "FsssmcCentralMosque_2026!Secure"

app.secret_key = SECRET_KEY

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("RENDER", "").lower() == "true"
    or os.environ.get("FLASK_ENV", "").lower() == "production"
)
app.config["SESSION_COOKIE_NAME"] = "fsssmc_session"
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_DOMAIN"] = None
app.config["PREFERRED_URL_SCHEME"] = "https"


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(DATABASE_DIR, "fss.db")
).strip()

if not DATABASE:
    DATABASE = os.path.join(
        DATABASE_DIR,
        "fss.db"
    )

DATABASE = os.path.abspath(DATABASE)

DATABASE_PARENT = os.path.dirname(DATABASE)

if DATABASE_PARENT:
    os.makedirs(
        DATABASE_PARENT,
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
# EMAIL / OTP CONFIGURATION
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
    ""
).strip()

SMTP_PASSWORD = os.environ.get(
    "SMTP_PASSWORD",
    ""
)

SMTP_FROM = os.environ.get(
    "SMTP_FROM",
    SMTP_USERNAME
).strip()

OTP_EXPIRY_MINUTES = 10
OTP_RESEND_SECONDS = 60


# ================================================================
# MAILBOXLAYER
# ================================================================

MAILBOXLAYER_API_KEY = os.environ.get(
    "MAILBOXLAYER_API_KEY",
    ""
).strip()


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


POSTS = [
    "Imam",
    "Doctor",
    "Engineer",
    "Teacher",
    "Student",
    "Business Owner",
    "Accountant",
    "Lawyer",
    "Civil Servant",
    "Trader",
    "Artisan",
    "Retired",
    "Other"
]


# ================================================================
# DATABASE
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

    add_column_if_missing(
        "users",
        "verification_code",
        "TEXT"
    )

    add_column_if_missing(
        "users",
        "verification_expires",
        "TEXT"
    )

    add_column_if_missing(
        "users",
        "verification_sent_at",
        "TEXT"
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
    # MIGRATIONS
    # ------------------------------------------------------------

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

        ("users", "email_verified", "INTEGER DEFAULT 0"),
        ("users", "verification_code", "TEXT"),
        ("users", "verification_expires", "TEXT"),
        ("users", "verification_sent_at", "TEXT")
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
                "Migration failed for %s.%s: %s",
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
    # ADMIN
    # ------------------------------------------------------------

    admin_email = os.environ.get(
        "ADMIN_EMAIL",
        "admin@fsssmc.org"
    ).strip().lower()

    admin_password = os.environ.get(
        "ADMIN_PASSWORD",
        "FsssmcCentralMosque_2026!Secure"
    )

    if not admin_password:

        if os.environ.get(
            "RENDER",
            ""
        ).lower() == "true":

            raise RuntimeError(
                "ADMIN_PASSWORD is required in Render Environment Variables."
            )

        admin_password = "ChangeThisPassword123!"

    existing_admin = db.execute(
        """
        SELECT *
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

        try:

            password_matches = check_password_hash(
                existing_admin["password_hash"],
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
                    generate_password_hash(
                        admin_password
                    ),
                    admin_email
                )
            )

    db.commit()


# ================================================================
# AUTH HELPERS
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
# SAFE TEMPLATE RENDER
# ================================================================

def safe_render(
    template_name,
    **context
):

    aliases = {

        "admin_login.html": [
            "admin/login.html",
            "admin_login.html"
        ],

        "admin.html": [
            "admin/dashboard.html",
            "admin_dashboard.html",
            "admin.html"
        ],

        "admin_members.html": [
            "admin/members.html",
            "admin_members.html"
        ],

        "admin_member_form.html": [
            "admin/member_form.html",
            "admin_member_form.html"
        ],

        "admin_donations.html": [
            "admin/donations.html",
            "admin_donations.html",
            "donations.html"
        ],

        "admin_announcements.html": [
            "admin/announcements.html",
            "admin_announcements.html"
        ]
    }

    candidates = aliases.get(
        template_name,
        [template_name]
    )

    for candidate in candidates:

        try:

            app.jinja_env.get_template(
                candidate
            )

            return render_template(
                candidate,
                **context
            )

        except Exception as error:

            from jinja2 import TemplateNotFound

            if isinstance(
                error,
                TemplateNotFound
            ):
                continue

            raise

    return (
        f"""
        <!doctype html>
        <html>
        <head>
        <meta charset="utf-8">
        <meta name="viewport"
              content="width=device-width,initial-scale=1">
        <title>FSSSMC Central Mosque</title>
        <style>
        body {{
            font-family: Arial,sans-serif;
            background:#f7f8f7;
            margin:0;
            padding:40px;
            color:#17352d;
        }}

        .box {{
            max-width:720px;
            margin:40px auto;
            background:white;
            padding:32px;
            border-radius:16px;
            box-shadow:0 8px 30px rgba(0,0,0,.08);
        }}

        h1 {{
            color:#006b57;
        }}

        code {{
            background:#eef3f1;
            padding:3px 7px;
            border-radius:5px;
        }}
        </style>
        </head>
        <body>
        <div class="box">
        <h1>FSSSMC Central Mosque</h1>
        <p>
        This page could not be loaded because its template
        is missing from the deployed project.
        </p>
        <p>
        Templates checked:
        <code>{", ".join(candidates)}</code>
        </p>
        </div>
        </body>
        </html>
        """,
        500
    )


# ================================================================
# LOGIN GATE
# ================================================================

@app.before_request
def require_login():

    public_endpoints = {
        "home",
        "index",
        "about",
        "prayer",
        "services",
        "events",
        "learn",
        "get_involved",
        "contact",
        "announcements",
        "donate",
        "member_register",
        "register_member",
        "login",
        "open_registration",
        "register",
        "verify_email",
        "resend_verification",
        "logout",
        "static",
        "paystack_webhook",
        "paystack_callback",
        "admin_login",
        "admin_logout",
        "page_not_found",
        "internal_error",
        "health"
    }

    endpoint = request.endpoint

    if endpoint in public_endpoints:
        return None

    if endpoint is None:
        return None

    if endpoint.startswith("admin_"):
        return None

    if account_authenticated():
        return None

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

    email = (
        email or ""
    ).strip().lower()

    if not email:
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

    if not MAILBOXLAYER_API_KEY:
        return True

    try:

        params = urlencode({
            "access_key": MAILBOXLAYER_API_KEY,
            "email": email,
            "smtp": "0",
            "format": "1"
        })

        url = (
            "https://apilayer.net/api/check?"
            + params
        )

        req = Request(
            url,
            headers={
                "User-Agent": "FSSSMC-Central-Mosque/1.0"
            }
        )

        with urlopen(
            req,
            timeout=10
        ) as response:

            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        if data.get("success") is False:
            return True

        disposable = data.get(
            "disposable",
            False
        )

        if disposable:
            return False

        return True

    except Exception as error:

        app.logger.warning(
            "Mailboxlayer validation failed: %s",
            error
        )

        # Fail open if Mailboxlayer is temporarily unavailable.
        return True


# ================================================================
# OTP HELPERS
# ================================================================

def generate_otp():

    return str(
        secrets.randbelow(
            900000
        ) + 100000
    )


def send_verification_email(
    email,
    name,
    code
):

    if not SMTP_USERNAME or not SMTP_PASSWORD:

        raise RuntimeError(
            "SMTP_USERNAME and SMTP_PASSWORD are not configured."
        )

    message = EmailMessage()

    message["Subject"] = (
        "FSSSMC Central Mosque - Email Verification"
    )

    message["From"] = (
        SMTP_FROM or SMTP_USERNAME
    )

    message["To"] = email

    message.set_content(
        f"""
Assalamu Alaikum {name},

Your FSSSMC Central Mosque verification code is:

{code}

This code expires in {OTP_EXPIRY_MINUTES} minutes.

If you did not create an account on the FSSSMC Central Mosque website,
you can ignore this email.

FSSSMC Central Mosque
"""
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30
    ) as server:

        server.starttls()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.send_message(
            message
        )


def create_and_send_otp(
    user_id,
    email,
    name
):

    db = get_db()

    now = datetime.utcnow()

    existing = db.execute(
        """
        SELECT verification_sent_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if existing and existing["verification_sent_at"]:

        try:

            last_sent = datetime.fromisoformat(
                existing["verification_sent_at"]
            )

            elapsed = (
                now - last_sent
            ).total_seconds()

            if elapsed < OTP_RESEND_SECONDS:

                remaining = int(
                    OTP_RESEND_SECONDS - elapsed
                )

                return (
                    False,
                    f"Please wait {remaining} seconds before requesting another code."
                )

        except ValueError:
            pass

    code = generate_otp()

    expires = (
        now + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )
    ).isoformat()

    sent_at = now.isoformat()

    db.execute(
        """
        UPDATE users
        SET verification_code = ?,
            verification_expires = ?,
            verification_sent_at = ?
        WHERE id = ?
        """,
        (
            code,
            expires,
            sent_at,
            user_id
        )
    )

    db.commit()

    try:

        send_verification_email(
            email,
            name,
            code
        )

    except Exception as error:

        db.execute(
            """
            UPDATE users
            SET verification_code = NULL,
                verification_expires = NULL,
                verification_sent_at = NULL
            WHERE id = ?
            """,
            (user_id,)
        )

        db.commit()

        app.logger.exception(
            "Could not send verification email: %s",
            error
        )

        return (
            False,
            "Could not send the verification code. Please check the email configuration."
        )

    return (
        True,
        "A verification code has been sent to your email."
    )


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

        try:

            password_ok = check_password_hash(
                admin["password_hash"],
                password
            )

        except Exception:

            password_ok = False

        if password_ok:

            session.clear()

            session["admin_id"] = int(
                admin["id"]
            )

            session["admin_email"] = str(
                admin["email"]
            )

            session.modified = True

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
    # NORMAL USER
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

    try:

        password_ok = check_password_hash(
            user["password_hash"],
            password
        )

    except Exception:

        password_ok = False

    if not password_ok:

        flash(
            "Invalid email or password.",
            "error"
        )

        return safe_render(
            "login.html"
        )

    # ------------------------------------------------------------
    # EMAIL VERIFICATION
    # ------------------------------------------------------------

    if not bool(
        user["email_verified"]
    ):

        session["pending_user_id"] = int(
            user["id"]
        )

        session["pending_email"] = str(
            user["email"]
        )

        session["pending_name"] = str(
            user["name"]
        )

        session.modified = True

        flash(
            "Please verify your email before logging in.",
            "error"
        )

        return redirect(
            url_for("verify_email")
        )

    # ------------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------------

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
        f"Login successful. Welcome back, {user['name']}.",
        "success"
    )

    next_url = request.args.get(
        "next",
        ""
    ).strip()

    if (
        next_url.startswith("/")
        and not next_url.startswith("//")
    ):
        return redirect(
            next_url
        )

    return redirect(
        url_for("profile")
    )


# ================================================================
# CREATE ACCOUNT
# ================================================================

@app.route(
    "/create-account"
)
def open_registration():

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

    # IMPORTANT:
    # Registration must NEVER require a previous session.
    # This was the reason your Create Account button was returning
    # to the login page.

    if account_authenticated():

        return redirect(
            url_for("profile")
        )

    if admin_authenticated():

        return redirect(
            url_for("admin_dashboard")
        )

    # ------------------------------------------------------------
    # GET
    # ------------------------------------------------------------

    if request.method == "GET":

        return safe_render(
            "register.html"
        )

    # ------------------------------------------------------------
    # POST
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

    if not basic_email_valid(email):

        flash(
            "Please enter a valid email address.",
            "error"
        )

        return safe_render(
            "register.html"
        )

    if not validate_email_with_mailboxlayer(
        email
    ):

        flash(
            "Please use a valid non-disposable email address.",
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

    db = get_db()

    existing_user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    # ------------------------------------------------------------
    # EXISTING UNVERIFIED ACCOUNT
    # ------------------------------------------------------------

    if existing_user and not bool(
        existing_user["email_verified"]
    ):

        session["pending_user_id"] = int(
            existing_user["id"]
        )

        session["pending_email"] = email

        session["pending_name"] = str(
            existing_user["name"]
        )

        session.modified = True

        success, message = create_and_send_otp(
            existing_user["id"],
            email,
            existing_user["name"]
        )

        if success:

            flash(
                message,
                "success"
            )

        else:

            flash(
                message,
                "error"
            )

        return redirect(
            url_for("verify_email")
        )

    # ------------------------------------------------------------
    # EXISTING VERIFIED ACCOUNT
    # ------------------------------------------------------------

    if existing_user:

        flash(
            "An account with this email already exists. Please log in instead.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    now = datetime.utcnow().isoformat()

    try:

        cursor = db.execute(
            """
            INSERT INTO users (
                name,
                surname,
                email,
                password_hash,
                created_at,
                email_verified,
                verification_code,
                verification_expires,
                verification_sent_at
            )
            VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, NULL)
            """,
            (
                name,
                surname,
                email,
                generate_password_hash(
                    password
                ),
                now
            )
        )

        db.commit()

    except sqlite3.IntegrityError:

        db.rollback()

        flash(
            "An account with this email already exists.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    user_id = cursor.lastrowid

    session["pending_user_id"] = int(
        user_id
    )

    session["pending_email"] = email

    session["pending_name"] = name

    session.modified = True

    success, message = create_and_send_otp(
        user_id,
        email,
        name
    )

    if not success:

        # Remove the account if the first verification email
        # could not be sent. This prevents unusable accounts.
        db.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        db.commit()

        session.pop(
            "pending_user_id",
            None
        )

        session.pop(
            "pending_email",
            None
        )

        session.pop(
            "pending_name",
            None
        )

        flash(
            message,
            "error"
        )

        return safe_render(
            "register.html"
        )

    flash(
        message,
        "success"
    )

    return redirect(
        url_for("verify_email")
    )


# ================================================================
# VERIFY EMAIL
# ================================================================

@app.route(
    "/verify-email",
    methods=["GET", "POST"]
)
def verify_email():

    user_id = session.get(
        "pending_user_id"
    )

    if not user_id:

        return redirect(
            url_for("register")
        )

    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if not user:

        session.pop(
            "pending_user_id",
            None
        )

        return redirect(
            url_for("register")
        )

    if bool(
        user["email_verified"]
    ):

        session.pop(
            "pending_user_id",
            None
        )

        session.pop(
            "pending_email",
            None
        )

        session.pop(
            "pending_name",
            None
        )

        flash(
            "Your email is already verified. Please log in.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    if request.method == "GET":

        return render_template_string(
            """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">
<title>Email Verification | FSSSMC Central Mosque</title>
<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: #f4f7f5;
    font-family: Inter, Arial, sans-serif;
    color: #17352d;
}

.verify-box {
    width: 100%;
    max-width: 500px;
    background: #ffffff;
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 18px 60px rgba(0,0,0,.10);
}

.logo {
    width: 76px;
    height: 76px;
    object-fit: contain;
    display: block;
    margin: 0 auto 20px;
}

h1 {
    margin: 0 0 10px;
    text-align: center;
    color: #006b57;
}

p {
    line-height: 1.7;
    text-align: center;
}

.email {
    font-weight: 700;
    color: #006b57;
    word-break: break-word;
}

input {
    width: 100%;
    padding: 15px;
    border: 1px solid #ccd8d3;
    border-radius: 10px;
    font-size: 22px;
    text-align: center;
    letter-spacing: 7px;
    margin-top: 18px;
}

button {
    width: 100%;
    border: 0;
    padding: 14px;
    margin-top: 18px;
    border-radius: 10px;
    background: #006b57;
    color: white;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
}

button:hover {
    background: #005846;
}

.resend {
    display: block;
    text-align: center;
    margin-top: 18px;
    color: #006b57;
    text-decoration: none;
    font-weight: 700;
}
</style>
</head>

<body>

<div class="verify-box">

<img
    class="logo"
    src="{{ url_for('static', filename='images/fsssmc.jpeg') }}"
    alt="FSSSMC Central Mosque"
>

<h1>Verify Your Email</h1>

<p>
We sent a 6-digit verification code to
</p>

<p class="email">
{{ user["email"] }}
</p>

<form method="post">

<input
    type="text"
    name="code"
    inputmode="numeric"
    autocomplete="one-time-code"
    maxlength="6"
    pattern="[0-9]{6}"
    placeholder="000000"
    required
>

<button type="submit">
Verify Email
</button>

</form>

<a class="resend"
   href="{{ url_for('resend_verification') }}">
Resend verification code
</a>

</div>

</body>
</html>
            """,
            user=user
        )

    code = request.form.get(
        "code",
        ""
    ).strip()

    if not code:

        flash(
            "Please enter the verification code.",
            "error"
        )

        return redirect(
            url_for("verify_email")
        )

    if not code.isdigit() or len(code) != 6:

        flash(
            "The verification code must contain 6 digits.",
            "error"
        )

        return redirect(
            url_for("verify_email")
        )

    stored_code = user["verification_code"]

    expires = user["verification_expires"]

    if not stored_code or not expires:

        flash(
            "Your verification code has expired. Please request a new one.",
            "error"
        )

        return redirect(
            url_for("verify_email")
        )

    try:

        expiry_time = datetime.fromisoformat(
            expires
        )

    except ValueError:

        expiry_time = datetime.utcnow() - timedelta(
            seconds=1
        )

    if datetime.utcnow() > expiry_time:

        flash(
            "Your verification code has expired. Please request a new one.",
            "error"
        )

        return redirect(
            url_for("verify_email")
        )

    if not secrets.compare_digest(
        str(stored_code),
        code
    ):

        flash(
            "Incorrect verification code.",
            "error"
        )

        return redirect(
            url_for("verify_email")
        )

    db.execute(
        """
        UPDATE users
        SET email_verified = 1,
            verification_code = NULL,
            verification_expires = NULL,
            verification_sent_at = NULL
        WHERE id = ?
        """,
        (user_id,)
    )

    db.commit()

    name = str(
        user["name"]
    )

    surname = str(
        user["surname"]
    )

    email = str(
        user["email"]
    )

    session.clear()

    session["user_id"] = int(
        user_id
    )

    session["user_name"] = name

    session["user_surname"] = surname

    session["user_email"] = email

    session.modified = True

    flash(
        f"Email verified successfully. Welcome, {name}.",
        "success"
    )

    return redirect(
        url_for("profile")
    )


# ================================================================
# RESEND VERIFICATION
# ================================================================

@app.route(
    "/resend-verification"
)
def resend_verification():

    user_id = session.get(
        "pending_user_id"
    )

    if not user_id:

        return redirect(
            url_for("register")
        )

    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    if not user:

        session.clear()

        flash(
            "Account not found.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if bool(
        user["email_verified"]
    ):

        flash(
            "Your email is already verified.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    success, message = create_and_send_otp(
        user["id"],
        user["email"],
        user["name"]
    )

    flash(
        message,
        "success" if success else "error"
    )

    return redirect(
        url_for("verify_email")
    )


# ================================================================
# LOGOUT
# ================================================================

@app.route(
    "/logout"
)
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

@app.route(
    "/profile"
)
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


# IMPORTANT:
# Older templates use url_for("index").
# Your real homepage endpoint is "home".
# This alias prevents contact.html and older templates from
# producing BuildError: Could not build url for endpoint 'index'.

app.add_url_rule(
    "/",
    endpoint="index",
    view_func=home
)


# ================================================================
# ABOUT
# ================================================================

@app.route(
    "/about"
)
def about():

    return safe_render(
        "about.html",
        executive_members=EXECUTIVE_MEMBERS,
        facilities=FACILITIES
    )


# ================================================================
# PRAYER - ALADHAN API
# ================================================================

def get_prayer_times():

    today = datetime.now().strftime(
        "%d-%m-%Y"
    )

    params = urlencode({
        "city": "Lagos",
        "country": "Nigeria",
        "method": 2,
        "school": 0
    })

    api_url = (
        "https://api.aladhan.com/v1/timingsByCity/"
        f"{today}?{params}"
    )

    try:

        req = Request(
            api_url,
            headers={
                "User-Agent":
                    "FSSSMC-Central-Mosque/1.0"
            }
        )

        with urlopen(
            req,
            timeout=10
        ) as response:

            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        if payload.get(
            "code"
        ) != 200:

            raise ValueError(
                "AlAdhan returned an unsuccessful response."
            )

        data = payload.get(
            "data",
            {}
        )

        timings = data.get(
            "timings",
            {}
        )

        date_info = data.get(
            "date",
            {}
        )

        prayer_times = {
            "Fajr": timings.get(
                "Fajr",
                "--:--"
            ),
            "Sunrise": timings.get(
                "Sunrise",
                "--:--"
            ),
            "Dhuhr": timings.get(
                "Dhuhr",
                "--:--"
            ),
            "Asr": timings.get(
                "Asr",
                "--:--"
            ),
            "Maghrib": timings.get(
                "Maghrib",
                "--:--"
            ),
            "Isha": timings.get(
                "Isha",
                "--:--"
            )
        }

        return {
            "times": prayer_times,
            "date": date_info.get(
                "readable",
                today
            ),
            "hijri": date_info.get(
                "hijri",
                {}
            ).get(
                "date",
                ""
            ),
            "location": "Lagos, Nigeria",
            "method": "AlAdhan — ISNA (Method 2)",
            "error": None
        }

    except (
        URLError,
        HTTPError,
        TimeoutError,
        ValueError,
        KeyError,
        json.JSONDecodeError
    ) as error:

        app.logger.warning(
            "Prayer API request failed: %s",
            error
        )

        return {
            "times": {
                "Fajr": "05:20",
                "Sunrise": "06:35",
                "Dhuhr": "12:38",
                "Asr": "15:51",
                "Maghrib": "18:40",
                "Isha": "19:45"
            },
            "date": today,
            "hijri": "",
            "location": "Lagos, Nigeria",
            "method": "AlAdhan — ISNA (Method 2)",
            "error": (
                "Live prayer-time service is temporarily unavailable. "
                "Showing the latest fallback schedule."
            )
        }


@app.route(
    "/prayer"
)
def prayer():

    prayer_data = get_prayer_times()

    return safe_render(
        "prayer.html",
        prayer_times=prayer_data["times"],
        prayer_date=prayer_data["date"],
        hijri_date=prayer_data["hijri"],
        location=prayer_data["location"],
        prayer_method=prayer_data["method"],
        prayer_error=prayer_data["error"]
    )


# ================================================================
# SERVICES
# ================================================================

@app.route(
    "/services"
)
def services():

    return safe_render(
        "services.html",
        facilities=FACILITIES
    )


# ================================================================
# EVENTS
# ================================================================

@app.route(
    "/events"
)
def events():

    db = get_db()

    event_announcements = db.execute(
        """
        SELECT
            id,
            title,
            body,
            published,
            created_at,
            updated_at
        FROM announcements
        WHERE COALESCE(published, 0) = 1
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    return safe_render(
        "events.html",
        announcements=event_announcements
    )


# ================================================================
# LEARN
# ================================================================

@app.route(
    "/learn"
)
def learn():

    return safe_render(
        "learn.html"
    )


# ================================================================
# GET INVOLVED
# ================================================================

@app.route(
    "/get-involved"
)
def get_involved():

    return safe_render(
        "get-involved.html"
    )


# ================================================================
# CONTACT
# ================================================================

@app.route(
    "/contact"
)
def contact():

    committee_data = {
        committee["name"]: [
            (
                committee["description"],
                ""
            )
        ]
        for committee in COMMITTEES
    }

    jummah_data = [
        imam["name"]
        for imam in JUMMAH_IMAMS
    ]

    past_data = [
        {
            "name": person.get(
                "name",
                ""
            ),
            "status": person.get(
                "status",
                person.get(
                    "role",
                    ""
                )
            )
        }
        for person in PAST_EXECUTIVE
    ]

    db = get_db()

    registered_members = db.execute(
        """
        SELECT
            id,
            name,
            surname,
            post,
            created_at
        FROM members
        ORDER BY created_at DESC
        LIMIT 20
        """
    ).fetchall()

    return safe_render(
        "contact.html",
        executive_members=EXECUTIVE_MEMBERS,
        past_executive=past_data,
        committees=committee_data,
        jummah_imams=jummah_data,
        posts=POSTS,
        registered_members=registered_members
    )


# ================================================================
# ANNOUNCEMENTS
# ================================================================

@app.route(
    "/announcements"
)
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

        try:

            return render_template(
                "member_register.html",
                posts=POSTS
            )

        except Exception as error:

            from jinja2 import TemplateNotFound

            if not isinstance(
                error,
                TemplateNotFound
            ):
                raise

            return render_template_string(
                """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1">
<title>Member Registration</title>
<style>
body {
    font-family: Arial,sans-serif;
    background:#f5f7f5;
    margin:0;
    padding:30px;
    color:#17352d;
}

.box {
    max-width:680px;
    margin:auto;
    background:#fff;
    padding:28px;
    border-radius:16px;
    box-shadow:0 8px 30px rgba(0,0,0,.08);
}

h1 {
    color:#006b57;
}

label {
    display:block;
    margin-top:14px;
    font-weight:600;
}

input,
textarea,
select {
    width:100%;
    box-sizing:border-box;
    padding:11px;
    margin-top:6px;
    border:1px solid #ccd7d2;
    border-radius:8px;
}

button {
    margin-top:20px;
    padding:12px 18px;
    border:0;
    border-radius:8px;
    background:#006b57;
    color:white;
    font-weight:700;
    cursor:pointer;
}
</style>
</head>

<body>

<div class="box">

<h1>Member Registration</h1>

<form method="post">

<label>
First Name
<input name="name" required>
</label>

<label>
Surname
<input name="surname" required>
</label>

<label>
Phone Number
<input name="phone" required>
</label>

<label>
Email
<input type="email" name="email" required>
</label>

<label>
Address
<textarea name="address" required></textarea>
</label>

<label>
Post / Occupation

<select name="post" required>

<option value="">
Select occupation
</option>

{% for item in posts %}

<option value="{{ item }}">
{{ item }}
</option>

{% endfor %}

</select>

</label>

<label>
Notes
<textarea name="notes"></textarea>
</label>

<button type="submit">
Register as Member
</button>

</form>

</div>

</body>
</html>
                """,
                posts=POSTS
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

    if post not in POSTS:

        flash(
            "Please select a valid occupation.",
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
            "This member could not be registered.",
            "error"
        )

        return redirect(
            url_for("member_register")
        )

    flash(
        "Membership registration submitted successfully.",
        "success"
    )

    if account_authenticated():

        return redirect(
            url_for("profile")
        )

    return redirect(
        url_for("contact")
    )


# Backward-compatible endpoint.
app.add_url_rule(
    "/members/register",
    endpoint="register_member",
    view_func=member_register,
    methods=["GET", "POST"]
)


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
            "Paystack is not configured."
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

            parsed = json.loads(
                body
            )

            if not parsed.get(
                "status",
                False
            ):

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

    except URLError:

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
        "amount": amount_kobo,
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
    reference,
    transaction=None
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

    if transaction is not None:

        try:

            expected_kobo = naira_to_kobo(
                donation["amount"]
            )

            received_kobo = int(
                transaction.get(
                    "amount",
                    0
                )
            )

            currency = str(
                transaction.get(
                    "currency",
                    ""
                )
            ).upper()

            tx_reference = str(
                transaction.get(
                    "reference",
                    ""
                )
            ).strip()

        except (
            TypeError,
            ValueError,
            InvalidOperation
        ):

            return False

        if (
            expected_kobo is None
            or received_kobo != expected_kobo
        ):

            return False

        if (
            currency != PAYSTACK_CURRENCY
            or tx_reference != reference
        ):

            return False

    db.execute(
        """
        UPDATE donations
        SET payment_status = 'paid',
            paid_at = ?
        WHERE payment_reference = ?
        """,
        (
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

            if (
                reference
                and transaction.get(
                    "status"
                ) == "success"
            ):

                mark_donation_as_paid(
                    reference,
                    transaction
                )

        return "", 200

    except Exception:

        app.logger.exception(
            "Paystack webhook error"
        )

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
                    Decimal(
                        str(amount)
                    )
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

        return redirect(
            url_for("donate")
        )

    callback_url = url_for(
        "paystack_callback",
        _external=True
    )

    metadata = {
        "donor_name": donor_name,
        "phone": phone,
        "purpose": purpose
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
        .get(
            "data",
            {}
        )
        .get(
            "authorization_url"
        )
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
        and transaction.get("status") == "success"
    ):

        if mark_donation_as_paid(
            reference,
            transaction
        ):

            flash(
                "Donation payment completed successfully. "
                "Thank you for your support.",
                "success"
            )

            if account_authenticated():
                return redirect(
                    url_for("profile")
                )

            return redirect(
                url_for("donate")
            )

        flash(
            "Payment verification failed because the transaction details "
            "did not match the donation record.",
            "error"
        )

        return redirect(
            url_for("donate")
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

    try:

        password_ok = bool(
            admin
            and check_password_hash(
                admin["password_hash"],
                password
            )
        )

    except Exception:

        password_ok = False

    if not password_ok:

        flash(
            "Invalid administrator credentials.",
            "error"
        )

        return safe_render(
            "admin_login.html"
        )

    session.clear()

    session["admin_id"] = int(
        admin["id"]
    )

    session["admin_email"] = str(
        admin["email"]
    )

    session.modified = True

    flash(
        "Administrator login successful.",
        "success"
    )

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

@app.route(
    "/admin"
)
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
        members=members,
        posts=POSTS
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
            member=None,
            posts=POSTS
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
            member=None,
            posts=POSTS
        )

    if post not in POSTS:

        flash(
            "Please select a valid occupation.",
            "error"
        )

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS
        )

    db = get_db()

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

    except sqlite3.IntegrityError:

        db.rollback()

        flash(
            "A member with this information already exists.",
            "error"
        )

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS
        )

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
            member=member,
            posts=POSTS
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
            member=member,
            posts=POSTS
        )

    if post not in POSTS:

        flash(
            "Please select a valid occupation.",
            "error"
        )

        return safe_render(
            "admin_member_form.html",
            member=member,
            posts=POSTS
        )

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
    "/admin/donations/<int:donation_id>/update",
    methods=["POST"]
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
# HEALTH
# ================================================================

@app.route(
    "/health"
)
def health():

    try:

        db = get_db()

        db.execute(
            "SELECT 1"
        ).fetchone()

        return {
            "status": "ok"
        }, 200

    except Exception:

        app.logger.exception(
            "Health check failed"
        )

        return {
            "status": "error"
        }, 503


# ================================================================
# ERROR HANDLERS
# ================================================================

@app.errorhandler(404)
def page_not_found(error):

    try:

        return safe_render(
            "404.html"
        ), 404

    except Exception:

        return (
            "<h1>404 - Page Not Found</h1>"
            "<p>FSSSMC Central Mosque</p>"
        ), 404


@app.errorhandler(500)
def internal_error(error):

    try:

        db = g.get(
            "db"
        )

        if db:
            db.rollback()

    except Exception:
        pass

    app.logger.exception(
        "UNHANDLED APPLICATION ERROR: %s",
        error
    )

    try:

        return safe_render(
            "500.html"
        ), 500

    except Exception:

        return (
            "<h1>500 - Server Error</h1>"
            "<p>The server encountered an error.</p>"
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
        debug=(
            os.environ.get(
                "FLASK_DEBUG",
                "0"
            ) == "1"
        ),
        use_reloader=False,
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                "5000"
            )
        )
    )