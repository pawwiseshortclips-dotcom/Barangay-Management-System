import sqlite3

def create_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create residents table
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

    # Create certificates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resident_id INTEGER,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            request_date TEXT,
            FOREIGN KEY (resident_id) REFERENCES residents (id)
        )
    ''')

    # Create announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT
        )
    ''')

    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            resident_id INTEGER,
            status TEXT,
            approval_status TEXT DEFAULT 'Pending',
            date TEXT,
            FOREIGN KEY (resident_id) REFERENCES residents (id)
        )
    ''')

    # Create users table for simple login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Create resident requests table for public resident submissions
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
            date TEXT
        )
    ''')

    # Insert default admin user (password: admin123, hashed with werkzeug)
    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash('admin123')
    cursor.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', ('admin', hashed_password))

    conn.commit()
    conn.close()
    print("Database created successfully!")

if __name__ == '__main__':
    create_database()
