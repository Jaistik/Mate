import os
import sqlite3
import razorpay
from datetime import datetime
from dotenv import load_dotenv


from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

load_dotenv()
app = Flask(__name__)

# Secret key for Flask sessions
app.secret_key = os.environ.get("MATE_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("MATE_SECRET_KEY is not configured")

#========================================================
#Razorpay
#========================================================
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError("Razorpay environment variables are not configured")

razorpay_client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)

# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


# SQLite database
DATABASE = os.path.join(
    BASE_DIR,
    "mate.db"
)


# User profile-photo folder
USER_UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads",
    "user"
)


# Professional profile-photo folder
PROFESSIONAL_UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads",
    "professional"
)


# ============================================================
# FLASK CONFIGURATION
# ============================================================

# Maximum upload size: 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

app.config["USER_UPLOAD_FOLDER"] = (
    USER_UPLOAD_FOLDER
)

app.config["PROFESSIONAL_UPLOAD_FOLDER"] = (
    PROFESSIONAL_UPLOAD_FOLDER
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

os.makedirs(
    USER_UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    PROFESSIONAL_UPLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    """
    Create and return a connection to mate.db.
    """

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    # Enable foreign-key support
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ============================================================
# DATABASE TEST
# ============================================================

def database_is_available():
    """
    Check whether the SQLite database
    can be opened successfully.
    """

    try:

        connection = get_db_connection()

        connection.execute(
            "SELECT 1"
        )

        connection.close()

        return True

    except sqlite3.Error:

        return False


# ============================================================
# GLOBAL TEMPLATE INFORMATION
# ============================================================

@app.context_processor
def inject_user():
    """
    Make session information available
    to all HTML templates.
    """

    return {
        "logged_in": "user_id" in session,

        "current_user_id":
            session.get("user_id"),

        "current_user_role":
            session.get("role"),

        "current_user_name":
            session.get("full_name"),

        "current_year":
            datetime.now().year
    }





# ============================================================
# CREATE NOTIFICATION
# ============================================================

def create_notification(
    title,
    message,
    user_id=None,
    professional_id=None
):
    """
    Create a notification for a user or professional.
    """

    connection = get_db_connection()

    try:

        connection.execute(
            """
            INSERT INTO notifications
            (
                user_id,
                professional_id,
                title,
                message
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                professional_id,
                title,
                message
            )
        )

        connection.commit()

    except sqlite3.Error as error:

        connection.rollback()

        print(
            "NOTIFICATION CREATION ERROR:",
            error
        )

    finally:

        connection.close()

# ============================================================
# PUBLIC ROUTES
# ============================================================

@app.route("/")
def index():
    """
    MATE homepage.
    """

    return render_template(
        "index.html"
    )


@app.route("/about")
def about():
    """
    About MATE page.
    """

    return render_template(
        "about.html"
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
    Contact page.

    Allows visitors to send a message to MATE.
    """

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name or not email or not message:

            flash(
                "Please fill in all required fields.",
                "danger"
            )

            return render_template(
                "contact.html"
            )


        # ----------------------------------------------------
        # SAVE MESSAGE
        # ----------------------------------------------------

        connection = get_db_connection()

        try:

            connection.execute(
                """
                INSERT INTO contact_messages
                (
                    name,
                    email,
                    subject,
                    message
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    subject,
                    message
                )
            )

            connection.commit()

            flash(
                "Your message has been sent successfully.",
                "success"
            )

            return redirect(
                url_for("contact")
            )


        except sqlite3.Error as error:

            connection.rollback()

            print(
                "CONTACT MESSAGE ERROR:",
                error
            )

            flash(
                "Unable to send your message.",
                "danger"
            )


        finally:

            connection.close()


    return render_template(
        "contact.html"
    )

@app.route("/explore")
def explore():
    """
    Display registered professionals.
    """

    connection = get_db_connection()

    try:

        professionals = connection.execute(
            """
            SELECT
                id,
                full_name,
                profile_photo,
                profession,
                category,
                experience,
                qualification,
                description,
                service_price,
                price_unit,
                location,
                service_area,
                verification_status
            FROM professionals
            ORDER BY id DESC
            """
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "EXPLORE DATABASE ERROR:",
            error
        )

        professionals = []

        flash(
            "Unable to load professionals.",
            "danger"
        )

    finally:

        connection.close()

    return render_template(
        "explore.html",
        professionals=professionals
    )



# ============================================================
# PROFESSIONAL DETAILS
# ============================================================

@app.route("/professional/<int:professional_id>")
def professional_details(professional_id):
    """
    Display the complete profile of a professional.
    """

    connection = get_db_connection()

    try:

        professional = connection.execute(
            """
            SELECT *
            FROM professionals
            WHERE id = ?
            """,
            (professional_id,)
        ).fetchone()

        if professional is None:

            flash(
                "Professional not found.",
                "danger"
            )

            return redirect(
                url_for("explore")
            )

        # ----------------------------------------------------
        # GET REVIEWS
        # ----------------------------------------------------

        reviews = connection.execute(
            """
            SELECT
                reviews.*,
                users.full_name AS user_name,
                users.profile_photo AS user_photo

            FROM reviews

            LEFT JOIN users
                ON reviews.user_id = users.id

            WHERE reviews.professional_id = ?

            ORDER BY reviews.created_at DESC
            """,
            (professional_id,)
        ).fetchall()

        # ----------------------------------------------------
        # AVERAGE RATING
        # ----------------------------------------------------

        rating_result = connection.execute(
            """
            SELECT
                AVG(rating) AS average_rating,
                COUNT(*) AS review_count

            FROM reviews

            WHERE professional_id = ?
            """,
            (professional_id,)
        ).fetchone()

    except sqlite3.Error as error:

        print(
            "PROFESSIONAL DETAILS DATABASE ERROR:",
            error
        )

        flash(
            "Unable to load professional profile.",
            "danger"
        )

        return redirect(
            url_for("explore")
        )

    finally:

        connection.close()


    average_rating = (
        rating_result["average_rating"]
        if rating_result
        and rating_result["average_rating"] is not None
        else 0
    )

    review_count = (
        rating_result["review_count"]
        if rating_result
        else 0
    )


    return render_template(
        "professional_details.html",
        professional=professional,
        reviews=reviews,
        average_rating=average_rating,
        review_count=review_count
    )

# ============================================================
# REGISTRATION CHOICE
# ============================================================

@app.route("/register")
def register_choice():
    """
    Registration choice page.

    User can choose between:
    - User account
    - Professional account
    """

    return render_template(
        "register_choice.html"
    )


# ============================================================
# USER REGISTRATION
# ============================================================

@app.route(
    "/register/user",
    methods=["GET", "POST"]
)
def register_user():
    """
    Register a new MATE user.

    Features:
    - Form validation
    - Duplicate email checking
    - Password hashing
    - Profile photo upload
    - SQLite insertion
    """

    if request.method == "POST":

        # ----------------------------------------------------
        # GET FORM DATA
        # ----------------------------------------------------

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        profile_photo = request.files.get(
            "profile_photo"
        )

        print("========================================")
        print("PROFILE PHOTO OBJECT:", profile_photo)
        print("PROFILE PHOTO FILENAME:", profile_photo.filename if profile_photo else None)
        print("========================================")
        


        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if (
            not full_name
            or not email
            or not password
        ):

            flash(
                "Name, email and password are required.",
                "danger"
            )

            return render_template(
                "register_user.html"
            )


        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return render_template(
                "register_user.html"
            )


        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "register_user.html"
            )


        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        connection = get_db_connection()


        try:

            # ------------------------------------------------
            # CHECK USER EMAIL
            # ------------------------------------------------

            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()


            # ------------------------------------------------
            # CHECK PROFESSIONAL EMAIL
            # ------------------------------------------------

            existing_professional = connection.execute(
                """
                SELECT id
                FROM professionals
                WHERE email = ?
                """,
                (email,)
            ).fetchone()


            if (
                existing_user
                or existing_professional
            ):

                flash(
                    "An account with this email already exists.",
                    "danger"
                )

                return render_template(
                    "register_user.html"
                )


            # ------------------------------------------------
            # HASH PASSWORD
            # ------------------------------------------------

            hashed_password = (
                generate_password_hash(
                    password
                )
            )


            # ------------------------------------------------
            # PROFILE PHOTO
            # ------------------------------------------------

            photo_filename = None


            if (
                profile_photo
                and profile_photo.filename
            ):

                original_filename = (
                    secure_filename(
                        profile_photo.filename
                    )
                )


                extension = os.path.splitext(
                    original_filename
                )[1].lower()


                allowed_extensions = {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                }


                if extension not in allowed_extensions:

                    flash(
                        "Please upload a JPG, JPEG, PNG, or WEBP image.",
                        "danger"
                    )

                    return render_template(
                        "register_user.html"
                    )


                # Generate unique filename
                import uuid

                photo_filename = (
                    str(uuid.uuid4())
                    + extension
                )


                upload_folder = app.config[
                    "USER_UPLOAD_FOLDER"
                ]


                photo_path = os.path.join(
                    upload_folder,
                    photo_filename
                )


                profile_photo.save(
                    photo_path
                )


            # ------------------------------------------------
            # INSERT USER
            # ------------------------------------------------

            connection.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    phone,
                    password,
                    location,
                    address,
                    profile_photo,
                    role
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    phone,
                    hashed_password,
                    location,
                    address,
                    photo_filename,
                    "user"
                )
            )


            connection.commit()


            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            flash(
                "User account created successfully. "
                "Please login.",
                "success"
            )


            return redirect(
                url_for("login")
            )


        except sqlite3.IntegrityError:

            connection.rollback()

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return render_template(
                "register_user.html"
            )


        except sqlite3.Error as error:

            connection.rollback()

            print(
                "DATABASE ERROR:",
                error
            )

            flash(
                "A database error occurred. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "register_user.html"
            )


        finally:

            connection.close()


    return render_template(
        "register_user.html"
    )


# ============================================================
# PROFESSIONAL REGISTRATION
# ============================================================

@app.route(
    "/register/professional",
    methods=["GET", "POST"]
)
def register_professional():
    """
    Register a professional.

    Initial registration creates the professional account.
    Additional professional information will be managed
    from the professional profile later.
    """

    if request.method == "POST":

        # ----------------------------------------------------
        # GET FORM DATA
        # ----------------------------------------------------

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        profession = request.form.get(
            "profession",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        experience = request.form.get(
            "experience",
            "0"
        ).strip()

        qualification = request.form.get(
            "qualification",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        service_area = request.form.get(
            "service_area",
            ""
        ).strip()

        service_price = request.form.get(
            "service_price",
            "0"
        ).strip()

        price_unit = request.form.get(
            "price_unit",
            "hour"
        ).strip()

        start_time = request.form.get(
            "start_time",
            ""
        ).strip()

        end_time = request.form.get(
            "end_time",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        profile_photo = request.files.get(
            "profile_photo"
        )


        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if (
            not full_name
            or not email
            or not password
        ):

            flash(
                "Name, email and password are required.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        # ----------------------------------------------------
        # CONVERT NUMERIC VALUES
        # ----------------------------------------------------

        try:

            experience_value = int(
                experience
            )

            if experience_value < 0:
                experience_value = 0


        except ValueError:

            flash(
                "Experience must be a valid number.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        try:

            service_price_value = float(
                service_price
            )

            if service_price_value < 0:
                service_price_value = 0


        except ValueError:

            flash(
                "Service price must be a valid number.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        connection = get_db_connection()


        try:

            # ------------------------------------------------
            # CHECK EMAIL
            # ------------------------------------------------

            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()


            existing_professional = connection.execute(
                """
                SELECT id
                FROM professionals
                WHERE email = ?
                """,
                (email,)
            ).fetchone()


            if (
                existing_user
                or existing_professional
            ):

                flash(
                    "An account with this email already exists.",
                    "danger"
                )

                return render_template(
                    "register_professional.html"
                )


            # ------------------------------------------------
            # HASH PASSWORD
            # ------------------------------------------------

            hashed_password = (
                generate_password_hash(
                    password
                )
            )


            # ------------------------------------------------
            # PROFILE PHOTO
            # ------------------------------------------------

            photo_filename = None


            if (
                profile_photo
                and profile_photo.filename
            ):

                original_filename = (
                    secure_filename(
                        profile_photo.filename
                    )
                )


                extension = os.path.splitext(
                    original_filename
                )[1].lower()


                allowed_extensions = {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                }


                if extension not in allowed_extensions:

                    flash(
                        "Please upload a JPG, JPEG, PNG, or WEBP image.",
                        "danger"
                    )

                    return render_template(
                        "register_professional.html"
                    )


                import uuid

                photo_filename = (
                    str(uuid.uuid4())
                    + extension
                )


                upload_folder = app.config[
                    "PROFESSIONAL_UPLOAD_FOLDER"
                ]


                photo_path = os.path.join(
                    upload_folder,
                    photo_filename
                )


                profile_photo.save(
                    photo_path
                )


            # ------------------------------------------------
            # INSERT PROFESSIONAL
            # ------------------------------------------------

            connection.execute(
                """
                INSERT INTO professionals
                (
                    full_name,
                    email,
                    phone,
                    password,
                    profile_photo,
                    profession,
                    category,
                    experience,
                    qualification,
                    description,
                    verification_status,
                    service_price,
                    price_unit,
                    location,
                    service_area,
                    start_time,
                    end_time,
                    role
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    full_name,
                    email,
                    phone,
                    hashed_password,
                    photo_filename,
                    profession,
                    category,
                    experience_value,
                    qualification,
                    description,
                    "pending",
                    service_price_value,
                    price_unit,
                    location,
                    service_area,
                    start_time,
                    end_time,
                    "professional"
                )
            )


            connection.commit()


            flash(
                "Professional account created successfully. "
                "Please login.",
                "success"
            )


            return redirect(
                url_for("login")
            )


        except sqlite3.IntegrityError:

            connection.rollback()

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        except sqlite3.Error as error:

            connection.rollback()

            print(
                "DATABASE ERROR:",
                error
            )

            flash(
                "A database error occurred. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "register_professional.html"
            )


        finally:

            connection.close()


    return render_template(
        "register_professional.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():
    """
    Login for both users and professionals.

    The email is checked against both tables.
    Account bans are checked after password verification.
    """

    if request.method == "POST":

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
                "danger"
            )

            return render_template(
                "login.html"
            )

        connection = get_db_connection()

        try:

            # ------------------------------------------------
            # CHECK USER
            # ------------------------------------------------

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            # ------------------------------------------------
            # CHECK PROFESSIONAL
            # ------------------------------------------------

            professional = connection.execute(
                """
                SELECT *
                FROM professionals
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

        finally:

            connection.close()

        # ----------------------------------------------------
        # USER LOGIN
        # ----------------------------------------------------

        if (
            user
            and check_password_hash(
                user["password"],
                password
            )
        ):

            # ------------------------------------------------
            # CHECK USER ACCOUNT STATUS
            # ------------------------------------------------

            account_status = user["account_status"]

            # Temporary ban
            if account_status == "temporarily_banned":

                ban_until = user["ban_until"]

                if ban_until:

                    connection = get_db_connection()

                    try:

                        # Check whether the temporary ban
                        # has expired
                        result = connection.execute(
                            """
                            SELECT datetime(?) <= datetime('now')
                            """,
                            (ban_until,)
                        ).fetchone()

                        ban_expired = result[0] == 1

                        if ban_expired:

                            connection.execute(
                                """
                                UPDATE users
                                SET account_status = 'active',
                                    ban_until = NULL,
                                    ban_reason = NULL
                                WHERE id = ?
                                """,
                                (user["id"],)
                            )

                            connection.commit()

                            account_status = "active"

                    finally:

                        connection.close()

            # ------------------------------------------------
            # BLOCK TEMPORARY BAN
            # ------------------------------------------------

            if account_status == "temporarily_banned":

                message = "Your account is temporarily banned."

                if user["ban_until"]:
                    message += f" Your ban expires on {user['ban_until']}."

                if user["ban_reason"]:
                    message += f" Reason: {user['ban_reason']}"

                flash(
                    message,
                    "danger"
                )

                return render_template(
                    "login.html"
                )

            # ------------------------------------------------
            # BLOCK PERMANENT BAN
            # ------------------------------------------------

            if account_status == "permanently_banned":

                message = "Your account has been permanently banned."

                if user["ban_reason"]:
                    message += f" Reason: {user['ban_reason']}"

                flash(
                    message,
                    "danger"
                )

                return render_template(
                    "login.html"
                )

            # ------------------------------------------------
            # NORMAL USER LOGIN
            # ------------------------------------------------

            session.clear()

            session["user_id"] = user["id"]

            session["role"] = "user"

            session["full_name"] = (
                user["full_name"]
            )

            session["email"] = (
                user["email"]
            )

            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("user_dashboard")
            )

        # ----------------------------------------------------
        # PROFESSIONAL LOGIN
        # ----------------------------------------------------

        if (
            professional
            and check_password_hash(
                professional["password"],
                password
            )
        ):

            # ------------------------------------------------
            # CHECK PROFESSIONAL ACCOUNT STATUS
            # ------------------------------------------------

            account_status = professional["account_status"]

            # Temporary ban
            if account_status == "temporarily_banned":

                ban_until = professional["ban_until"]

                if ban_until:

                    connection = get_db_connection()

                    try:

                        result = connection.execute(
                            """
                            SELECT datetime(?) <= datetime('now')
                            """,
                            (ban_until,)
                        ).fetchone()

                        ban_expired = result[0] == 1

                        if ban_expired:

                            connection.execute(
                                """
                                UPDATE professionals
                                SET account_status = 'active',
                                    ban_until = NULL,
                                    ban_reason = NULL
                                WHERE id = ?
                                """,
                                (professional["id"],)
                            )

                            connection.commit()

                            account_status = "active"

                    finally:

                        connection.close()

            # ------------------------------------------------
            # BLOCK TEMPORARY BAN
            # ------------------------------------------------

            if account_status == "temporarily_banned":

                message = "Your account is temporarily banned."

                if professional["ban_until"]:
                    message += f" Your ban expires on {professional['ban_until']}."

                if professional["ban_reason"]:
                    message += f" Reason: {professional['ban_reason']}"

                flash(
                    message,
                    "danger"
                )

                return render_template(
                    "login.html"
                )

            # ------------------------------------------------
            # BLOCK PERMANENT BAN
            # ------------------------------------------------

            if account_status == "permanently_banned":

                message = "Your account has been permanently banned."

                if professional["ban_reason"]:
                    message += f" Reason: {professional['ban_reason']}"

                flash(
                    message,
                    "danger"
                )

                return render_template(
                    "login.html"
                )

            # ------------------------------------------------
            # NORMAL PROFESSIONAL LOGIN
            # ------------------------------------------------

            session.clear()

            session["user_id"] = (
                professional["id"]
            )

            session["role"] = "professional"

            session["full_name"] = (
                professional["full_name"]
            )

            session["email"] = (
                professional["email"]
            )

            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("professional_dashboard")
            )

        # ----------------------------------------------------
        # INVALID LOGIN
        # ----------------------------------------------------

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    """
    Logout the current account.
    """

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# ============================================================
# USER DASHBOARD
# ============================================================

@app.route("/user/dashboard")
def user_dashboard():
    """
    User dashboard.

    Only logged-in users with the user role
    can access this page.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()


        # ----------------------------------------------------
        # GET USER BOOKINGS
        # ----------------------------------------------------

        bookings = connection.execute(
            """
            SELECT
                bookings.*,
                professionals.full_name AS professional_name

            FROM bookings

            LEFT JOIN professionals
                ON bookings.professional_id =
                   professionals.id

            WHERE bookings.user_id = ?

            ORDER BY bookings.created_at DESC
            """,
            (session["user_id"],)
        ).fetchall()


    except sqlite3.Error as error:

        print(
            "USER DASHBOARD DATABASE ERROR:",
            error
        )

        bookings = []


    finally:

        connection.close()


    # --------------------------------------------------------
    # USER NOT FOUND
    # --------------------------------------------------------

    if user is None:

        session.clear()

        flash(
            "Your account could not be found.",
            "danger"
        )

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # RENDER DASHBOARD
    # --------------------------------------------------------

    return render_template(
        "user_dashboard.html",
        user=user,
        bookings=bookings
    )


# ============================================================
# USER PROFILE
# ============================================================

@app.route("/user/profile", methods=["GET", "POST"])
def user_profile():
    """
    User profile page.

    Allows a logged-in user to view and update
    their basic profile information.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    connection = get_db_connection()


    try:

        # ----------------------------------------------------
        # UPDATE PROFILE
        # ----------------------------------------------------

        if request.method == "POST":

            full_name = request.form.get(
                "full_name",
                ""
            ).strip()

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            location = request.form.get(
                "location",
                ""
            ).strip()

            address = request.form.get(
                "address",
                ""
            ).strip()


            if not full_name:

                flash(
                    "Full name is required.",
                    "danger"
                )

            else:

                connection.execute(
                    """
                    UPDATE users

                    SET
                        full_name = ?,
                        phone = ?,
                        location = ?,
                        address = ?

                    WHERE id = ?
                    """,
                    (
                        full_name,
                        phone,
                        location,
                        address,
                        session["user_id"]
                    )
                )

                connection.commit()


                # Update session name
                session["full_name"] = full_name


                flash(
                    "Profile updated successfully.",
                    "success"
                )


        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()


    finally:

        connection.close()


    # --------------------------------------------------------
    # USER NOT FOUND
    # --------------------------------------------------------

    if user is None:

        session.clear()

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "user_profile.html",
        user=user
    )

# ============================================================
# PROFESSIONAL DASHBOARD
# ============================================================

@app.route("/professional/dashboard")
def professional_dashboard():
    """
    Professional dashboard.

    Only logged-in professionals can access it.
    """

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("role") != "professional":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    connection = get_db_connection()


    try:

        professional = connection.execute(
            """
            SELECT *
            FROM professionals
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

    finally:

        connection.close()


    if professional is None:

        session.clear()

        return redirect(
            url_for("login")
        )


    return render_template(
        "professional_dashboard.html",
        professional=professional
    )



# ============================================================
# PROFESSIONAL PROFILE
# ============================================================

@app.route("/professional/profile", methods=["GET", "POST"])
def professional_profile():

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "professional":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # UPDATE PROFILE
        # ----------------------------------------------------

        if request.method == "POST":

            full_name = request.form.get(
                "full_name",
                ""
            ).strip()

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            profession = request.form.get(
                "profession",
                ""
            ).strip()

            category = request.form.get(
                "category",
                ""
            ).strip()

            experience = request.form.get(
                "experience",
                "0"
            ).strip()

            qualification = request.form.get(
                "qualification",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            location = request.form.get(
                "location",
                ""
            ).strip()

            service_area = request.form.get(
                "service_area",
                ""
            ).strip()

            service_price = request.form.get(
                "service_price",
                "0"
            ).strip()

            price_unit = request.form.get(
                "price_unit",
                "hour"
            ).strip()

            start_time = request.form.get(
                "start_time",
                ""
            ).strip()

            end_time = request.form.get(
                "end_time",
                ""
            ).strip()

            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if not full_name:

                flash(
                    "Full name is required.",
                    "danger"
                )

            else:

                try:

                    experience_value = int(
                        experience
                    )

                    service_price_value = float(
                        service_price
                    )

                    if experience_value < 0:
                        experience_value = 0

                    if service_price_value < 0:
                        service_price_value = 0

                except ValueError:

                    flash(
                        "Experience and service price must be valid numbers.",
                        "danger"
                    )

                    professional = connection.execute(
                        """
                        SELECT *
                        FROM professionals
                        WHERE id = ?
                        """,
                        (session["user_id"],)
                    ).fetchone()

                    return render_template(
                        "professional_profile.html",
                        professional=professional
                    )

                # --------------------------------------------
                # UPDATE DATABASE
                # --------------------------------------------

                connection.execute(
                    """
                    UPDATE professionals

                    SET
                        full_name = ?,
                        phone = ?,
                        profession = ?,
                        category = ?,
                        experience = ?,
                        qualification = ?,
                        description = ?,
                        location = ?,
                        service_area = ?,
                        service_price = ?,
                        price_unit = ?,
                        start_time = ?,
                        end_time = ?,
                        verification_status = ?

                    WHERE id = ?
                    """,
                    (
                        full_name,
                        phone,
                        profession,
                        category,
                        experience_value,
                        qualification,
                        description,
                        location,
                        service_area,
                        service_price_value,
                        price_unit,
                        start_time,
                        end_time,
                        "pending",
                        session["user_id"]
                    )
                )

                connection.commit()

                # Update session name
                session["full_name"] = full_name

                flash(
                    "Professional profile updated successfully.",
                    "success"
                )

        # ----------------------------------------------------
        # GET PROFESSIONAL
        # ----------------------------------------------------

        professional = connection.execute(
            """
            SELECT *
            FROM professionals
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

    except sqlite3.Error as error:

        connection.rollback()

        print(
            "PROFESSIONAL PROFILE DATABASE ERROR:",
            error
        )

        flash(
            "Unable to update your profile.",
            "danger"
        )

        professional = connection.execute(
            """
            SELECT *
            FROM professionals
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

    finally:

        connection.close()

    # --------------------------------------------------------
    # PROFESSIONAL NOT FOUND
    # --------------------------------------------------------

    if professional is None:

        session.clear()

        flash(
            "Your professional account could not be found.",
            "danger"
        )

        return redirect(
            url_for("login")
        )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "professional_profile.html",
        professional=professional
    )


# ============================================================
# PROFESSIONAL BOOKINGS
# ============================================================

@app.route("/professional/bookings")
def professional_bookings():
    """
    Display bookings received by the logged-in professional.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "professional":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()

    try:

        bookings = connection.execute(
            """
            SELECT
                bookings.*,
                users.full_name AS user_name,
                users.email AS user_email,
                users.phone AS user_phone

            FROM bookings

            LEFT JOIN users
                ON bookings.user_id = users.id

            WHERE bookings.professional_id = ?

            ORDER BY bookings.created_at DESC
            """,
            (session["user_id"],)
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "PROFESSIONAL BOOKINGS DATABASE ERROR:",
            error
        )

        bookings = []

        flash(
            "Unable to load your bookings.",
            "danger"
        )

    finally:

        connection.close()

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "professional_bookings.html",
        bookings=bookings
    )

# ============================================================
# UPDATE BOOKING STATUS
# ============================================================

@app.route(
    "/professional/bookings/<int:booking_id>/status",
    methods=["POST"]
)
def update_booking_status(booking_id):
    """
    Allow a professional to update the status
    of one of their bookings.

    Flow:
        pending → accepted
        pending → rejected
        confirmed → completed
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "professional":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    # --------------------------------------------------------
    # GET NEW STATUS
    # --------------------------------------------------------

    new_status = request.form.get(
        "status",
        ""
    ).strip().lower()


    allowed_statuses = {
        "accepted",
        "rejected",
        "completed"
    }


    if new_status not in allowed_statuses:

        flash(
            "Invalid booking status.",
            "danger"
        )

        return redirect(
            url_for("professional_bookings")
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()


    try:

        # ----------------------------------------------------
        # GET BOOKING
        # ----------------------------------------------------

        booking = connection.execute(
            """
            SELECT
                id,
                user_id,
                professional_id,
                status,
                service
            FROM bookings
            WHERE id = ?
              AND professional_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        ).fetchone()


        # ----------------------------------------------------
        # BOOKING NOT FOUND
        # ----------------------------------------------------

        if booking is None:

            flash(
                "Booking not found or access denied.",
                "danger"
            )

            return redirect(
                url_for("professional_bookings")
            )


        current_status = (
            booking["status"] or ""
        ).lower()


        # ----------------------------------------------------
        # ACCEPT BOOKING
        # ----------------------------------------------------

        if new_status == "accepted":

            if current_status != "pending":

                flash(
                    "Only pending bookings can be accepted.",
                    "warning"
                )

                return redirect(
                    url_for("professional_bookings")
                )


        # ----------------------------------------------------
        # REJECT BOOKING
        # ----------------------------------------------------

        elif new_status == "rejected":

            if current_status != "pending":

                flash(
                    "Only pending bookings can be rejected.",
                    "warning"
                )

                return redirect(
                    url_for("professional_bookings")
                )


        # ----------------------------------------------------
        # COMPLETE BOOKING
        # ----------------------------------------------------

        elif new_status == "completed":

            # IMPORTANT:
            # A professional can only complete a booking
            # after the user has successfully paid.

            if current_status != "confirmed":

                flash(
                    "The booking must be paid for before it can be completed.",
                    "warning"
                )

                return redirect(
                    url_for("professional_bookings")
                )


        # ----------------------------------------------------
        # UPDATE STATUS
        # ----------------------------------------------------

        connection.execute(
            """
            UPDATE bookings
            SET status = ?
            WHERE id = ?
              AND professional_id = ?
            """,
            (
                new_status,
                booking_id,
                session["user_id"]
            )
        )


        connection.commit()

        # --------------------------------------------------------
        # CREATE USER NOTIFICATION
        # --------------------------------------------------------

        if new_status == "accepted":
            create_notification(
                title="Booking Accepted",
                message=(
                    f"Your booking for {booking['service']} "
                    "has been accepted. You can now proceed "
                    "with payment."
                ),
                user_id=booking["user_id"]
            )

        elif new_status == "rejected":
            create_notification(
                title="Booking Rejected",
                message=(
                    f"Your booking for {booking['service']} "
                    "has been rejected."
                ),
                user_id=booking["user_id"]
            )

        elif new_status == "completed":
            create_notification(
                title="Booking Completed",
                message=(
                    f"Your booking for {booking['service']} "
                    "has been completed."
                ),
                user_id=booking["user_id"]
            )

        # ----------------------------------------------------
        # SUCCESS MESSAGES
        # ----------------------------------------------------

        if new_status == "accepted":

            flash(
                "Booking accepted. The user can now proceed with payment.",
                "success"
            )


        elif new_status == "rejected":

            flash(
                "Booking rejected.",
                "warning"
            )


        elif new_status == "completed":

            flash(
                "Booking marked as completed.",
                "success"
            )


    except sqlite3.Error as error:

        connection.rollback()

        print(
            "UPDATE BOOKING STATUS ERROR:",
            error
        )

        flash(
            "Unable to update the booking.",
            "danger"
        )


    finally:

        connection.close()


    return redirect(
        url_for("professional_bookings")
    )

# ============================================================
# PROFESSIONAL EARNINGS
# ============================================================

@app.route("/professional/earnings")
def professional_earnings():
    """
    Professional earnings page.

    Earnings are calculated from completed bookings
    belonging to the logged-in professional.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "professional":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # GET COMPLETED BOOKINGS
        # ----------------------------------------------------

        completed_bookings = connection.execute(
            """
            SELECT
                bookings.*,
                users.full_name AS user_name

            FROM bookings

            LEFT JOIN users
                ON bookings.user_id = users.id

            WHERE bookings.professional_id = ?
            AND LOWER(bookings.status) = 'completed'

            ORDER BY bookings.created_at DESC
            """,
            (session["user_id"],)
        ).fetchall()


    except sqlite3.Error as error:

        print(
            "PROFESSIONAL EARNINGS DATABASE ERROR:",
            error
        )

        completed_bookings = []

        flash(
            "Unable to load earnings.",
            "danger"
        )


    finally:

        connection.close()


    # --------------------------------------------------------
    # CALCULATE EARNINGS
    # --------------------------------------------------------

    total_earnings = 0.0

    for booking in completed_bookings:

        try:

            amount = float(
                booking["price"]
            )

        except (
            ValueError,
            TypeError
        ):

            amount = 0.0

        total_earnings += amount


    completed_jobs = len(
        completed_bookings
    )


    if completed_jobs > 0:

        average_earning = (
            total_earnings / completed_jobs
        )

    else:

        average_earning = 0.0


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "professional_earnings.html",
        completed_bookings=completed_bookings,
        total_earnings=total_earnings,
        completed_jobs=completed_jobs,
        average_earning=average_earning
    )

# ============================================================
# PROFESSIONAL SCHEDULE
# ============================================================

@app.route("/professional/schedule")
def professional_schedule():
    """
    Display the logged-in professional's schedule.

    Shows upcoming accepted bookings.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "professional":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()

    try:

        bookings = connection.execute(
            """
            SELECT
                bookings.*,
                users.full_name AS user_name,
                users.phone AS user_phone

            FROM bookings

            LEFT JOIN users
                ON bookings.user_id = users.id

            WHERE bookings.professional_id = ?

            AND LOWER(bookings.status) IN (
                'accepted',
                'confirmed'
            )

            ORDER BY
                bookings.booking_date ASC,
                bookings.booking_time ASC
            """,
            (session["user_id"],)
        ).fetchall()


    except sqlite3.Error as error:

        print(
            "PROFESSIONAL SCHEDULE DATABASE ERROR:",
            error
        )

        bookings = []

        flash(
            "Unable to load your schedule.",
            "danger"
        )


    finally:

        connection.close()


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "professional_schedule.html",
        bookings=bookings
    )

# ============================================================
# USER BOOKING HISTORY
# ============================================================

@app.route("/user/bookings")
def booking_history():
    """
    Display the logged-in user's booking history.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Access denied.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_db_connection()

    try:

        bookings = connection.execute(
    """
    SELECT
        bookings.*,

        professionals.full_name AS professional_name,
        professionals.profile_photo AS professional_photo,
        professionals.profession AS professional_profession

    FROM bookings

    LEFT JOIN professionals
        ON bookings.professional_id = professionals.id

    WHERE bookings.user_id = ?

    ORDER BY bookings.created_at DESC
    """,
    (session["user_id"],)
).fetchall()

    except sqlite3.Error as error:

        print(
            "BOOKING HISTORY DATABASE ERROR:",
            error
        )

        bookings = []

        flash(
            "Unable to load booking history.",
            "danger"
        )

    finally:

        connection.close()


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "booking_history.html",
        bookings=bookings
    )


# ============================================================
# USER REVIEW
# ============================================================

@app.route(
    "/user/review/<int:booking_id>",
    methods=["GET", "POST"]
)
def user_review(booking_id):
    """
    Allow a user to review a completed booking.

    Only the user who owns the booking can submit
    a review, and only completed bookings can be reviewed.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Only users can submit reviews.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    connection = get_db_connection()


    try:

        # ----------------------------------------------------
        # GET BOOKING
        # ----------------------------------------------------

        booking = connection.execute(
            """
            SELECT
                bookings.*,

                professionals.full_name AS professional_name,
                professionals.profile_photo AS professional_photo,
                professionals.profession AS professional_profession

            FROM bookings

            LEFT JOIN professionals
                ON bookings.professional_id = professionals.id

            WHERE bookings.id = ?
              AND bookings.user_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        ).fetchone()


        # ----------------------------------------------------
        # BOOKING NOT FOUND
        # ----------------------------------------------------

        if booking is None:

            flash(
                "Booking not found or access denied.",
                "danger"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # ONLY COMPLETED BOOKINGS CAN BE REVIEWED
        # ----------------------------------------------------

        if booking["status"].lower() != "completed":

            flash(
                "Only completed bookings can be reviewed.",
                "warning"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # CHECK IF REVIEW ALREADY EXISTS
        # ----------------------------------------------------

        existing_review = connection.execute(
            """
            SELECT *
            FROM reviews
            WHERE booking_id = ?
              AND user_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        ).fetchone()


        # ----------------------------------------------------
        # SUBMIT REVIEW
        # ----------------------------------------------------

        if request.method == "POST":

            # Prevent duplicate reviews

            if existing_review:

                flash(
                    "You have already reviewed this booking.",
                    "warning"
                )

                return redirect(
                    url_for("booking_history")
                )


            rating = request.form.get(
                "rating",
                ""
            ).strip()

            review_text = request.form.get(
                "review_text",
                ""
            ).strip()


            # ------------------------------------------------
            # VALIDATE RATING
            # ------------------------------------------------

            try:

                rating_value = int(rating)

            except ValueError:

                rating_value = 0


            if rating_value < 1 or rating_value > 5:

                flash(
                    "Please select a rating between 1 and 5.",
                    "danger"
                )

                return render_template(
                    "user_review.html",
                    booking=booking
                )


            # ------------------------------------------------
            # INSERT REVIEW
            # ------------------------------------------------

            connection.execute(
                """
                INSERT INTO reviews
                (
                    user_id,
                    professional_id,
                    booking_id,
                    rating,
                    review_text
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    booking["professional_id"],
                    booking_id,
                    rating_value,
                    review_text
                )
            )


            connection.commit()


            flash(
                "Your review has been submitted successfully.",
                "success"
            )


            return redirect(
                url_for("booking_history")
            )


    except sqlite3.IntegrityError as error:

        connection.rollback()

        print(
            "REVIEW INTEGRITY ERROR:",
            error
        )

        flash(
            "Unable to submit this review.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    except sqlite3.Error as error:

        connection.rollback()

        print(
            "REVIEW DATABASE ERROR:",
            error
        )

        flash(
            "Unable to submit your review.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    finally:

        connection.close()


    # --------------------------------------------------------
    # RENDER REVIEW PAGE
    # --------------------------------------------------------

    return render_template(
        "user_review.html",
        booking=booking,
        existing_review=existing_review
    )

# ============================================================
# BOOK PROFESSIONAL
# ============================================================

@app.route(
    "/booking/<int:professional_id>",
    methods=["GET", "POST"]
)
def booking(professional_id):
    """
    Allow a logged-in user to book a professional.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        flash(
            "Please login to book a professional.",
            "danger"
        )

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Only users can book professionals.",
            "danger"
        )

        return redirect(
            url_for("explore")
        )


    connection = get_db_connection()


    try:

        # ----------------------------------------------------
        # GET PROFESSIONAL
        # ----------------------------------------------------

        professional = connection.execute(
            """
            SELECT *
            FROM professionals
            WHERE id = ?
            """,
            (professional_id,)
        ).fetchone()


        if professional is None:

            flash(
                "Professional not found.",
                "danger"
            )

            return redirect(
                url_for("explore")
            )


        # ----------------------------------------------------
        # PROCESS BOOKING
        # ----------------------------------------------------

        if request.method == "POST":

            booking_date = request.form.get(
                "booking_date",
                ""
            ).strip()

            booking_time = request.form.get(
                "booking_time",
                ""
            ).strip()

            service = request.form.get(
                "service",
                ""
            ).strip()

            message = request.form.get(
                "message",
                ""
            ).strip()


            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if not booking_date or not booking_time:

                flash(
                    "Please select a date and time.",
                    "danger"
                )

                return render_template(
                    "booking.html",
                    professional=professional
                )


            if not service:

                service = (
                    professional["profession"]
                    or "Professional Service"
                )


            # ------------------------------------------------
            # CREATE BOOKING
            # ------------------------------------------------

            connection.execute(
                """
                INSERT INTO bookings
                (
                    user_id,
                    professional_id,
                    booking_date,
                    booking_time,
                    service,
                    message,
                    price,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    professional_id,
                    booking_date,
                    booking_time,
                    service,
                    message,
                    professional["service_price"] or 0,
                    "pending"
                )
            )


            connection.commit()

            # Notify professional about new booking
            connection.execute(
                """
                INSERT INTO notifications
                (
                professional_id,
                title,
                message
                )
                VALUES (?, ?, ?)
                """,
                (
                    professional_id,
                    "Booking Request",
                    "You have received a new booking request."
                    )
                )

            connection.commit()


            flash(
                "Booking request sent successfully.",
                "success"
            )


            return redirect(
                url_for("booking_history")
            )


    except sqlite3.Error as error:

        connection.rollback()

        print(
            "BOOKING DATABASE ERROR:",
            error
        )

        flash(
            "Unable to create booking.",
            "danger"
        )


    finally:

        connection.close()


    return render_template(
        "booking.html",
        professional=professional
    )

# ============================================================
# PAYMENT
# ============================================================

@app.route("/payment/<int:booking_id>", methods=["GET"])
def payment(booking_id):
    """
    Display the payment page for an accepted booking.

    Only the user who owns the booking can access it.
    A Razorpay order is created when the payment page is opened.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        flash(
            "Please login to continue.",
            "danger"
        )

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Only users can make payments.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # GET BOOKING
        # ----------------------------------------------------

        booking = connection.execute(
            """
            SELECT
                bookings.*,

                professionals.full_name AS professional_name,
                professionals.profile_photo AS professional_photo,
                professionals.profession AS professional_profession

            FROM bookings

            LEFT JOIN professionals
                ON bookings.professional_id = professionals.id

            WHERE bookings.id = ?
              AND bookings.user_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        ).fetchone()


        # ----------------------------------------------------
        # BOOKING NOT FOUND
        # ----------------------------------------------------

        if booking is None:

            flash(
                "Booking not found or access denied.",
                "danger"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # PAYMENT ONLY AFTER ACCEPTANCE
        # ----------------------------------------------------

        if booking["status"].lower() != "accepted":

            flash(
                "Payment is available only for accepted bookings.",
                "warning"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # CHECK PAYMENT STATUS
        # ----------------------------------------------------

        if booking["payment_status"] == "paid":

            flash(
                "This booking has already been paid.",
                "info"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # CHECK BOOKING AMOUNT
        # ----------------------------------------------------

        amount = float(
            booking["price"] or 0
        )

        if amount <= 0:

            flash(
                "Invalid booking amount.",
                "danger"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # CONVERT RUPEES TO PAISE
        # ----------------------------------------------------

        amount_in_paise = int(
            round(amount * 100)
        )


        # ----------------------------------------------------
        # CREATE RAZORPAY ORDER
        # ----------------------------------------------------

        razorpay_order = razorpay_client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"booking_{booking_id}"
            }
        )


        # ----------------------------------------------------
        # SAVE RAZORPAY ORDER ID
        # ----------------------------------------------------

        connection.execute(
            """
            UPDATE bookings
            SET
                razorpay_order_id = ?,
                payment_status = 'pending'
            WHERE id = ?
            """,
            (
                razorpay_order["id"],
                booking_id
            )
        )

        connection.commit()


        # ----------------------------------------------------
        # SHOW PAYMENT PAGE
        # ----------------------------------------------------

        return render_template(
            "payment.html",
            booking=booking,
            razorpay_order_id=razorpay_order["id"],
            razorpay_key_id=RAZORPAY_KEY_ID
        )


    except sqlite3.Error as error:

        print(
            "PAYMENT DATABASE ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to load the payment page.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    except Exception as error:

        print(
            "RAZORPAY PAYMENT ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to create the payment.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    finally:

        connection.close()


# ============================================================
# VERIFY RAZORPAY PAYMENT
# ============================================================

@app.route("/verify-payment/<int:booking_id>", methods=["POST"])
def verify_payment(booking_id):

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        flash(
            "Please login to continue.",
            "danger"
        )

        return redirect(
            url_for("login")
        )


    # --------------------------------------------------------
    # ROLE CHECK
    # --------------------------------------------------------

    if session.get("role") != "user":

        flash(
            "Only users can make payments.",
            "danger"
        )

        return redirect(
            url_for("index")
        )


    # --------------------------------------------------------
    # GET RAZORPAY PAYMENT DATA
    # --------------------------------------------------------

    payment_id = request.form.get(
        "razorpay_payment_id"
    )

    order_id = request.form.get(
        "razorpay_order_id"
    )

    signature = request.form.get(
        "razorpay_signature"
    )


    # --------------------------------------------------------
    # CHECK PAYMENT DATA
    # --------------------------------------------------------

    if not payment_id or not order_id or not signature:

        flash(
            "Payment verification data is missing.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # GET BOOKING
        # ----------------------------------------------------

        booking = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ?
              AND user_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        ).fetchone()


        # ----------------------------------------------------
        # BOOKING NOT FOUND
        # ----------------------------------------------------

        if booking is None:

            flash(
                "Booking not found.",
                "danger"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # CHECK ORDER ID
        # ----------------------------------------------------

        if booking["razorpay_order_id"] != order_id:

            flash(
                "Payment order does not match this booking.",
                "danger"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # CHECK IF ALREADY PAID
        # ----------------------------------------------------

        if booking["payment_status"] == "paid":

            flash(
                "This booking has already been paid.",
                "info"
            )

            return redirect(
                url_for("booking_history")
            )


        # ----------------------------------------------------
        # VERIFY RAZORPAY SIGNATURE
        # ----------------------------------------------------

        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            }
        )


        # ----------------------------------------------------
        # PAYMENT VERIFIED
        # ----------------------------------------------------

        connection.execute(
            """
            UPDATE bookings
            SET
                razorpay_payment_id = ?,
                payment_status = 'paid',
                paid_at = datetime(
                    'now',
                    '+5 hours',
                    '+30 minutes'
                ),
                status = 'confirmed'
            WHERE id = ?
              AND payment_status != 'paid'
            """,
            (
                payment_id,
                booking_id
            )
        )


        connection.commit()


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        flash(
            "Payment successful! Your booking is now confirmed.",
            "success"
        )

        return redirect(
            url_for("booking_history")
        )


    # --------------------------------------------------------
    # DATABASE ERROR
    # --------------------------------------------------------

    except sqlite3.Error as error:

        print(
            "PAYMENT VERIFICATION DATABASE ERROR:",
            error
        )

        connection.rollback()

        flash(
            "A database error occurred while verifying payment.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    # --------------------------------------------------------
    # RAZORPAY / OTHER ERROR
    # --------------------------------------------------------

    except Exception as error:

        print(
            "RAZORPAY PAYMENT VERIFICATION ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Payment verification failed. If money was deducted, please contact support.",
            "danger"
        )

        return redirect(
            url_for("booking_history")
        )


    finally:

        connection.close()

# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
def notifications():
    """
    Display notifications for the logged-in user or professional.
    """

    # --------------------------------------------------------
    # AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]
    role = session.get("role")

    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # USER NOTIFICATIONS
        # ----------------------------------------------------

        if role == "user":

            notifications = connection.execute(
                """
                SELECT *
                FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            ).fetchall()


        # ----------------------------------------------------
        # PROFESSIONAL NOTIFICATIONS
        # ----------------------------------------------------

        elif role == "professional":

            notifications = connection.execute(
                """
                SELECT *
                FROM notifications
                WHERE professional_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            ).fetchall()


        else:

            notifications = []


    except sqlite3.Error as error:

        print(
            "NOTIFICATIONS DATABASE ERROR:",
            error
        )

        notifications = []

        flash(
            "Unable to load notifications.",
            "danger"
        )

    finally:

        connection.close()


    return render_template(
        "notifications.html",
        notifications=notifications
    )

# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """
    Login page for MATE administrators.
    """

    # --------------------------------------------------------
    # IF ALREADY LOGGED IN AS ADMIN
    # --------------------------------------------------------

    if session.get("admin_id"):

        return redirect(
            url_for("admin_dashboard")
        )


    # --------------------------------------------------------
    # PROCESS LOGIN
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not username or not password:

            flash(
                "Please enter your username and password.",
                "danger"
            )

            return render_template(
                "admin_login.html"
            )


        connection = get_db_connection()


        try:

            admin = connection.execute(
                """
                SELECT *
                FROM admins
                WHERE username = ?
                """,
                (username,)
            ).fetchone()


            # ------------------------------------------------
            # CHECK PASSWORD
            # ------------------------------------------------

            if admin and check_password_hash(
                admin["password"],
                password
            ):

                session.clear()

                session["admin_id"] = admin["id"]

                session["admin_username"] = admin["username"]


                flash(
                    "Welcome to the MATE Admin Panel.",
                    "success"
                )


                return redirect(
                    url_for("admin_dashboard")
                )


            flash(
                "Invalid admin username or password.",
                "danger"
            )


        except sqlite3.Error as error:

            print(
                "ADMIN LOGIN DATABASE ERROR:",
                error
            )

            flash(
                "Unable to login.",
                "danger"
            )


        finally:

            connection.close()


    return render_template(
        "admin_login.html"
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():
    """
    Display the MATE administrator dashboard.
    """

    # --------------------------------------------------------
    # ADMIN AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # TOTAL USERS
        # ----------------------------------------------------

        total_users = connection.execute(
            """
            SELECT COUNT(*)
            AS count
            FROM users
            """
        ).fetchone()["count"]


        # ----------------------------------------------------
        # TOTAL PROFESSIONALS
        # ----------------------------------------------------

        total_professionals = connection.execute(
            """
            SELECT COUNT(*)
            AS count
            FROM professionals
            """
        ).fetchone()["count"]


        # ----------------------------------------------------
        # TOTAL BOOKINGS
        # ----------------------------------------------------

        total_bookings = connection.execute(
            """
            SELECT COUNT(*)
            AS count
            FROM bookings
            """
        ).fetchone()["count"]


        # ----------------------------------------------------
        # COMPLETED BOOKINGS
        # ----------------------------------------------------

        completed_bookings = connection.execute(
            """
            SELECT COUNT(*)
            AS count
            FROM bookings
            WHERE LOWER(status) = 'completed'
            """
        ).fetchone()["count"]


        # ----------------------------------------------------
        # PENDING PROFESSIONAL VERIFICATIONS
        # ----------------------------------------------------

        pending_professionals = connection.execute(
            """
            SELECT COUNT(*)
            AS count
            FROM professionals
            WHERE LOWER(verification_status) = 'pending'
            """
        ).fetchone()["count"]


        # ----------------------------------------------------
        # UNREAD CONTACT MESSAGES
        # ----------------------------------------------------

        unread_messages = connection.execute(
            """
            SELECT COUNT(*)
            AS count
            FROM contact_messages
            WHERE is_read = 0
            """
        ).fetchone()["count"]


    except sqlite3.Error as error:

        print(
            "ADMIN DASHBOARD DATABASE ERROR:",
            error
        )

        flash(
            "Unable to load admin dashboard.",
            "danger"
        )

        total_users = 0
        total_professionals = 0
        total_bookings = 0
        completed_bookings = 0
        pending_professionals = 0
        unread_messages = 0

    finally:

        connection.close()


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_professionals=total_professionals,
        total_bookings=total_bookings,
        completed_bookings=completed_bookings,
        pending_professionals=pending_professionals,
        unread_messages=unread_messages
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():
    """
    Log the admin out of MATE.
    """

    session.pop("admin_id", None)

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


@app.route("/admin/users")
def admin_users():
    """
    Display all registered MATE users.
    """

    # --------------------------------------------------------
    # ADMIN AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    connection = get_db_connection()

    try:

        users = connection.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                location,
                profile_photo,
                created_at,
                account_status,
                ban_until,
                ban_reason
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "ADMIN USERS DATABASE ERROR:",
            error
        )

        users = []

        flash(
            "Unable to load users.",
            "danger"
        )

    finally:

        connection.close()


    return render_template(
        "admin_users.html",
        users=users
    )

# ============================================================
# ADMIN — USER ACCOUNT CONTROLS
# ============================================================

@app.route(
    "/admin/users/<int:user_id>/temporary-ban",
    methods=["POST"]
)
def admin_temp_ban_user(user_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    # Get and validate ban duration
    duration = request.form.get("duration", "7").strip()

    allowed_durations = {
        "1": 1,
        "3": 3,
        "7": 7,
        "30": 30
    }

    if duration not in allowed_durations:
        flash("Invalid temporary ban duration.", "danger")
        return redirect(url_for("admin_users"))

    days = allowed_durations[duration]

    # Get optional reason
    reason = request.form.get("reason", "").strip()

    if not reason:
        reason = "Temporarily banned by administrator."

    connection = get_db_connection()

    try:

        connection.execute(
            """
            UPDATE users
            SET account_status = 'temporarily_banned',
                ban_until = datetime('now', ?),
                ban_reason = ?
            WHERE id = ?
            """,
            (
                f"+{days} days",
                reason,
                user_id
            )
        )

        connection.commit()

        flash(
            f"User has been temporarily banned for {days} day(s).",
            "warning"
        )

    except sqlite3.Error as error:

        print(
            "TEMPORARY BAN ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to temporarily ban the user.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_users")
    )


@app.route(
    "/admin/users/<int:user_id>/permanent-ban",
    methods=["POST"]
)
def admin_permanent_ban_user(user_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    # Get permanent ban reason
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash(
            "Please enter a reason for the permanent ban.",
            "danger"
        )
        return redirect(url_for("admin_users"))

    connection = get_db_connection()

    try:

        connection.execute(
            """
            UPDATE users
            SET account_status = 'permanently_banned',
                ban_until = NULL,
                ban_reason = ?
            WHERE id = ?
            """,
            (
                reason,
                user_id
            )
        )

        connection.commit()

        flash(
            "User has been permanently banned.",
            "danger"
        )

    except sqlite3.Error as error:

        print(
            "PERMANENT BAN ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to permanently ban the user.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_users")
    )


@app.route(
    "/admin/users/<int:user_id>/unban",
    methods=["POST"]
)
def admin_unban_user(user_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    try:

        connection.execute(
            """
            UPDATE users
            SET account_status = 'active',
                ban_until = NULL,
                ban_reason = NULL
            WHERE id = ?
            """,
            (user_id,)
        )

        connection.commit()

        flash(
            "User has been unbanned.",
            "success"
        )

    except sqlite3.Error as error:

        print(
            "UNBAN USER ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to unban the user.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_users")
    )


@app.route(
    "/admin/users/<int:user_id>/delete",
    methods=["POST"]
)
def admin_delete_user(user_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    try:

        # Get profile photo before deleting the database record
        user = connection.execute(
            """
            SELECT profile_photo
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        # Delete database record
        connection.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        connection.commit()

        # Delete profile photo from storage if it exists
        if user and user["profile_photo"]:

            photo_path = os.path.join(
                USER_UPLOAD_FOLDER,
                os.path.basename(
                    user["profile_photo"]
                )
            )

            if os.path.isfile(photo_path):
                os.remove(photo_path)

        flash(
            "User account has been deleted.",
            "success"
        )

    except sqlite3.Error as error:

        print(
            "DELETE USER ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to delete the user account.",
            "danger"
        )

    except OSError as error:

        print(
            "DELETE USER PHOTO ERROR:",
            error
        )

        flash(
            "User account deleted, but the profile photo could not be removed.",
            "warning"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_users")
    )


# ============================================================
# ADMIN — PROFESSIONAL ACCOUNT CONTROLS
# ============================================================

@app.route(
    "/admin/professionals/<int:professional_id>/temporary-ban",
    methods=["POST"]
)
def admin_temp_ban_professional(professional_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    # Get and validate ban duration
    duration = request.form.get("duration", "7").strip()

    allowed_durations = {
        "1": 1,
        "3": 3,
        "7": 7,
        "30": 30
    }

    if duration not in allowed_durations:

        flash(
            "Invalid temporary ban duration.",
            "danger"
        )

        return redirect(
            url_for("admin_professionals")
        )

    days = allowed_durations[duration]

    # Get optional reason
    reason = request.form.get("reason", "").strip()

    if not reason:
        reason = "Temporarily banned by administrator."

    connection = get_db_connection()

    try:

        connection.execute(
            """
            UPDATE professionals
            SET account_status = 'temporarily_banned',
                ban_until = datetime('now', ?),
                ban_reason = ?
            WHERE id = ?
            """,
            (
                f"+{days} days",
                reason,
                professional_id
            )
        )

        connection.commit()

        flash(
            f"Professional has been temporarily banned for {days} day(s).",
            "warning"
        )

    except sqlite3.Error as error:

        print(
            "TEMPORARY BAN PROFESSIONAL ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to temporarily ban the professional.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_professionals")
    )


@app.route(
    "/admin/professionals/<int:professional_id>/permanent-ban",
    methods=["POST"]
)
def admin_permanent_ban_professional(professional_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    # Get permanent ban reason
    reason = request.form.get("reason", "").strip()

    if not reason:

        flash(
            "Please enter a reason for the permanent ban.",
            "danger"
        )

        return redirect(
            url_for("admin_professionals")
        )

    connection = get_db_connection()

    try:

        connection.execute(
            """
            UPDATE professionals
            SET account_status = 'permanently_banned',
                ban_until = NULL,
                ban_reason = ?
            WHERE id = ?
            """,
            (
                reason,
                professional_id
            )
        )

        connection.commit()

        flash(
            "Professional has been permanently banned.",
            "danger"
        )

    except sqlite3.Error as error:

        print(
            "PERMANENT BAN PROFESSIONAL ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to permanently ban the professional.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_professionals")
    )


@app.route(
    "/admin/professionals/<int:professional_id>/unban",
    methods=["POST"]
)
def admin_unban_professional(professional_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    try:

        connection.execute(
            """
            UPDATE professionals
            SET account_status = 'active',
                ban_until = NULL,
                ban_reason = NULL
            WHERE id = ?
            """,
            (professional_id,)
        )

        connection.commit()

        flash(
            "Professional has been unbanned.",
            "success"
        )

    except sqlite3.Error as error:

        print(
            "UNBAN PROFESSIONAL ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to unban the professional.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_professionals")
    )


@app.route(
    "/admin/professionals/<int:professional_id>/delete",
    methods=["POST"]
)
def admin_delete_professional(professional_id):

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    try:

        # Get profile photo before deleting the record
        professional = connection.execute(
            """
            SELECT profile_photo
            FROM professionals
            WHERE id = ?
            """,
            (professional_id,)
        ).fetchone()

        # Delete professional
        connection.execute(
            """
            DELETE FROM professionals
            WHERE id = ?
            """,
            (professional_id,)
        )

        connection.commit()

        # Delete profile photo if it exists
        if (
            professional
            and professional["profile_photo"]
        ):

            photo_path = os.path.join(
                PROFESSIONAL_UPLOAD_FOLDER,
                os.path.basename(
                    professional["profile_photo"]
                )
            )

            if os.path.isfile(photo_path):
                os.remove(photo_path)

        flash(
            "Professional account has been deleted.",
            "success"
        )

    except sqlite3.Error as error:

        print(
            "DELETE PROFESSIONAL ERROR:",
            error
        )

        connection.rollback()

        flash(
            "Unable to delete the professional account.",
            "danger"
        )

    except OSError as error:

        print(
            "DELETE PROFESSIONAL PHOTO ERROR:",
            error
        )

        flash(
            "Account deleted, but the profile photo could not be removed.",
            "warning"
        )

    finally:

        connection.close()

    return redirect(
        url_for("admin_professionals")
    )


# ============================================================
# ADMIN — MANAGE
# ============================================================

@app.route("/admin/manage")
def admin_manage():
    """
    Admin management page.

    Provides access to user and professional management.
    """

    # --------------------------------------------------------
    # ADMIN AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    return render_template(
        "admin_manage.html"
    )

# ============================================================
# ADMIN — PROFESSIONALS
# ============================================================

@app.route("/admin/professionals")
def admin_professionals():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    try:

        professionals = connection.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                profile_photo,
                profession,
                category,
                experience,
                qualification,
                description,
                government_id_type,
                government_id_document,
                qualification_document,
                additional_document,
                verification_status,
                service_price,
                price_unit,
                location,
                service_area,
                start_time,
                end_time,
                role,
                created_at,
                account_status,
                ban_until,
                ban_reason
            FROM professionals
            ORDER BY created_at DESC
            """
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "ADMIN PROFESSIONALS DATABASE ERROR:",
            error
        )

        professionals = []

        flash(
            "Unable to load professionals.",
            "danger"
        )

    finally:

        connection.close()

    return render_template(
        "admin_professionals.html",
        professionals=professionals
    )

# ============================================================
# ADMIN — VERIFY PROFESSIONAL
# ============================================================

@app.route(
    "/admin/professionals/<int:professional_id>/verify",
    methods=["POST"]
)
def admin_verify_professional(professional_id):

    # --------------------------------------------------------
    # ADMIN AUTHENTICATION
    # --------------------------------------------------------

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    connection = get_db_connection()

    try:

        # ----------------------------------------------------
        # CHECK PROFESSIONAL
        # ----------------------------------------------------

        professional = connection.execute(
            """
            SELECT id, full_name, verification_status
            FROM professionals
            WHERE id = ?
            """,
            (professional_id,)
        ).fetchone()


        if professional is None:

            flash(
                "Professional not found.",
                "danger"
            )

            return redirect(
                url_for("admin_professionals")
            )


        # ----------------------------------------------------
        # VERIFY PROFESSIONAL
        # ----------------------------------------------------

        connection.execute(
            """
            UPDATE professionals
            SET verification_status = ?
            WHERE id = ?
            """,
            (
                "verified",
                professional_id
            )
        )


        connection.commit()


        flash(
            f"{professional['full_name']} has been verified successfully.",
            "success"
        )


    except sqlite3.Error as error:

        connection.rollback()

        print(
            "ADMIN VERIFY PROFESSIONAL ERROR:",
            error
        )

        flash(
            "Unable to verify professional.",
            "danger"
        )


    finally:

        connection.close()


    return redirect(
        url_for("admin_professionals")
    )

# ============================================================
# ADMIN — BOOKINGS
# ============================================================

@app.route("/admin/bookings")
def admin_bookings():
    """
    Display all bookings on the MATE platform.
    """

    # --------------------------------------------------------
    # ADMIN AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    connection = get_db_connection()

    try:

        bookings = connection.execute(
            """
            SELECT
                bookings.id,
                bookings.booking_date,
                bookings.booking_time,
                bookings.service,
                bookings.message,
                bookings.price,
                bookings.status,
                bookings.created_at,

                users.full_name AS user_name,
                users.email AS user_email,

                professionals.full_name AS professional_name,
                professionals.email AS professional_email,
                professionals.profession AS professional_profession

            FROM bookings

            LEFT JOIN users
                ON bookings.user_id = users.id

            LEFT JOIN professionals
                ON bookings.professional_id = professionals.id

            ORDER BY bookings.created_at DESC
            """
        ).fetchall()

    except sqlite3.Error as error:

        print(
            "ADMIN BOOKINGS DATABASE ERROR:",
            error
        )

        bookings = []

        flash(
            "Unable to load bookings.",
            "danger"
        )

    finally:

        connection.close()


    return render_template(
        "admin_bookings.html",
        bookings=bookings
    )

# ============================================================
# ADMIN — MESSAGES
# ============================================================

@app.route("/admin/messages")
def admin_messages():
    """
    Display contact messages for the admin.
    """

    # --------------------------------------------------------
    # ADMIN AUTHENTICATION CHECK
    # --------------------------------------------------------

    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )


    connection = get_db_connection()

    try:

        messages = connection.execute(
            """
            SELECT
                id,
                name,
                email,
                subject,
                message,
                is_read,
                created_at

            FROM contact_messages

            ORDER BY created_at DESC
            """
        ).fetchall()


    except sqlite3.Error as error:

        print(
            "ADMIN MESSAGES DATABASE ERROR:",
            error
        )

        messages = []

        flash(
            "Unable to load messages.",
            "danger"
        )


    finally:

        connection.close()


    return render_template(
        "admin_messages.html",
        messages=messages
    )

# ============================================================
# TEMPORARY PAYMENT BYPASS — TESTING ONLY
# ============================================================

@app.route("/payment/<int:booking_id>/test", methods=["POST"])
def test_payment(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        flash("Only users can make payments.", "danger")
        return redirect(url_for("index"))

    connection = get_db_connection()

    try:

        booking = connection.execute(
            """
            SELECT id, status
            FROM bookings
            WHERE id = ?
              AND user_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        ).fetchone()

        if booking is None:
            flash("Booking not found.", "danger")
            return redirect(url_for("booking_history"))

        if booking["status"].lower() != "accepted":
            flash("Only accepted bookings can be confirmed.", "warning")
            return redirect(url_for("booking_history"))

        connection.execute(
            """
            UPDATE bookings
            SET status = 'confirmed'
            WHERE id = ?
              AND user_id = ?
            """,
            (
                booking_id,
                session["user_id"]
            )
        )

        connection.commit()

        flash(
            "TEST PAYMENT: Booking confirmed successfully.",
            "success"
        )

    except sqlite3.Error as error:

        connection.rollback()

        print("TEST PAYMENT ERROR:", error)

        flash(
            "Unable to confirm test payment.",
            "danger"
        )

    finally:

        connection.close()

    return redirect(
        url_for("booking_history")
    )

# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def page_not_found(error):
    """
    Handle unknown URLs.
    """

    return render_template(
        "index.html"
    ), 404


# ============================================================
# 413 ERROR
# ============================================================

@app.errorhandler(413)
def file_too_large(error):
    """
    Handle files larger than 5 MB.
    """

    flash(
        "The uploaded file is too large. Maximum size is 5 MB.",
        "danger"
    )

    return redirect(
        request.referrer
        or url_for("index")
    )



print("\n========== MATE ROUTES ==========")

for rule in app.url_map.iter_rules():
    print(
        f"{rule.endpoint:30} -> {rule}"
    )

print("================================\n")


# ============================================================
# DEVELOPMENT SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)

    print(
        "MATE — Hire a Professional"
    )

    print("=" * 60)

    print(
        f"Database: {DATABASE}"
    )


    if database_is_available():

        print(
            "Database connection: OK"
        )

    else:

        print(
            "Database connection: FAILED"
        )


    print("=" * 60)


    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )