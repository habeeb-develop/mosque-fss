from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)

import sqlite3
import os
import json
import hashlib
import hmac
import uuid

from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from functools import wraps
from datetime import datetime
from decimal import Decimal, InvalidOperation

from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv


load_dotenv()


# ================================================================
# APP CONFIGURATION
# ================================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-this-secret-key"
).strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "database",
    "fss.db"
)

print("DATABASE LOCATION:", DATABASE)


# ================================================================
# PAYMENT / EMAIL API CONFIGURATION
# ================================================================

# Paystack
PAYSTACK_SECRET_KEY = os.environ.get(
    "PAYSTACK_SECRET_KEY",
    ""
).strip()

PAYSTACK_BASE_URL = "https://api.paystack.co"


# Mailboxlayer
MAILBOXLAYER_ACCESS_KEY = os.environ.get(
    "MAILBOXLAYER_ACCESS_KEY",
    ""
).strip()

MAILBOXLAYER_URL = "https://apilayer.net/api/check"



# ================================================================
# SITE DATA
# ================================================================

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


DONATION_PURPOSES = [
    "General Mosque Fund",
    "Zakat",
    "Sadaqah",
    "Building / Maintenance",
    "Education",
    "Food / Welfare",
    "Ramadan",
    "Other"
]


EXECUTIVE_MEMBERS = [
    {
        "name": "Muritala Adekunle Balogun",
        "role": "Amir"
    },
    {
        "name": "Mustapha Motilola Alli",
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
    },
]


PAST_EXECUTIVE = [
    {
        "name": "Late Alhaji Musliu Arinola",
        "role": "Past Executive",
        "status": "Deceased"
    },
    {
        "name": "Late Alhaji Ayoade Musibau Adetunji",
        "role": "Past Executive",
        "status": "Deceased"
    },
]


COMMITTEES = {
    "Financial Committee": [
        ("Abdul Ganiyu Olayinka Dabiri", ""),
        ("Lukman Badiru", ""),
        ("Abdul Gafar Wale Ajala", ""),
        ("Muhammed Bello", ""),
        ("Abdul Fatai Bakare", "Change of location"),
        ("Monsuru Oyinlola", ""),
        ("Sikiru Bankole", ""),
        ("Ibikunle Rasaq Adekunmi Abu Zaid", ""),
    ],

    "Infrastructure / Project Committee": [
        ("Balogun Muritala Adekunle", ""),
        ("Dabiri Ganiyu Olayinka", ""),
        ("Arinola Musliu", "Deceased"),
        ("Ayoade Musibau Adetunji", "Deceased"),
        ("Engr. Sanni Ismail", ""),
    ],

    "Da'awa Committee": [
        ("Imam Alli Mustapha", ""),
        ("Abimbola Ishaq Aderemi", ""),
        ("Badiru Lukman", ""),
        ("Abdul Lateef", ""),
        ("Ustadh Abdul Ganny Ejalonibu", ""),
        ("Ustadh Abu Abdul Rahman Opeyemi", ""),
        ("Ibikunle Rasaq Adekunmi Abu Zaid", ""),
        ("Ustadh Abdul Rasheed Adebayo", "Relocation"),
    ],

    "Welfare Committee": [
        ("Abdul Lateef Usman", ""),
        ("Hassan Muhammad Bello", ""),
        ("Muhammed Bello", ""),
        ("Demola Adeduntan", ""),
    ],

    "Education Committee": [
        ("Abimbola Ishaq Aderemi", ""),
        ("Prof. Aderolu Zaid", ""),
        ("Ustadh Abdul Ganny Ejalonibu", ""),
        ("Balogun Muritala Adekunle", ""),
    ],

    "Ramadan Planning Committee": [
        ("Hassan Muhammad Bello", ""),
        ("Abdul Lateef Usman", ""),
        ("Lukman Badiru", ""),
        ("Monsuru Oyinlola", ""),
        ("Muhammed Bello", ""),
    ],

    "Masjid Maintenance Committee": [
        ("Ajao Ibrahim", ""),
        ("Ibikunle Rasaq Adekunmi", ""),
        ("Qozeem Adebisi", ""),
    ],
}


JUMMAH_IMAMS = [
    "Ustadh Abdul Granny Adebayo Ejalonibu",
    "Opeyemi Abu Abdul Rahman",
    "Ustadh Abdul Rasheed Adebayo Abu Qoonitah",
    "Ustadh Abdul Azeez Abu Nasir",
    "Ustadh Abu Abdullah",
    "Ustadh Abu Abidah",
]


FACILITIES = [
    (
        "Main Prayer Hall",
        "A dedicated space for congregational worship and daily prayers."
    ),
    (
        "Women’s Prayer Area",
        "A dedicated prayer area for sisters and women in the community."
    ),
    (
        "Islamic Library",
        "A space for Qur’anic, Islamic and educational materials."
    ),
    (
        "Ablution Facilities",
        "Facilities provided to support worshippers before prayer."
    ),
    (
        "Classrooms",
        "Learning spaces for Islamic education and community programmes."
    ),
    (
        "Meeting Halls",
        "Spaces for meetings, planning and community activities."
    ),
]


# ================================================================
# DATABASE
# ================================================================

def get_db():

    if "db" not in g:

        os.makedirs(
            os.path.dirname(DATABASE),
            exist_ok=True
        )

        g.db = sqlite3.connect(
            DATABASE,
            timeout=30,
            check_same_thread=False
        )

        g.db.row_factory = sqlite3.Row

        # Foreign keys
        g.db.execute(
            "PRAGMA foreign_keys = ON"
        )

        # Wait up to 30 seconds if another connection
        # is temporarily writing to the database.
        g.db.execute(
            "PRAGMA busy_timeout = 30000"
        )

        # WAL allows readers and writers to work together
        # more smoothly than the default journal mode.
        try:
            g.db.execute(
                "PRAGMA journal_mode = WAL"
            )
        except sqlite3.OperationalError:
            pass

    return g.db


@app.teardown_appcontext
def close_db(exception=None):

    db = g.pop("db", None)

    if db is not None:

        try:
            if exception is not None:
                db.rollback()
        except sqlite3.Error:
            pass

        try:
            db.close()
        except sqlite3.Error:
            pass


def init_db():

    db = get_db()

    try:

        try:
            db.execute(
                "PRAGMA journal_mode = WAL"
            )
        except sqlite3.OperationalError:
            pass

        db.execute(
            "PRAGMA foreign_keys = ON"
        )

        db.execute(
            "PRAGMA busy_timeout = 30000"
        )

        # --------------------------------------------------------
        # CREATE TABLES
        # --------------------------------------------------------

        db.executescript("""

            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                address TEXT NOT NULL,
                post TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                amount REAL NOT NULL CHECK(amount > 0),
                purpose TEXT NOT NULL,
                payment_reference TEXT,
                payment_method TEXT DEFAULT 'Manual',
                payment_status TEXT DEFAULT 'Pending',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                paid_at TEXT
            );

            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                published INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_members_phone
            ON members(phone);

            CREATE INDEX IF NOT EXISTS idx_members_post
            ON members(post);

            CREATE INDEX IF NOT EXISTS idx_donations_status
            ON donations(payment_status);

            CREATE INDEX IF NOT EXISTS idx_donations_created
            ON donations(created_at);

            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_donations_reference
            ON donations(payment_reference)
            WHERE payment_reference IS NOT NULL;

        """)

        # --------------------------------------------------------
        # USER EMAIL VERIFICATION COLUMN
        user_columns = db.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

        column_names = {
            column["name"]
            for column in user_columns
        }

        if "email_verified" not in column_names:
            db.execute(
                """
                ALTER TABLE users
                ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0
                """
            )

        # CREATE DEFAULT ADMIN
        # --------------------------------------------------------

        admin_email = os.environ.get(
            "ADMIN_EMAIL",
            "admin@fsssmc.org"
        ).strip().lower()

        admin_password = os.environ.get(
            "ADMIN_PASSWORD",
            "ChangeThisPassword123!"
        )

        admin = db.execute(
            """
            SELECT id
            FROM admins
            WHERE email = ?
            """,
            (admin_email,)
        ).fetchone()

        if admin is None:

            db.execute(
                """
                INSERT INTO admins
                (email, password_hash)
                VALUES (?, ?)
                """,
                (
                    admin_email,
                    generate_password_hash(admin_password)
                )
            )

        db.commit()

    except sqlite3.Error:

        try:
            db.rollback()
        except sqlite3.Error:
            pass

        raise


# ================================================================
# TEMPLATE GLOBALS
# ================================================================

@app.context_processor
def inject_globals():

    return {
        "site_name": "FSSSMC Central Mosque",
        "current_year": datetime.now().year,
        "executive_members": EXECUTIVE_MEMBERS,
        "past_executive": PAST_EXECUTIVE,
        "committees": COMMITTEES,
        "jummah_imams": JUMMAH_IMAMS,
        "facilities": FACILITIES,
        "logged_in": account_authenticated() if "account_authenticated" in globals() else False,
        "admin_logged_in": bool(session.get("admin_id")),
        "user_logged_in": bool(session.get("user_id")),
    }


# ================================================================
# MAILBOXLAYER EMAIL VALIDATION
# ================================================================

def validate_email_with_mailboxlayer(email):

    email = (email or "").strip().lower()

    if not email:
        return False

    # Always perform a basic syntax check first.
    if (
        "@" not in email
        or email.startswith("@")
        or email.endswith("@")
        or "." not in email.split("@")[-1]
    ):
        return False

    # If no API key has been configured, allow the
    # basic syntax check to work during local development.
    if not MAILBOXLAYER_ACCESS_KEY:
        print(
            "MAILBOXLAYER_ACCESS_KEY is not configured. "
            "Using basic email validation."
        )
        return True

    params = urlencode({
        "access_key": MAILBOXLAYER_ACCESS_KEY,
        "email": email,
    })

    api_url = f"{MAILBOXLAYER_URL}?{params}"

    try:

        req = Request(
            api_url,
            headers={
                "User-Agent": "FSSSMC-Central-Mosque/1.0"
            }
        )

        with urlopen(
            req,
            timeout=8
        ) as response:

            payload = json.loads(
                response.read().decode("utf-8")
            )

        # Mailboxlayer can return an error object.
        if payload.get("success") is False:

            print(
                "Mailboxlayer returned an API error:",
                payload.get("error")
            )

            # Fail open, like the previous FSSSMC setup.
            return True

        format_valid = payload.get(
            "format_valid",
            True
        )

        if not format_valid:
            return False

        # Reject disposable addresses when the API
        # explicitly identifies them.
        disposable = payload.get(
            "disposable",
            False
        )

        if disposable is True:
            return False

        return True

    except (
        URLError,
        HTTPError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError
    ) as error:

        print(
            "Mailboxlayer validation error:",
            error
        )

        # Fail open so a temporary Mailboxlayer outage
        # does not prevent legitimate users from registering.
        return True

    except Exception as error:

        print(
            "Unexpected Mailboxlayer error:",
            error
        )

        return True


# ================================================================
# PAYSTACK HELPERS
# ================================================================

def generate_payment_reference():

    return (
        "FSSMC-"
        + datetime.now().strftime("%Y%m%d%H%M%S")
        + "-"
        + uuid.uuid4().hex[:8].upper()
    )


def naira_to_kobo(amount):

    try:

        decimal_amount = Decimal(
            str(amount)
        ).quantize(
            Decimal("0.01")
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError
    ):

        raise ValueError(
            "Invalid amount."
        )

    if decimal_amount <= 0:
        raise ValueError(
            "Amount must be greater than zero."
        )

    return int(
        decimal_amount * Decimal("100")
    )


def paystack_request(
    method,
    endpoint,
    data=None
):

    if not PAYSTACK_SECRET_KEY:

        raise RuntimeError(
            "PAYSTACK_SECRET_KEY is not configured."
        )

    url = (
        PAYSTACK_BASE_URL
        + endpoint
    )

    headers = {
        "Authorization":
            f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type":
            "application/json",
        "User-Agent":
            "FSSSMC-Central-Mosque/1.0"
    }

    body = None

    if data is not None:

        body = json.dumps(
            data
        ).encode("utf-8")

    req = Request(
        url,
        data=body,
        headers=headers,
        method=method
    )

    with urlopen(
        req,
        timeout=15
    ) as response:

        response_body = response.read().decode(
            "utf-8"
        )

        return json.loads(
            response_body
        )


def initialize_paystack_transaction(
    email,
    amount_kobo,
    reference,
    donor_name,
    purpose
):

    callback_url = url_for(
        "paystack_callback",
        _external=True
    )

    first_name = donor_name
    last_name = ""

    parts = donor_name.split()

    if len(parts) > 1:

        first_name = parts[0]
        last_name = " ".join(
            parts[1:]
        )

    payload = {
        "email": email,
        "amount": str(amount_kobo),
        "currency": "NGN",
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {
            "donor_name": donor_name,
            "purpose": purpose,
            "cancel_action": url_for(
                "donate",
                _external=True
            ),
            "custom_fields": [
                {
                    "display_name": "Donor Name",
                    "variable_name": "donor_name",
                    "value": donor_name
                },
                {
                    "display_name": "Donation Purpose",
                    "variable_name": "purpose",
                    "value": purpose
                }
            ]
        }
    }

    response = paystack_request(
        "POST",
        "/transaction/initialize",
        payload
    )

    if not response.get("status"):

        raise RuntimeError(
            response.get(
                "message",
                "Paystack could not initialize the payment."
            )
        )

    data = response.get(
        "data",
        {}
    )

    authorization_url = data.get(
        "authorization_url"
    )

    returned_reference = data.get(
        "reference"
    )

    if not authorization_url:

        raise RuntimeError(
            "Paystack did not return a payment URL."
        )

    return {
        "authorization_url":
            authorization_url,
        "reference":
            returned_reference or reference
    }


def verify_paystack_transaction(reference):

    if not reference:

        return None

    response = paystack_request(
        "GET",
        "/transaction/verify/"
        + reference
    )

    if not response.get("status"):

        return None

    return response.get(
        "data"
    )


def mark_donation_as_paid(
    reference,
    paystack_data
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

    if donation is None:
        return False

    if donation["payment_status"] == "Paid":
        return True

    try:

        paid_amount_kobo = int(
            paystack_data.get(
                "amount",
                0
            )
        )

        expected_amount_kobo = naira_to_kobo(
            donation["amount"]
        )

        if (
            paid_amount_kobo
            != expected_amount_kobo
        ):

            print(
                "Paystack amount mismatch:",
                reference
            )

            return False

        currency = paystack_data.get(
            "currency",
            ""
        )

        if currency != "NGN":

            print(
                "Unexpected Paystack currency:",
                currency
            )

            return False

        status = paystack_data.get(
            "status"
        )

        if status != "success":
            return False

        db.execute(
            """
            UPDATE donations
            SET
                payment_status = 'Paid',
                payment_method = 'Paystack',
                paid_at = CURRENT_TIMESTAMP
            WHERE payment_reference = ?
            """,
            (reference,)
        )

        db.commit()

        return True

    except (
        ValueError,
        TypeError,
        sqlite3.Error
    ) as error:

        print(
            "Unable to mark donation as paid:",
            error
        )

        try:
            db.rollback()
        except sqlite3.Error:
            pass

        return False


# ================================================================
# PAYSTACK WEBHOOK
# ================================================================

@app.route(
    "/paystack/webhook",
    methods=["POST"]
)
def paystack_webhook():

    if not PAYSTACK_SECRET_KEY:

        return (
            "Paystack not configured.",
            503
        )

    signature = request.headers.get(
        "x-paystack-signature",
        ""
    )

    raw_body = request.get_data()

    expected_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512
    ).hexdigest()

    if not signature:

        return (
            "Missing signature.",
            400
        )

    if not hmac.compare_digest(
        signature,
        expected_signature
    ):

        return (
            "Invalid signature.",
            400
        )

    try:

        payload = request.get_json(
            silent=True
        )

        if not payload:

            return (
                "Invalid JSON.",
                400
            )

        event = payload.get(
            "event"
        )

        if event == "charge.success":

            data = payload.get(
                "data",
                {}
            )

            reference = data.get(
                "reference"
            )

            if reference:

                mark_donation_as_paid(
                    reference,
                    data
                )

        return (
            "OK",
            200
        )

    except Exception as error:

        print(
            "Paystack webhook error:",
            error
        )

        return (
            "Webhook error.",
            500
        )


# ================================================================
# ADMIN AUTHENTICATION
# ================================================================

def admin_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if not session.get("admin_id"):

            flash(
                "Please log in as administrator.",
                "error"
            )

            return redirect(
                url_for("admin_login")
            )

        return view(*args, **kwargs)

    return wrapped_view


# ================================================================
# PUBLIC PAGES
# ================================================================

@app.route("/")
def home():

    db = get_db()

    announcements = db.execute("""
        SELECT *
        FROM announcements
        WHERE published = 1
        ORDER BY created_at DESC
        LIMIT 3
    """).fetchall()

    return render_template(
        "index.html",
        announcements=announcements
    )


@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# ================================================================
# PRAYER TIMES
# ================================================================

def get_prayer_times():

    today = datetime.now().strftime(
        "%d-%m-%Y"
    )

    params = urlencode({
        "city": "Lagos",
        "country": "Nigeria",
        "method": 2,
    })

    api_url = (
        f"https://api.aladhan.com/v1/"
        f"timingsByCity/{today}?{params}"
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
            timeout=8
        ) as response:

            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
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

        wanted = [
            "Fajr",
            "Sunrise",
            "Dhuhr",
            "Asr",
            "Maghrib",
            "Isha"
        ]

        prayer_times = {
            key: timings.get(
                key,
                "--:--"
            )
            for key in wanted
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
            "location":
                "Lagos, Nigeria",
            "method":
                "AlAdhan calculation method 2",
            "error": None,
        }

    except (
        URLError,
        HTTPError,
        TimeoutError,
        ValueError,
        KeyError
    ):

        return {
            "times": {},
            "date": today,
            "hijri": "",
            "location":
                "Lagos, Nigeria",
            "method":
                "AlAdhan calculation method 2",
            "error":
                "Prayer times are temporarily unavailable. "
                "Please try again shortly.",
        }


@app.route("/prayer")
def prayer():

    prayer_data = get_prayer_times()

    return render_template(
        "prayer.html",
        prayer_times=
            prayer_data["times"],
        prayer_date=
            prayer_data["date"],
        hijri_date=
            prayer_data["hijri"],
        location=
            prayer_data["location"],
        prayer_method=
            prayer_data["method"],
        prayer_error=
            prayer_data["error"],
    )


@app.route("/services")
def services():

    return render_template(
        "services.html"
    )


@app.route("/events")
def events():

    db = get_db()

    announcements = db.execute("""
        SELECT *
        FROM announcements
        WHERE published = 1
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
        "events.html",
        announcements=announcements
    )


@app.route("/learn")
def learn():

    return render_template(
        "learn.html"
    )


@app.route("/get-involved")
def get_involved():

    return render_template(
        "get-involved.html"
    )


@app.route("/contact")
def contact():

    db = get_db()

    registered_members = db.execute("""
        SELECT *
        FROM members
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
        "contact.html",
        posts=POSTS,
        registered_members=
            registered_members,
    )


@app.route("/announcements")
def announcements():

    db = get_db()

    rows = db.execute("""
        SELECT *
        FROM announcements
        WHERE published = 1
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
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
def register_member():

    if request.method == "GET":
        flash(
            "Please complete the membership form on the Contact page.",
            "info"
        )
        return redirect(url_for("contact") + "#membership")

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
    ).strip()

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

    if (
        not name
        or not surname
        or not phone
        or not address
        or not post
    ):

        flash(
            "Please fill in all required member fields.",
            "error"
        )

        return redirect(
            url_for("contact")
            + "#membership"
        )

    if post not in POSTS:

        flash(
            "Invalid profession selected.",
            "error"
        )

        return redirect(
            url_for("contact")
            + "#membership"
        )

    if email:

        if not validate_email_with_mailboxlayer(
            email
        ):

            flash(
                "Please provide a valid email address.",
                "error"
            )

            return redirect(
                url_for("contact")
                + "#membership"
            )

    db = get_db()

    try:

        db.execute("""
            INSERT INTO members
            (
                name,
                surname,
                phone,
                email,
                address,
                post,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            surname,
            phone,
            email,
            address,
            post,
            notes
        ))

        db.commit()

    except sqlite3.Error:

        db.rollback()

        flash(
            "Unable to save the membership information. "
            "Please try again.",
            "error"
        )

        return redirect(
            url_for("contact")
            + "#membership"
        )

    flash(
        "Your membership information has been submitted successfully.",
        "success"
    )

    return redirect(
        url_for("contact")
        + "#membership"
    )



# ================================================================
# ================================================================
# ACCOUNT AUTHENTICATION
# ================================================================

def account_authenticated():
    return bool(
        session.get("user_id")
        or session.get("admin_id")
    )


# ================================================================
# LOGIN GATE
# ================================================================

@app.before_request
def require_login_for_website():

    # Public website pages and authentication pages.
    public_endpoints = {
        "home",
        "about",
        "prayer",
        "services",
        "events",
        "learn",
        "get_involved",
        "contact",
        "announcements",
        "login",
        "register",
        "logout",
        "admin_login",
        "admin_logout",
        "paystack_webhook",
        "paystack_callback",
        "static",
        "page_not_found",
        "internal_error",
    }

    if request.endpoint in public_endpoints:
        return None

    # Profile requires a normal user account.
    if request.endpoint == "profile":
        if session.get("user_id"):
            return None

        flash(
            "Please sign in to view your profile.",
            "error"
        )

        return redirect(url_for("login"))

    # Admin routes are protected by @admin_required.
    # Other non-public website actions, including donations and
    # membership registration, require a logged-in user.
    if request.endpoint and request.endpoint.startswith("admin_"):
        return None

    if session.get("user_id") or session.get("admin_id"):
        return None

    flash(
        "Please sign in to continue.",
        "error"
    )

    return redirect(url_for("login"))


# ================================================================
# USER REGISTRATION
# ================================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if account_authenticated():
        if session.get("admin_id"):
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("profile"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        surname = request.form.get("surname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not surname or not email or not password:
            flash("Please complete all required fields.", "error")
            return redirect(url_for("register"))

        if not validate_email_with_mailboxlayer(email):
            flash("Please enter a valid email address.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        db = get_db()

        existing = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            flash(
                "An account with that email already exists. Please log in instead.",
                "error"
            )
            return redirect(url_for("login"))

        try:
            cursor = db.execute(
                """
                INSERT INTO users
                (
                    name,
                    surname,
                    email,
                    password_hash,
                    email_verified
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    name,
                    surname,
                    email,
                    generate_password_hash(password),
                )
            )
            db.commit()

        except sqlite3.IntegrityError:
            db.rollback()
            flash(
                "An account with that email already exists. Please log in instead.",
                "error"
            )
            return redirect(url_for("login"))

        except sqlite3.Error as error:
            db.rollback()
            print("Registration database error:", error)
            flash(
                "Unable to create your account right now. Please try again.",
                "error"
            )
            return redirect(url_for("register"))

        # Registration is complete immediately. No email verification
        # or SMTP message is required.
        session.clear()
        session["user_id"] = cursor.lastrowid
        session["user_name"] = name
        session["user_surname"] = surname
        session["user_email"] = email

        flash(
            f"Account created successfully. Welcome, {name}.",
            "success"
        )

        return redirect(url_for("profile"))

    return render_template("register.html")


# ================================================================
# LOGIN
# ================================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("user_id"):
        return redirect(url_for("profile"))

    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash(
                "Please enter your email and password.",
                "error"
            )
            return redirect(url_for("login"))

        db = get_db()

        # --------------------------------------------------------
        # ADMIN LOGIN
        # --------------------------------------------------------
        # Admin logs in directly. No OTP is required.
        admin = db.execute(
            "SELECT * FROM admins WHERE email = ?",
            (email,)
        ).fetchone()

        if admin:
            if check_password_hash(
                admin["password_hash"],
                password
            ):
                session.clear()
                session["admin_id"] = admin["id"]
                session["admin_email"] = admin["email"]

                flash(
                    "Welcome to the FSSSMC admin dashboard.",
                    "success"
                )

                return redirect(url_for("admin_dashboard"))

            flash(
                "Invalid email or password.",
                "error"
            )
            return redirect(url_for("login"))

        # --------------------------------------------------------
        # NORMAL USER LOGIN
        # --------------------------------------------------------
        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user is None:
            flash(
                "Invalid email or password.",
                "error"
            )
            return redirect(url_for("login"))

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            flash(
                "Invalid email or password.",
                "error"
            )
            return redirect(url_for("login"))

        next_url = request.form.get("next", "").strip()
        if not next_url:
            next_url = request.args.get("next", "").strip()

        if (
            not next_url
            or not next_url.startswith("/")
            or next_url.startswith("//")
        ):
            next_url = url_for("profile")

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_surname"] = user["surname"]
        session["user_email"] = user["email"]

        flash(
            f"Welcome back, {user['name']}.",
            "success"
        )

        return redirect(next_url)

    return render_template("login.html")


# USER LOGOUT
# ================================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# ================================================================
# USER PROFILE
# ================================================================

@app.route("/profile")
def profile():

    if not session.get("user_id"):

        flash(
            "Please sign in to view your profile.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    db = get_db()

    user = db.execute(
        """
        SELECT
            id,
            name,
            surname,
            email,
            created_at
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    if user is None:

        session.clear()

        return redirect(
            url_for("login")
        )

    return render_template(
        "profile.html",
        user=user
    )


# ================================================================
# PUBLIC DONATIONS + PAYSTACK
# ================================================================

@app.route(
    "/donate",
    methods=["GET", "POST"]
)
def donate():

    if request.method == "POST":

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

        amount_text = request.form.get(
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

        # --------------------------------------------------------
        # REQUIRED FIELDS
        # --------------------------------------------------------

        if (
            not donor_name
            or not amount_text
            or not purpose
            or not email
        ):

            flash(
                "Please fill in your name, email, amount and purpose.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        # --------------------------------------------------------
        # MAILBOXLAYER
        # --------------------------------------------------------

        if not validate_email_with_mailboxlayer(
            email
        ):

            flash(
                "Please provide a valid email address.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        try:

            amount_decimal = Decimal(
                amount_text
            ).quantize(
                Decimal("0.01")
            )

            if amount_decimal <= 0:
                raise ValueError

            amount_kobo = naira_to_kobo(
                amount_decimal
            )

            amount = float(
                amount_decimal
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            flash(
                "Please enter a valid donation amount.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        # --------------------------------------------------------
        # PURPOSE
        # --------------------------------------------------------

        if purpose not in DONATION_PURPOSES:

            flash(
                "Invalid donation purpose.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        # --------------------------------------------------------
        # PAYSTACK KEY
        # --------------------------------------------------------

        if not PAYSTACK_SECRET_KEY:

            flash(
                "Online payment is not configured yet. "
                "Please contact the mosque administrator.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        db = get_db()

        reference = generate_payment_reference()

        # --------------------------------------------------------
        # SAVE PENDING DONATION FIRST
        # --------------------------------------------------------

        try:

            db.execute("""
                INSERT INTO donations
                (
                    donor_name,
                    phone,
                    email,
                    amount,
                    purpose,
                    payment_reference,
                    payment_method,
                    payment_status,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                donor_name,
                phone,
                email,
                amount,
                purpose,
                reference,
                "Paystack",
                "Pending",
                notes
            ))

            db.commit()

        except sqlite3.Error:

            db.rollback()

            flash(
                "The donation could not be started right now. "
                "Please try again.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        # --------------------------------------------------------
        # INITIALIZE PAYSTACK
        # --------------------------------------------------------

        try:

            payment = initialize_paystack_transaction(
                email=email,
                amount_kobo=amount_kobo,
                reference=reference,
                donor_name=donor_name,
                purpose=purpose
            )

            returned_reference = payment[
                "reference"
            ]

            # If Paystack returns a different reference,
            # update our local record.
            if returned_reference != reference:

                db.execute(
                    """
                    UPDATE donations
                    SET payment_reference = ?
                    WHERE id = (
                        SELECT id
                        FROM donations
                        WHERE payment_reference = ?
                        LIMIT 1
                    )
                    """,
                    (
                        returned_reference,
                        reference
                    )
                )

                db.commit()

            return redirect(
                payment["authorization_url"]
            )

        except (
            URLError,
            HTTPError,
            TimeoutError,
            ValueError,
            RuntimeError,
            json.JSONDecodeError
        ) as error:

            print(
                "Paystack initialization error:",
                error
            )

            flash(
                "Paystack could not start the payment. "
                "Please try again.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

        except Exception as error:

            print(
                "Unexpected Paystack error:",
                error
            )

            flash(
                "Unable to start the payment right now. "
                "Please try again.",
                "error"
            )

            return redirect(
                url_for("donate")
            )

    return render_template(
        "donate.html",
        donation_purposes=
            DONATION_PURPOSES
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
            "No Paystack transaction reference was received.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    db = get_db()

    donation = db.execute(
        """
        SELECT *
        FROM donations
        WHERE payment_reference = ?
        """,
        (reference,)
    ).fetchone()

    if donation is None:

        flash(
            "Donation record not found.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    # Already paid, for example through webhook.
    if donation["payment_status"] == "Paid":

        flash(
            "Your donation was received successfully. "
            "Thank you.",
            "success"
        )

        return redirect(
            url_for("donate")
        )

    try:

        payment_data = verify_paystack_transaction(
            reference
        )

    except (
        URLError,
        HTTPError,
        TimeoutError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError
    ) as error:

        print(
            "Paystack verification error:",
            error
        )

        flash(
            "We could not verify the payment yet. "
            "Please try again shortly.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    except Exception as error:

        print(
            "Unexpected Paystack verification error:",
            error
        )

        flash(
            "We could not verify the payment yet. "
            "Please try again shortly.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    if not payment_data:

        flash(
            "Paystack could not verify this transaction.",
            "error"
        )

        return redirect(
            url_for("donate")
        )

    payment_status = payment_data.get(
        "status"
    )

    if payment_status == "success":

        paid = mark_donation_as_paid(
            reference,
            payment_data
        )

        if paid:

            flash(
                "Donation payment successful. "
                "JazakAllahu Khairan.",
                "success"
            )

        else:

            flash(
                "The payment was returned as successful, "
                "but we could not confirm the donation amount. "
                "Please contact the mosque administrator.",
                "error"
            )

    elif payment_status in (
        "failed",
        "abandoned",
        "reversed"
    ):

        db.execute(
            """
            UPDATE donations
            SET payment_status = ?
            WHERE payment_reference = ?
            """,
            (
                "Cancelled",
                reference
            )
        )

        db.commit()

        flash(
            "The Paystack payment was not completed.",
            "error"
        )

    else:

        flash(
            "The payment is still being processed. "
            "Please check again shortly.",
            "success"
        )

    return redirect(
        url_for("donate")
    )


# ================================================================
# ADMIN LOGIN
# ================================================================

@app.route("/admin/login")
def admin_login():

    return redirect(
        url_for("login")
    )


@app.route("/admin/logout")
def admin_logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


# ================================================================
# ADMIN DASHBOARD
# ================================================================

@app.route("/admin")
@app.route("/admin/")
@admin_required
def admin_dashboard():

    db = get_db()

    # ------------------------------------------------------------
    # TOTAL MEMBERS
    # ------------------------------------------------------------

    total_members = db.execute("""
        SELECT COUNT(*) AS total
        FROM members
    """).fetchone()["total"]

    # ------------------------------------------------------------
    # PAID DONATION AMOUNT
    # ------------------------------------------------------------

    total_donations = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM donations
        WHERE payment_status = 'Paid'
    """).fetchone()["total"]

    # ------------------------------------------------------------
    # PENDING DONATIONS
    # ------------------------------------------------------------

    pending_donations = db.execute("""
        SELECT COUNT(*) AS total
        FROM donations
        WHERE payment_status = 'Pending'
    """).fetchone()["total"]

    # ------------------------------------------------------------
    # ANNOUNCEMENTS
    # ------------------------------------------------------------

    total_announcements = db.execute("""
        SELECT COUNT(*) AS total
        FROM announcements
    """).fetchone()["total"]

    # ------------------------------------------------------------
    # DONATION COUNTS
    # ------------------------------------------------------------

    paid_donations_count = db.execute("""
        SELECT COUNT(*) AS total
        FROM donations
        WHERE payment_status = 'Paid'
    """).fetchone()["total"]

    pending_donations_count = db.execute("""
        SELECT COUNT(*) AS total
        FROM donations
        WHERE payment_status = 'Pending'
    """).fetchone()["total"]

    cancelled_donations_count = db.execute("""
        SELECT COUNT(*) AS total
        FROM donations
        WHERE payment_status = 'Cancelled'
    """).fetchone()["total"]

    # ------------------------------------------------------------
    # DONATION AMOUNTS
    # ------------------------------------------------------------

    pending_amount = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM donations
        WHERE payment_status = 'Pending'
    """).fetchone()["total"]

    cancelled_amount = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM donations
        WHERE payment_status = 'Cancelled'
    """).fetchone()["total"]

    # ------------------------------------------------------------
    # RECENT MEMBERS
    # ------------------------------------------------------------

    recent_members = db.execute("""
        SELECT
            id,
            name,
            surname,
            phone,
            email,
            post,
            created_at
        FROM members
        ORDER BY created_at DESC
        LIMIT 6
    """).fetchall()

    # ------------------------------------------------------------
    # MEMBER POST BREAKDOWN
    # ------------------------------------------------------------

    member_posts = db.execute("""
        SELECT
            post,
            COUNT(*) AS total
        FROM members
        GROUP BY post
        ORDER BY total DESC
    """).fetchall()

    # ------------------------------------------------------------
    # RECENT DONATIONS
    # ------------------------------------------------------------

    recent_donations = db.execute("""
        SELECT
            id,
            donor_name,
            amount,
            purpose,
            payment_method,
            payment_status,
            created_at
        FROM donations
        ORDER BY created_at DESC
        LIMIT 6
    """).fetchall()

    # ------------------------------------------------------------
    # RECENT ANNOUNCEMENTS
    # ------------------------------------------------------------

    recent_announcements = db.execute("""
        SELECT
            id,
            title,
            published,
            created_at
        FROM announcements
        ORDER BY created_at DESC
        LIMIT 5
    """).fetchall()

    return render_template(
        "admin/dashboard.html",

        member_count=total_members,
        paid_donations=total_donations,
        announcement_count=total_announcements,

        total_members=
            total_members,

        total_donations=
            total_donations,

        pending_donations=
            pending_donations,

        total_announcements=
            total_announcements,

        paid_donations_count=
            paid_donations_count,

        pending_donations_count=
            pending_donations_count,

        cancelled_donations_count=
            cancelled_donations_count,

        pending_amount=
            pending_amount,

        cancelled_amount=
            cancelled_amount,

        recent_members=
            recent_members,

        member_posts=
            member_posts,

        recent_donations=
            recent_donations,

        recent_announcements=
            recent_announcements
    )


# ================================================================
# ADMIN MEMBERS
# ================================================================

@app.route("/admin/members")
@admin_required
def admin_members():

    db = get_db()

    members = db.execute("""
        SELECT *
        FROM members
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
        "admin/members.html",
        members=members
    )


@app.route(
    "/admin/members/add",
    methods=["GET", "POST"]
)
@admin_required
def admin_add_member():

    if request.method == "POST":

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
        ).strip()

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

        if (
            not name
            or not surname
            or not phone
            or not address
            or not post
        ):

            flash(
                "Please fill in all required fields.",
                "error"
            )

            return redirect(
                url_for("admin_add_member")
            )

        if post not in POSTS:

            flash(
                "Please select a valid profession.",
                "error"
            )

            return redirect(
                url_for("admin_add_member")
            )

        if email:

            if not validate_email_with_mailboxlayer(
                email
            ):

                flash(
                    "Please provide a valid email address.",
                    "error"
                )

                return redirect(
                    url_for("admin_add_member")
                )

        db = get_db()

        try:

            db.execute("""
                INSERT INTO members
                (
                    name,
                    surname,
                    phone,
                    email,
                    address,
                    post,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                surname,
                phone,
                email,
                address,
                post,
                notes
            ))

            db.commit()

        except sqlite3.Error:

            db.rollback()

            flash(
                "Unable to add the member right now.",
                "error"
            )

            return redirect(
                url_for("admin_add_member")
            )

        flash(
            "Member added successfully.",
            "success"
        )

        return redirect(
            url_for("admin_members")
        )

    return render_template(
        "admin/member_form.html",
        member=None,
        posts=POSTS
    )


@app.route(
    "/admin/members/<int:member_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def admin_edit_member(member_id):

    db = get_db()

    member = db.execute(
        """
        SELECT *
        FROM members
        WHERE id = ?
        """,
        (member_id,)
    ).fetchone()

    if member is None:

        flash(
            "Member not found.",
            "error"
        )

        return redirect(
            url_for("admin_members")
        )

    if request.method == "POST":

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
        ).strip()

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

        if (
            not name
            or not surname
            or not phone
            or not address
            or not post
        ):

            flash(
                "Please fill in all required fields.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_edit_member",
                    member_id=member_id
                )
            )

        if post not in POSTS:

            flash(
                "Please select a valid profession.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_edit_member",
                    member_id=member_id
                )
            )

        if email:

            if not validate_email_with_mailboxlayer(
                email
            ):

                flash(
                    "Please provide a valid email address.",
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_edit_member",
                        member_id=member_id
                    )
                )

        try:

            db.execute("""
                UPDATE members
                SET
                    name = ?,
                    surname = ?,
                    phone = ?,
                    email = ?,
                    address = ?,
                    post = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                name,
                surname,
                phone,
                email,
                address,
                post,
                notes,
                member_id
            ))

            db.commit()

        except sqlite3.Error:

            db.rollback()

            flash(
                "Unable to update the member right now.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_edit_member",
                    member_id=member_id
                )
            )

        flash(
            "Member updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin_members")
        )

    return render_template(
        "admin/member_form.html",
        member=member,
        posts=POSTS
    )


@app.route(
    "/admin/members/<int:member_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_member(member_id):

    db = get_db()

    member = db.execute(
        """
        SELECT id
        FROM members
        WHERE id = ?
        """,
        (member_id,)
    ).fetchone()

    if member is None:

        flash(
            "Member not found.",
            "error"
        )

        return redirect(
            url_for("admin_members")
        )

    try:

        db.execute(
            """
            DELETE FROM members
            WHERE id = ?
            """,
            (member_id,)
        )

        db.commit()

    except sqlite3.Error:

        db.rollback()

        flash(
            "Unable to delete the member right now.",
            "error"
        )

        return redirect(
            url_for("admin_members")
        )

    flash(
        "Member deleted.",
        "success"
    )

    return redirect(
        url_for("admin_members")
    )


# ================================================================
# ADMIN DONATIONS
# ================================================================

@app.route("/admin/donations")
@admin_required
def admin_donations():

    db = get_db()

    donations = db.execute("""
        SELECT *
        FROM donations
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
        "admin/donations.html",
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
        "status",
        "Pending"
    ).strip()

    allowed_statuses = [
        "Pending",
        "Paid",
        "Cancelled"
    ]

    if status not in allowed_statuses:

        flash(
            "Invalid payment status.",
            "error"
        )

        return redirect(
            url_for("admin_donations")
        )

    db = get_db()

    donation = db.execute(
        """
        SELECT id
        FROM donations
        WHERE id = ?
        """,
        (donation_id,)
    ).fetchone()

    if donation is None:

        flash(
            "Donation not found.",
            "error"
        )

        return redirect(
            url_for("admin_donations")
        )

    try:

        if status == "Paid":

            db.execute(
                """
                UPDATE donations
                SET
                    payment_status = ?,
                    paid_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    status,
                    donation_id
                )
            )

        else:

            db.execute(
                """
                UPDATE donations
                SET
                    payment_status = ?,
                    paid_at = NULL
                WHERE id = ?
                """,
                (
                    status,
                    donation_id
                )
            )

        db.commit()

    except sqlite3.Error:

        db.rollback()

        flash(
            "Unable to update the donation status right now.",
            "error"
        )

        return redirect(
            url_for("admin_donations")
        )

    flash(
        "Donation status updated successfully.",
        "success"
    )

    return redirect(
        url_for("admin_donations")
    )


@app.route(
    "/admin/donations/<int:donation_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_donation(
    donation_id
):

    db = get_db()

    donation = db.execute(
        """
        SELECT id
        FROM donations
        WHERE id = ?
        """,
        (donation_id,)
    ).fetchone()

    if donation is None:

        flash(
            "Donation not found.",
            "error"
        )

        return redirect(
            url_for("admin_donations")
        )

    try:

        db.execute(
            """
            DELETE FROM donations
            WHERE id = ?
            """,
            (donation_id,)
        )

        db.commit()

    except sqlite3.Error:

        db.rollback()

        flash(
            "Unable to delete the donation right now.",
            "error"
        )

        return redirect(
            url_for("admin_donations")
        )

    flash(
        "Donation deleted.",
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
                "Title and announcement body are required.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_announcements"
                )
            )

        try:

            db.execute("""
                INSERT INTO announcements
                (
                    title,
                    body,
                    published
                )
                VALUES (?, ?, ?)
            """, (
                title,
                body,
                published
            ))

            db.commit()

        except sqlite3.Error:

            db.rollback()

            flash(
                "Unable to create the announcement right now.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_announcements"
                )
            )

        flash(
            "Announcement created.",
            "success"
        )

        return redirect(
            url_for(
                "admin_announcements"
            )
        )

    rows = db.execute("""
        SELECT *
        FROM announcements
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
        "admin/announcements.html",
        announcements=rows
    )


@app.route(
    "/admin/announcements/<int:announcement_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_announcement(
    announcement_id
):

    db = get_db()

    announcement = db.execute(
        """
        SELECT id
        FROM announcements
        WHERE id = ?
        """,
        (announcement_id,)
    ).fetchone()

    if announcement is None:

        flash(
            "Announcement not found.",
            "error"
        )

        return redirect(
            url_for(
                "admin_announcements"
            )
        )

    try:

        db.execute(
            """
            DELETE FROM announcements
            WHERE id = ?
            """,
            (announcement_id,)
        )

        db.commit()

    except sqlite3.Error:

        db.rollback()

        flash(
            "Unable to delete the announcement right now.",
            "error"
        )

        return redirect(
            url_for(
                "admin_announcements"
            )
        )

    flash(
        "Announcement deleted.",
        "success"
    )

    return redirect(
        url_for(
            "admin_announcements"
        )
    )


# ================================================================
# ERROR PAGES
# ================================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(500)
def internal_error(error):

    return render_template(
        "500.html"
    ), 500


# ================================================================
# INITIALIZE DATABASE
# ================================================================

with app.app_context():

    init_db()


# ================================================================
# START DEVELOPMENT SERVER
# ================================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )