from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g,
    render_template_string,
)

import sqlite3
import os
import json
import hashlib
import hmac
import secrets


from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


from functools import wraps
from datetime import datetime
from decimal import Decimal, InvalidOperation

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
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
# APPLICATION
# ================================================================

app = Flask(__name__)


SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "FsssmcCentralMosque_2026!Secure",
).strip()

if not SECRET_KEY:
    SECRET_KEY = "FsssmcCentralMosque_2026!Secure"

app.secret_key = SECRET_KEY


app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
)


app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.environ.get("RENDER", "").lower() == "true"
        or os.environ.get("FLASK_ENV", "").lower() == "production"
    ),
    SESSION_COOKIE_NAME="fsssmc_session",
    SESSION_COOKIE_PATH="/",
    SESSION_COOKIE_DOMAIN=None,
    PREFERRED_URL_SCHEME="https",
)


# ================================================================
# DATABASE LOCATION
# ================================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database",
)

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(DATABASE_DIR, "fss.db"),
).strip()

if not DATABASE:
    DATABASE = os.path.join(
        DATABASE_DIR,
        "fss.db",
    )

DATABASE = os.path.abspath(DATABASE)

DATABASE_PARENT = os.path.dirname(DATABASE)

if DATABASE_PARENT:
    os.makedirs(
        DATABASE_PARENT,
        exist_ok=True,
    )

print("DATABASE LOCATION:", DATABASE)


# ================================================================
# PAYSTACK
# ================================================================

PAYSTACK_SECRET_KEY = os.environ.get(
    "PAYSTACK_SECRET_KEY",
    "sk_test_0d971bb72ebed6d23d0471924df87bd5941db555",
).strip()

PAYSTACK_PUBLIC_KEY = os.environ.get(
    "PAYSTACK_PUBLIC_KEY",
    "pk_test_3a23b0594bd9ee4878b78d7d090f4d4a12a62721",
).strip()

PAYSTACK_BASE_URL = os.environ.get(
    "PAYSTACK_BASE_URL",
    "https://api.paystack.co",
).strip()

if not PAYSTACK_BASE_URL:
    PAYSTACK_BASE_URL = "https://api.paystack.co"

PAYSTACK_BASE_URL = PAYSTACK_BASE_URL.rstrip("/")

PAYSTACK_CURRENCY = "NGN"


 


# ================================================================
# MAILBOXLAYER
# ================================================================

MAILBOXLAYER_API_KEY = os.environ.get(
    "MAILBOXLAYER_API_KEY",
    "edb349802dd334a9479417e4b16e060a ",
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
    "Other",
]


EXECUTIVE_MEMBERS = [
    {
        "name": "Amir Muritala Adekunle Balogun",
        "role": "Amir",
    },
    {
        "name": "Imam Mustapha Motilola Alli",
        "role": "Imam",
    },
    {
        "name": "Ishaq Aderemi Abimbola",
        "role": "Secretary",
    },
    {
        "name": "Abdul Ganiyu Olayinka Dabiri",
        "role": "Executive Member",
    },
    {
        "name": "Lukman Badiru",
        "role": "Executive Member",
    },
    {
        "name": "Lateef Usman",
        "role": "Executive Member",
    },
    {
        "name": "Prof. Zaid Aderolu",
        "role": "Executive Member",
    },
    {
        "name": "Lasisi Abayomi Lawal",
        "role": "Executive Member",
    },
    {
        "name": "Hassan Muhammad Bello",
        "role": "Executive Member",
    },
    {
        "name": "Engr. Ismail Sanni",
        "role": "Executive Member",
    },
    {
        "name": "Monsuru Oladehide",
        "role": "Executive Member",
    },
]


PAST_EXECUTIVE = [
    {
        "name": "Previous Executive",
        "role": "Past Executive Member",
    }
]


COMMITTEES = [
    {
        "name": "Education Committee",
        "description": (
            "Coordinates Islamic learning, lectures, "
            "classes and educational programmes."
        ),
    },
    {
        "name": "Welfare Committee",
        "description": (
            "Supports members and community welfare initiatives."
        ),
    },
    {
        "name": "Finance Committee",
        "description": (
            "Supports responsible financial administration "
            "and accountability."
        ),
    },
    {
        "name": "Maintenance Committee",
        "description": (
            "Coordinates mosque facilities and maintenance."
        ),
    },
    {
        "name": "Youth Committee",
        "description": (
            "Coordinates activities and programmes for young members."
        ),
    },
]


JUMMAH_IMAMS = [
    {
        "name": "Ustadh Abdul Granny Adebayo Ejalonibu",
        "role": "Jummah Imam / Khatib",
    }
]


FACILITIES = [
    "Main Prayer Hall",
    "Women's Prayer Area",
    "Islamic Library",
    "Ablution Facilities",
    "Classrooms",
    "Meeting Halls",
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
    "Other",
]


# ================================================================
# DATABASE HELPERS
# ================================================================

def get_db():
    if "db" not in g:

        g.db = sqlite3.connect(
            DATABASE,
            timeout=30,
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
        None,
    )

    if db is not None:
        db.close()


def table_exists(table_name):

    db = get_db()

    row = db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def column_exists(
    table_name,
    column_name,
):

    if not table_exists(table_name):
        return False

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
    definition,
):

    db = get_db()

    if not table_exists(table_name):
        return

    if not column_exists(
        table_name,
        column_name,
    ):

        db.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )

        db.commit()


# ================================================================
# DATABASE INITIALIZATION
# ================================================================

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
            created_at TEXT NOT NULL,
            email_verified INTEGER DEFAULT 0,
            verification_code TEXT,
            verification_expires TEXT,
            verification_sent_at TEXT
        )
        """
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

    db.commit()

    # ------------------------------------------------------------
    # MIGRATIONS
    # ------------------------------------------------------------

    migrations = [
        (
            "users",
            "email_verified",
            "INTEGER DEFAULT 0",
        ),
        (
            "users",
            "verification_code",
            "TEXT",
        ),
        (
            "users",
            "verification_expires",
            "TEXT",
        ),
        (
            "users",
            "verification_sent_at",
            "TEXT",
        ),

        (
            "members",
            "email",
            "TEXT",
        ),
        (
            "members",
            "notes",
            "TEXT",
        ),
        (
            "members",
            "created_at",
            "TEXT",
        ),
        (
            "members",
            "updated_at",
            "TEXT",
        ),

        (
            "donations",
            "phone",
            "TEXT",
        ),
        (
            "donations",
            "email",
            "TEXT",
        ),
        (
            "donations",
            "amount",
            "REAL",
        ),
        (
            "donations",
            "purpose",
            "TEXT",
        ),
        (
            "donations",
            "payment_reference",
            "TEXT",
        ),
        (
            "donations",
            "payment_method",
            "TEXT DEFAULT 'paystack'",
        ),
        (
            "donations",
            "payment_status",
            "TEXT DEFAULT 'pending'",
        ),
        (
            "donations",
            "notes",
            "TEXT",
        ),
        (
            "donations",
            "created_at",
            "TEXT",
        ),
        (
            "donations",
            "paid_at",
            "TEXT",
        ),

        (
            "announcements",
            "published",
            "INTEGER DEFAULT 1",
        ),
        (
            "announcements",
            "created_at",
            "TEXT",
        ),
        (
            "announcements",
            "updated_at",
            "TEXT",
        ),
    ]

    for (
        table_name,
        column_name,
        definition,
    ) in migrations:

        try:

            add_column_if_missing(
                table_name,
                column_name,
                definition,
            )

        except sqlite3.OperationalError as error:

            app.logger.warning(
                "Migration failed for %s.%s: %s",
                table_name,
                column_name,
                error,
            )

    # ------------------------------------------------------------
    # INDEXES
    # ------------------------------------------------------------

    try:
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
            CREATE INDEX IF NOT EXISTS idx_members_email
            ON members(email)
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

        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_announcements_published
            ON announcements(published)
            """
        )

        db.commit()

    except sqlite3.OperationalError as error:

        app.logger.warning(
            "Index creation warning: %s",
            error,
        )

    # ------------------------------------------------------------
    # ADMIN ACCOUNT
    # ------------------------------------------------------------

    admin_email = os.environ.get(
        "ADMIN_EMAIL",
        "admin@fsssmc.org",
    ).strip().lower()

    admin_password = os.environ.get(
        "ADMIN_PASSWORD",
        "FsssmcCentralMosque_2026!Secure",
    ).strip()

    if not admin_password:

        if os.environ.get(
            "RENDER",
            "",
        ).lower() == "true":

            raise RuntimeError(
                "ADMIN_PASSWORD is required in Render Environment Variables."
            )

        admin_password = (
            "ChangeThisPassword123!"
        )

    existing_admin = db.execute(
        """
        SELECT *
        FROM admins
        WHERE email = ?
        """,
        (admin_email,),
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
                datetime.utcnow().isoformat(),
            ),
        )

    else:

        try:

            password_matches = check_password_hash(
                existing_admin["password_hash"],
                admin_password,
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
                    admin_email,
                ),
            )

    db.commit()


# ================================================================
# AUTHENTICATION
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
                url_for("login")
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
        "admin_logged_in": admin_authenticated(),
        "current_user_name": session.get(
            "user_name"
        ),
        "current_user_surname": session.get(
            "user_surname"
        ),
        "current_user_email": session.get(
            "user_email"
        ),
    }


# ================================================================
# SAFE TEMPLATE RENDERING
# ================================================================

def safe_render(
    template_name,
    **context,
):

    aliases = {

        "admin_login.html": [
            "admin/login.html",
            "admin_login.html",
        ],

        "admin.html": [
            "admin/dashboard.html",
            "admin_dashboard.html",
            "admin.html",
        ],

        "admin_members.html": [
            "admin/members.html",
            "admin_members.html",
        ],

        "admin_member_form.html": [
            "admin/member_form.html",
            "admin_member_form.html",
        ],

        "admin_donations.html": [
            "admin/donations.html",
            "admin_donations.html",
            "donations.html",
        ],

        "admin_announcements.html": [
            "admin/announcements.html",
            "admin_announcements.html",
        ],
    }

    candidates = aliases.get(
        template_name,
        [template_name],
    )

    from jinja2 import TemplateNotFound

    for candidate in candidates:

        try:

            app.jinja_env.get_template(
                candidate
            )

            return render_template(
                candidate,
                **context,
            )

        except TemplateNotFound:

            continue

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
            font-family: Arial, sans-serif;
            background: #f7f8f7;
            margin: 0;
            padding: 40px;
            color: #17352d;
        }}

        .box {{
            max-width: 720px;
            margin: 40px auto;
            background: white;
            padding: 32px;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,.08);
        }}

        h1 {{
            color: #006b57;
        }}

        code {{
            background: #eef3f1;
            padding: 3px 7px;
            border-radius: 5px;
        }}
        </style>
        </head>

        <body>

        <div class="box">

        <h1>FSSSMC Central Mosque</h1>

        <p>
        The requested page template could not be found.
        </p>

        <p>
        Template:
        <code>{template_name}</code>
        </p>

        <p>
        Templates checked:
        <code>{", ".join(candidates)}</code>
        </p>

        </div>

        </body>
        </html>
        """,
        500,
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
        

        "logout",

        "static",

        "paystack_webhook",
        "paystack_callback",

        "admin_login",
        "admin_logout",

        "page_not_found",
        "internal_error",

        "health",
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
            next=request.path,
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
            "format": "1",
        })

        api_url = (
            "https://apilayer.net/api/check?"
            + params
        )

        req = Request(
            api_url,
            headers={
                "User-Agent":
                    "FSSSMC-Central-Mosque/1.0",
            },
        )

        with urlopen(
            req,
            timeout=10,
        ) as response:

            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        if data.get("success") is False:
            return True

        if data.get(
            "disposable",
            False,
        ):
            return False

        return True

    except Exception as error:

        app.logger.warning(
            "Mailboxlayer validation failed: %s",
            error,
        )

        return True




# ================================================================
# LOGIN
# ================================================================

@app.route(
    "/login",
    methods=["GET", "POST"],
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
        "",
    ).strip().lower()

    password = request.form.get(
        "password",
        "",
    )

    if not email or not password:

        flash(
            "Please enter your email and password.",
            "error",
        )

        return safe_render(
            "login.html"
        )

    db = get_db()

    # ------------------------------------------------------------
    # ADMIN LOGIN THROUGH NORMAL LOGIN PAGE
    # ------------------------------------------------------------

    admin = db.execute(
        """
        SELECT *
        FROM admins
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if admin:

        try:

            password_ok = check_password_hash(
                admin["password_hash"],
                password,
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
                "success",
            )

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid email or password.",
            "error",
        )

        return safe_render(
            "login.html"
        )

    # ------------------------------------------------------------
    # NORMAL USER LOGIN
    # ------------------------------------------------------------

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if not user:

        flash(
            "Invalid email or password.",
            "error",
        )

        return safe_render(
            "login.html"
        )

    try:

        password_ok = check_password_hash(
            user["password_hash"],
            password,
        )

    except Exception:

        password_ok = False

    if not password_ok:

        flash(
            "Invalid email or password.",
            "error",
        )

        return safe_render(
            "login.html"
        )

    # ------------------------------------------------------------
    # LOGIN USER DIRECTLY
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
        "success",
    )

    next_url = request.args.get(
        "next",
        "",
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
    methods=["GET", "POST"],
)
def register():

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
            "register.html"
        )

    name = request.form.get(
        "name",
        "",
    ).strip()

    surname = request.form.get(
        "surname",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    password = request.form.get(
        "password",
        "",
    )

    confirm_password = request.form.get(
        "confirm_password",
        "",
    )

    if not all([
        name,
        surname,
        email,
        password,
        confirm_password,
    ]):

        flash(
            "Please fill in all fields.",
            "error",
        )

        return safe_render(
            "register.html"
        )

    if not basic_email_valid(email):

        flash(
            "Please enter a valid email address.",
            "error",
        )

        return safe_render(
            "register.html"
        )

    if not validate_email_with_mailboxlayer(
        email
    ):

        flash(
            "Please use a valid non-disposable email address.",
            "error",
        )

        return safe_render(
            "register.html"
        )

    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "error",
        )

        return safe_render(
            "register.html"
        )

    if len(password) < 6:

        flash(
            "Password must be at least 6 characters.",
            "error",
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
        (email,),
    ).fetchone()

    if existing_user:

        flash(
            "An account with this email already exists. Please log in instead.",
            "error",
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
            VALUES (?, ?, ?, ?, ?, 1, NULL, NULL, NULL)
            """,
            (
                name,
                surname,
                email,
                generate_password_hash(
                    password
                ),
                now,
            ),
        )

        db.commit()

    except sqlite3.IntegrityError:

        db.rollback()

        flash(
            "An account with this email already exists.",
            "error",
        )

        return redirect(
            url_for("login")
        )

    user_id = cursor.lastrowid

    # ------------------------------------------------------------
    # LOG THE NEW USER IN IMMEDIATELY
    # ------------------------------------------------------------

    session.clear()

    session["user_id"] = int(
        user_id
    )

    session["user_name"] = name

    session["user_surname"] = surname

    session["user_email"] = email

    session.modified = True

    flash(
        f"Account created successfully. Welcome, {name}.",
        "success",
    )

    return redirect(
        url_for("profile")
    )
    # ------------------------------------------------------------
    # EXISTING UNVERIFIED USER
    # ------------------------------------------------------------

    if (
        existing_user
        and not bool(
            existing_user["email_verified"]
        )
    ):

        session.clear()

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
            existing_user["name"],
        )

        flash(
            message,
            "success" if success else "error",
        )

        return redirect(
            url_for("verify_email")
        )

    # ------------------------------------------------------------
    # EXISTING VERIFIED USER
    # ------------------------------------------------------------

    if existing_user:

        flash(
            "An account with this email already exists. Please log in instead.",
            "error",
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
                now,
            ),
        )

        db.commit()

    except sqlite3.IntegrityError:

        db.rollback()

        flash(
            "An account with this email already exists.",
            "error",
        )

        return redirect(
            url_for("login")
        )

    user_id = cursor.lastrowid

    session.clear()

    session["pending_user_id"] = int(
        user_id
    )

    session["pending_email"] = email

    session["pending_name"] = name

    session.modified = True

    success, message = create_and_send_otp(
        user_id,
        email,
        name,
    )

    if not success:

        db.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,),
        )

        db.commit()

        session.clear()

        flash(
            message,
            "error",
        )

        return safe_render(
            "register.html"
        )

    flash(
        message,
        "success",
    )

    return redirect(
        url_for("verify_email")
    )


# ================================================================
# VERIFY EMAIL
# ================================================================





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
        "success",
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
        ),
    ).fetchone()

    if not user:

        session.clear()

        flash(
            "Your account could not be found.",
            "error",
        )

        return redirect(
            url_for("login")
        )

    return safe_render(
        "profile.html",
        user=user,
    )


# ================================================================
# HOME
# ================================================================

@app.route("/")
def home():

    return safe_render(
        "index.html"
    )


# Older templates may use url_for("index")
app.add_url_rule(
    "/",
    endpoint="index",
    view_func=home,
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
        facilities=FACILITIES,
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
        "school": 0,
    })

    api_url = (
        "https://api.aladhan.com/v1/timingsByCity/"
        + f"{today}?{params}"
    )

    try:

        req = Request(
            api_url,
            headers={
                "User-Agent":
                    "FSSSMC-Central-Mosque/1.0",
            },
        )

        with urlopen(
            req,
            timeout=10,
        ) as response:

            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        if payload.get("code") != 200:

            raise ValueError(
                "AlAdhan returned an unsuccessful response."
            )

        data = payload.get(
            "data",
            {},
        )

        timings = data.get(
            "timings",
            {},
        )

        date_info = data.get(
            "date",
            {},
        )

        prayer_times = {
            "Fajr": timings.get(
                "Fajr",
                "--:--",
            ),
            "Sunrise": timings.get(
                "Sunrise",
                "--:--",
            ),
            "Dhuhr": timings.get(
                "Dhuhr",
                "--:--",
            ),
            "Asr": timings.get(
                "Asr",
                "--:--",
            ),
            "Maghrib": timings.get(
                "Maghrib",
                "--:--",
            ),
            "Isha": timings.get(
                "Isha",
                "--:--",
            ),
        }

        return {
            "times": prayer_times,
            "date": date_info.get(
                "readable",
                today,
            ),
            "hijri": date_info.get(
                "hijri",
                {},
            ).get(
                "date",
                "",
            ),
            "location": "Lagos, Nigeria",
            "method": "AlAdhan — ISNA (Method 2)",
            "error": None,
        }

    except (
        URLError,
        HTTPError,
        TimeoutError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:

        app.logger.warning(
            "Prayer API request failed: %s",
            error,
        )

        return {
            "times": {
                "Fajr": "--:--",
                "Sunrise": "--:--",
                "Dhuhr": "--:--",
                "Asr": "--:--",
                "Maghrib": "--:--",
                "Isha": "--:--",
            },
            "date": today,
            "hijri": "",
            "location": "Lagos, Nigeria",
            "method": "AlAdhan — ISNA (Method 2)",
            "error": (
                "Live prayer-time service is temporarily unavailable."
            ),
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
        prayer_error=prayer_data["error"],
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
        facilities=FACILITIES,
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
        announcements=event_announcements,
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
                "",
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
                "",
            ),
            "status": person.get(
                "status",
                person.get(
                    "role",
                    "",
                ),
            ),
        }
        for person in PAST_EXECUTIVE
    ]

    registered_members = []

    try:

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
            ORDER BY created_at DESC, id DESC
            LIMIT 20
            """
        ).fetchall()

    except sqlite3.OperationalError as error:

        app.logger.warning(
            "Could not load contact members: %s",
            error,
        )

        try:
            get_db().rollback()
        except Exception:
            pass

    return safe_render(
        "contact.html",
        executive_members=EXECUTIVE_MEMBERS,
        past_executive=past_data,
        committees=committee_data,
        jummah_imams=jummah_data,
        posts=POSTS,
        registered_members=registered_members,
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
        WHERE COALESCE(published, 0) = 1
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    return safe_render(
        "announcements.html",
        announcements=rows,
    )


# ================================================================
# MEMBER REGISTRATION
# ================================================================

@app.route(
    "/members/register",
    methods=["GET", "POST"],
)
def member_register():

    if request.method == "GET":

        return safe_render(
            "member_register.html",
            posts=POSTS,
        )

    name = request.form.get(
        "name",
        "",
    ).strip()

    surname = request.form.get(
        "surname",
        "",
    ).strip()

    phone = request.form.get(
        "phone",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    address = request.form.get(
        "address",
        "",
    ).strip()

    post = request.form.get(
        "post",
        "",
    ).strip()

    notes = request.form.get(
        "notes",
        "",
    ).strip()

    if not all([
        name,
        surname,
        phone,
        email,
        address,
        post,
    ]):

        flash(
            "Please fill in all required fields.",
            "error",
        )

        return redirect(
            url_for("member_register")
        )

    if not basic_email_valid(email):

        flash(
            "Please enter a valid email address.",
            "error",
        )

        return redirect(
            url_for("member_register")
        )

    if post not in POSTS:

        flash(
            "Please select a valid occupation.",
            "error",
        )

        return redirect(
            url_for("member_register")
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM members
        WHERE LOWER(email) = ?
        """,
        (email,),
    ).fetchone()

    if existing:

        flash(
            "A member with this email already exists.",
            "error",
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
                now,
            ),
        )

        db.commit()

    except sqlite3.IntegrityError as error:

        db.rollback()

        app.logger.exception(
            "MEMBER REGISTRATION DATABASE ERROR: %s",
            error,
        )

        flash(
            "This member could not be registered.",
            "error",
        )

        return redirect(
            url_for("member_register")
        )

    flash(
        "Membership registration submitted successfully.",
        "success",
    )

    if account_authenticated():

        return redirect(
            url_for("profile")
        )

    return redirect(
        url_for("contact")
    )


app.add_url_rule(
    "/members/register",
    endpoint="register_member",
    view_func=member_register,
    methods=["GET", "POST"],
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

        kobo = value * Decimal("100")

        if kobo != kobo.to_integral_value():
            return None

        return int(kobo)

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):

        return None


def paystack_request(
    endpoint,
    method="GET",
    payload=None,
):

    if not PAYSTACK_SECRET_KEY:

        return (
            None,
            "PAYSTACK_SECRET_KEY is not configured.",
        )

    url = (
        PAYSTACK_BASE_URL
        + "/"
        + endpoint.lstrip("/")
    )

    headers = {
        "Authorization":
            "Bearer " + PAYSTACK_SECRET_KEY,
        "Content-Type":
            "application/json",
        "Cache-Control":
            "no-cache",
        "User-Agent":
            "FSSSMC-Central-Mosque/1.0",
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
        method=method,
    )

    try:

        with urlopen(
            req,
            timeout=30,
        ) as response:

            body = response.read().decode(
                "utf-8",
                errors="ignore",
            )

            parsed = json.loads(
                body
            )

            if not parsed.get(
                "status",
                False,
            ):

                message = parsed.get(
                    "message",
                    "Paystack rejected the request.",
                )

                app.logger.error(
                    "Paystack rejected request: %s",
                    message,
                )

                return (
                    None,
                    message,
                )

            return (
                parsed,
                None,
            )

    except HTTPError as error:

        try:

            body = error.read().decode(
                "utf-8",
                errors="ignore",
            )

            parsed = json.loads(
                body
            )

            message = parsed.get(
                "message",
                f"Paystack HTTP error {error.code}.",
            )

            app.logger.error(
                "Paystack HTTP %s: %s",
                error.code,
                message,
            )

            return (
                None,
                message,
            )

        except Exception:

            app.logger.exception(
                "Paystack HTTP error"
            )

            return (
                None,
                f"Paystack HTTP error {error.code}.",
            )

    except URLError as error:

        app.logger.error(
            "Could not connect to Paystack: %s",
            error,
        )

        return (
            None,
            "Could not connect to Paystack.",
        )

    except json.JSONDecodeError:

        app.logger.exception(
            "Paystack returned invalid JSON."
        )

        return (
            None,
            "Paystack returned an invalid response.",
        )

    except Exception as error:

        app.logger.exception(
            "Unexpected Paystack error"
        )

        return (
            None,
            str(error),
        )


def initialize_paystack_transaction(
    email,
    amount_kobo,
    reference,
    callback_url,
    metadata=None,
):

    payload = {
        "email": email,
        "amount": amount_kobo,
        "currency": PAYSTACK_CURRENCY,
        "reference": reference,
        "callback_url": callback_url,
    }

    if metadata:
        payload["metadata"] = metadata

    return paystack_request(
        "/transaction/initialize",
        "POST",
        payload,
    )


def verify_paystack_transaction(
    reference,
):

    return paystack_request(
        f"/transaction/verify/{reference}",
        "GET",
    )


def mark_donation_as_paid(
    reference,
    transaction=None,
):

    db = get_db()

    donation = db.execute(
        """
        SELECT *
        FROM donations
        WHERE payment_reference = ?
        """,
        (reference,),
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
                    0,
                )
            )

            currency = str(
                transaction.get(
                    "currency",
                    "",
                )
            ).upper()

            tx_reference = str(
                transaction.get(
                    "reference",
                    "",
                )
            ).strip()

            tx_status = str(
                transaction.get(
                    "status",
                    "",
                )
            ).lower()

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ):

            return False

        if (
            expected_kobo is None
            or received_kobo != expected_kobo
        ):

            return False

        if currency != PAYSTACK_CURRENCY:
            return False

        if tx_reference != reference:
            return False

        if tx_status != "success":
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
            reference,
        ),
    )

    db.commit()

    return True


# ================================================================
# PAYSTACK WEBHOOK
# ================================================================

@app.route(
    "/paystack/webhook",
    methods=["POST"],
)
def paystack_webhook():

    if not PAYSTACK_SECRET_KEY:
        return "", 200

    signature = request.headers.get(
        "X-Paystack-Signature",
        "",
    )

    payload = request.get_data()

    expected = hmac.new(
        PAYSTACK_SECRET_KEY.encode(
            "utf-8"
        ),
        payload,
        hashlib.sha512,
    ).hexdigest()

    if not signature:
        return "", 401

    if not hmac.compare_digest(
        signature,
        expected,
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
                {},
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
                    transaction,
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
    methods=["GET", "POST"],
)
def donate():

    user_email = session.get(
        "user_email",
        "",
    )

    user_name = session.get(
        "user_name",
        "",
    )

    if request.method == "GET":

        return safe_render(
            "donate.html",
            donation_purposes=DONATION_PURPOSES,
            user_email=user_email,
            user_name=user_name,
        )

    donor_name = request.form.get(
        "donor_name",
        "",
    ).strip()

    phone = request.form.get(
        "phone",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    amount = request.form.get(
        "amount",
        "",
    ).strip()

    purpose = request.form.get(
        "purpose",
        "",
    ).strip()

    notes = request.form.get(
        "notes",
        "",
    ).strip()

    if not donor_name:

        donor_name = (
            f"{user_name} "
        ).strip()

    if not email:
        email = user_email

    if not donor_name or not email:

        flash(
            "Please provide your name and email.",
            "error",
        )

        return redirect(
            url_for("donate")
        )

    if not basic_email_valid(email):

        flash(
            "Please provide a valid email address.",
            "error",
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
            "error",
        )

        return redirect(
            url_for("donate")
        )

    if purpose not in DONATION_PURPOSES:

        flash(
            "Please select a valid donation purpose.",
            "error",
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
                datetime.utcnow().isoformat(),
            ),
        )

        db.commit()

    except sqlite3.IntegrityError as error:

        db.rollback()

        app.logger.exception(
            "DONATION DATABASE ERROR: %s",
            error,
        )

        flash(
            "The donation could not be saved. Please try again.",
            "error",
        )

        return redirect(
            url_for("donate")
        )

    # ------------------------------------------------------------
    # PAYSTACK CALLBACK
    # ------------------------------------------------------------

    callback_url = url_for(
        "paystack_callback",
        _external=True,
    )

    metadata = {
        "donor_name": donor_name,
        "phone": phone,
        "purpose": purpose,
    }

    result, error = (
        initialize_paystack_transaction(
            email,
            amount_kobo,
            reference,
            callback_url,
            metadata,
        )
    )

    if error or not result:

        app.logger.error(
            "PAYSTACK INITIALIZATION FAILED: %s",
            error,
        )

        db.execute(
            """
            UPDATE donations
            SET payment_status = ?
            WHERE payment_reference = ?
            """,
            (
                "failed",
                reference,
            ),
        )

        db.commit()

        # Keep the detailed error in server logs,
        # but don't expose secret/configuration details
        # to the public user.
        flash(
            "Payment could not be initialized. Please try again.",
            "error",
        )

        return redirect(
            url_for("donate")
        )

    authorization_url = (
        result
        .get(
            "data",
            {},
        )
        .get(
            "authorization_url"
        )
    )

    if not authorization_url:

        app.logger.error(
            "Paystack response did not contain authorization_url: %s",
            result,
        )

        db.execute(
            """
            UPDATE donations
            SET payment_status = 'failed'
            WHERE payment_reference = ?
            """,
            (reference,),
        )

        db.commit()

        flash(
            "Paystack did not return a payment link. Please try again.",
            "error",
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
        "",
    ).strip()

    if not reference:

        flash(
            "No payment reference was provided.",
            "error",
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

        app.logger.error(
            "PAYSTACK VERIFICATION FAILED: %s",
            error,
        )

        flash(
            "Unable to verify the payment.",
            "error",
        )

        return redirect(
            url_for("donate")
        )

    transaction = result.get(
        "data",
        {},
    )

    if (
        result.get("status")
        and transaction.get("status") == "success"
    ):

        if mark_donation_as_paid(
            reference,
            transaction,
        ):

            flash(
                "Donation payment completed successfully. Thank you for your support.",
                "success",
            )

            if account_authenticated():

                return redirect(
                    url_for("profile")
                )

            return redirect(
                url_for("donate")
            )

        flash(
            "Payment verification failed because the transaction details did not match the donation record.",
            "error",
        )

        return redirect(
            url_for("donate")
        )

    flash(
        "The donation payment was not completed.",
        "error",
    )

    return redirect(
        url_for("donate")
    )


# ================================================================
# ADMIN LOGIN
# ================================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"],
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
        "",
    ).strip().lower()

    password = request.form.get(
        "password",
        "",
    )

    db = get_db()

    admin = db.execute(
        """
        SELECT *
        FROM admins
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    try:

        password_ok = bool(
            admin
            and check_password_hash(
                admin["password_hash"],
                password,
            )
        )

    except Exception:

        password_ok = False

    if not password_ok:

        flash(
            "Invalid administrator credentials.",
            "error",
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
        "success",
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
        "success",
    )

    return redirect(
        url_for("login")
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
        announcement_count=announcement_count,
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
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    return safe_render(
        "admin_members.html",
        members=members,
        posts=POSTS,
    )


@app.route(
    "/admin/members/add",
    methods=["GET", "POST"],
)
@admin_required
def admin_add_member():

    if request.method == "GET":

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS,
        )

    name = request.form.get(
        "name",
        "",
    ).strip()

    surname = request.form.get(
        "surname",
        "",
    ).strip()

    phone = request.form.get(
        "phone",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    address = request.form.get(
        "address",
        "",
    ).strip()

    post = request.form.get(
        "post",
        "",
    ).strip()

    notes = request.form.get(
        "notes",
        "",
    ).strip()

    if not all([
        name,
        surname,
        phone,
        email,
        address,
        post,
    ]):

        flash(
            "Please complete all required fields.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS,
        )

    if post not in POSTS:

        flash(
            "Please select a valid occupation.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS,
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM members
        WHERE LOWER(email) = ?
        """,
        (email,),
    ).fetchone()

    if existing:

        flash(
            "A member with this email already exists.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS,
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
                now,
            ),
        )

        db.commit()

    except sqlite3.IntegrityError:

        db.rollback()

        flash(
            "A member with this information already exists.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=None,
            posts=POSTS,
        )

    flash(
        "Member added successfully.",
        "success",
    )

    return redirect(
        url_for("admin_members")
    )


@app.route(
    "/admin/members/<int:member_id>/edit",
    methods=["GET", "POST"],
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
        (member_id,),
    ).fetchone()

    if not member:

        flash(
            "Member not found.",
            "error",
        )

        return redirect(
            url_for("admin_members")
        )

    if request.method == "GET":

        return safe_render(
            "admin_member_form.html",
            member=member,
            posts=POSTS,
        )

    name = request.form.get(
        "name",
        "",
    ).strip()

    surname = request.form.get(
        "surname",
        "",
    ).strip()

    phone = request.form.get(
        "phone",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip().lower()

    address = request.form.get(
        "address",
        "",
    ).strip()

    post = request.form.get(
        "post",
        "",
    ).strip()

    notes = request.form.get(
        "notes",
        "",
    ).strip()

    if not all([
        name,
        surname,
        phone,
        email,
        address,
        post,
    ]):

        flash(
            "Please complete all required fields.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=member,
            posts=POSTS,
        )

    if post not in POSTS:

        flash(
            "Please select a valid occupation.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=member,
            posts=POSTS,
        )

    duplicate = db.execute(
        """
        SELECT id
        FROM members
        WHERE LOWER(email) = ?
        AND id != ?
        """,
        (
            email,
            member_id,
        ),
    ).fetchone()

    if duplicate:

        flash(
            "Another member already uses this email.",
            "error",
        )

        return safe_render(
            "admin_member_form.html",
            member=member,
            posts=POSTS,
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
            member_id,
        ),
    )

    db.commit()

    flash(
        "Member updated successfully.",
        "success",
    )

    return redirect(
        url_for("admin_members")
    )


@app.route(
    "/admin/members/<int:member_id>/delete",
    methods=["GET", "POST"],
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
        (member_id,),
    )

    db.commit()

    flash(
        "Member deleted successfully.",
        "success",
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
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    return safe_render(
        "admin_donations.html",
        donations=donations,
    )


@app.route(
    "/admin/donations/<int:donation_id>/update",
    methods=["POST"],
)
@app.route(
    "/admin/donations/<int:donation_id>/status",
    methods=["POST"],
)
@admin_required
def admin_update_donation_status(
    donation_id
):

    status = request.form.get(
        "payment_status",
        "",
    ).strip().lower()

    if status not in {
        "pending",
        "paid",
        "failed",
        "cancelled",
    }:

        flash(
            "Invalid donation status.",
            "error",
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
            donation_id,
        ),
    )

    db.commit()

    flash(
        "Donation updated successfully.",
        "success",
    )

    return redirect(
        url_for("admin_donations")
    )


@app.route(
    "/admin/donations/<int:donation_id>/delete",
    methods=["GET", "POST"],
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
        (donation_id,),
    )

    db.commit()

    flash(
        "Donation deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin_donations")
    )


# ================================================================
# ADMIN ANNOUNCEMENTS
# ================================================================

@app.route(
    "/admin/announcements",
    methods=["GET", "POST"],
)
@admin_required
def admin_announcements():

    db = get_db()

    if request.method == "POST":

        title = request.form.get(
            "title",
            "",
        ).strip()

        body = request.form.get(
            "body",
            "",
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
                "error",
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
                now,
            ),
        )

        db.commit()

        flash(
            "Announcement created successfully.",
            "success",
        )

        return redirect(
            url_for("admin_announcements")
        )

    announcements = db.execute(
        """
        SELECT *
        FROM announcements
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()

    return safe_render(
        "admin_announcements.html",
        announcements=announcements,
    )


@app.route(
    "/admin/announcements/<int:announcement_id>/delete",
    methods=["GET", "POST"],
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
        (announcement_id,),
    )

    db.commit()

    flash(
        "Announcement deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin_announcements")
    )


# ================================================================
# HEALTH CHECK
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
        error,
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
                "0",
            ) == "1"
        ),
        use_reloader=False,
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                "5000",
            )
        ),
    )

