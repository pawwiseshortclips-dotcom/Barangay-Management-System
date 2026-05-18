import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS residents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            address TEXT,
            contact TEXT,
            email TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resident_id INTEGER,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            request_date TEXT,
            tracking_code TEXT,
            approved_date TEXT,
            sequence_number INTEGER,
            FOREIGN KEY (resident_id) REFERENCES residents (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resident_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            address TEXT,
            contact TEXT,
            email TEXT,
            request_type TEXT,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            date TEXT,
            tracking_code TEXT,
            approved_date TEXT,
            sequence_number INTEGER
        )
    ''')

    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash('admin123')
    cursor.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', ('admin', hashed_password))

    conn.commit()
    conn.close()
    print('Database created successfully!')


if __name__ == '__main__':
    create_database()
