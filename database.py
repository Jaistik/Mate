import sqlite3
import os
from werkzeug.security import generate_password_hash

# =========================================================
# DATABASE CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "mate.db")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    """
    Create and return a SQLite database connection.
    """

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    # Enable foreign-key relationships
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# =========================================================
# CREATE DATABASE
# =========================================================

def init_db():

    connection = get_db_connection()

    cursor = connection.cursor()


    # =====================================================
    # USERS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            full_name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            phone TEXT,

            password TEXT NOT NULL,

            location TEXT,

            address TEXT,

            profile_photo TEXT,

            role TEXT NOT NULL DEFAULT 'user',

            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes'))

        )
    """)


    # =====================================================
    # PROFESSIONALS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS professionals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            full_name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            phone TEXT,

            password TEXT NOT NULL,

            profile_photo TEXT,

            profession TEXT,

            category TEXT,

            experience INTEGER DEFAULT 0,

            qualification TEXT,

            description TEXT,

            government_id_type TEXT,

            government_id_document TEXT,

            qualification_document TEXT,

            additional_document TEXT,

            verification_status TEXT DEFAULT 'pending',

            service_price REAL DEFAULT 0,

            price_unit TEXT DEFAULT 'hour',

            location TEXT,

            service_area TEXT,

            start_time TEXT,

            end_time TEXT,

            role TEXT NOT NULL DEFAULT 'professional',

            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes'))

        )
    """)


    # =====================================================
    # PROFESSIONAL AVAILABILITY
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS professional_availability (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            professional_id INTEGER NOT NULL,

            day_of_week TEXT NOT NULL,

            is_available INTEGER DEFAULT 1,

            FOREIGN KEY (professional_id)
                REFERENCES professionals(id)
                ON DELETE CASCADE,

            UNIQUE (
                professional_id,
                day_of_week
            )

        )
    """)


    # =====================================================
    # BOOKINGS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            professional_id INTEGER NOT NULL,

            booking_date TEXT NOT NULL,

            booking_time TEXT NOT NULL,

            service TEXT NOT NULL,

            message TEXT,

            price REAL DEFAULT 0,

            status TEXT DEFAULT 'pending',

            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes')),

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (professional_id)
                REFERENCES professionals(id)
                ON DELETE CASCADE

        )
    """)


    # =====================================================
    # REVIEWS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            professional_id INTEGER NOT NULL,

            booking_id INTEGER,

            rating INTEGER NOT NULL,

            review_text TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (professional_id)
                REFERENCES professionals(id)
                ON DELETE CASCADE,

            FOREIGN KEY (booking_id)
                REFERENCES bookings(id)
                ON DELETE SET NULL,

            CHECK (
                rating >= 1
                AND rating <= 5
            )

        )
    """)


    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            professional_id INTEGER,

            title TEXT NOT NULL,

            message TEXT NOT NULL,

            is_read INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes')),

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (professional_id)
                REFERENCES professionals(id)
                ON DELETE CASCADE

        )
    """)

    # =====================================================
    # ADMINS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes'))

        )
    """)


    # =====================================================
    # CONTACT MESSAGES
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL,

            subject TEXT NOT NULL,

            message TEXT NOT NULL,

            is_read INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '+30 minutes'))

        )
    """)

    # =====================================================
    # INDEXES
    # =====================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_bookings_user
        ON bookings(user_id)
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_bookings_professional
        ON bookings(professional_id)
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_reviews_professional
        ON reviews(professional_id)
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_notifications_user
        ON notifications(user_id)
    """)


    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_notifications_professional
        ON notifications(professional_id)
    """)

    # =====================================================
    # ACCOUNT STATUS / BAN FIELDS
    # =====================================================

    # Users
    try:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN account_status TEXT DEFAULT 'active'
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN ban_until TEXT
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN ban_reason TEXT
        """)
    except sqlite3.OperationalError:
        pass


    # Professionals
    try:
        cursor.execute("""
            ALTER TABLE professionals
            ADD COLUMN account_status TEXT DEFAULT 'active'
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE professionals
            ADD COLUMN ban_until TEXT
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE professionals
            ADD COLUMN ban_reason TEXT
        """)
    except sqlite3.OperationalError:
        pass


        # =====================================================
    # PAYMENT FIELDS
    # =====================================================

    try:
        cursor.execute("""
            ALTER TABLE bookings
            ADD COLUMN razorpay_order_id TEXT
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE bookings
            ADD COLUMN razorpay_payment_id TEXT
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE bookings
            ADD COLUMN payment_status TEXT DEFAULT 'pending'
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE bookings
            ADD COLUMN paid_at TEXT
        """)
    except sqlite3.OperationalError:
        pass


    

    # =====================================================
    # SAVE CHANGES
    # =====================================================

    connection.commit()

    connection.close()

# =========================================================
# RUN DATABASE INITIALIZATION
# =========================================================

if __name__ == "__main__":

    init_db()

    print("MATE database initialized successfully.")