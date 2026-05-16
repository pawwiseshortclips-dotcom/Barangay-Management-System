from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import re
import sqlite3
import smtplib
from email.message import EmailMessage
from datetime import datetime
from werkzeug.security import check_password_hash
from functools import wraps
import os
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production
app.template_folder = 'templetes'

# Email notification settings: configure for your SMTP server
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-email-password'
EMAIL_USE_TLS = True


def send_email_notification(to_address, subject, body):
    if not to_address:
        return
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = to_address
        msg.set_content(body)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
            if EMAIL_USE_TLS:
                smtp.starttls()
            if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
                smtp.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print(f'Email send failed: {e}')


def clean_text(value):
    return value.strip() if value and isinstance(value, str) else None


def normalize_name(name):
    cleaned = clean_text(name)
    return cleaned.title() if cleaned else None


def normalize_email(email):
    cleaned = clean_text(email)
    return cleaned.lower() if cleaned else None


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS residents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            address TEXT,
            contact TEXT,
            email TEXT
        )
    ''')

    conn.execute('''
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

    conn.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT
        )
    ''')

    conn.execute('''
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

    columns = [row['name'] for row in conn.execute("PRAGMA table_info(resident_requests)").fetchall()]
    if 'tracking_code' not in columns:
        conn.execute("ALTER TABLE resident_requests ADD COLUMN tracking_code TEXT")
    if 'approved_date' not in columns:
        conn.execute("ALTER TABLE resident_requests ADD COLUMN approved_date TEXT")
    if 'sequence_number' not in columns:
        conn.execute("ALTER TABLE resident_requests ADD COLUMN sequence_number INTEGER")

    cert_columns = [row['name'] for row in conn.execute("PRAGMA table_info(certificates)").fetchall()]
    if 'tracking_code' not in cert_columns:
        conn.execute("ALTER TABLE certificates ADD COLUMN tracking_code TEXT")
    if 'approved_date' not in cert_columns:
        conn.execute("ALTER TABLE certificates ADD COLUMN approved_date TEXT")
    if 'sequence_number' not in cert_columns:
        conn.execute("ALTER TABLE certificates ADD COLUMN sequence_number INTEGER")

    resident_columns = [row['name'] for row in conn.execute("PRAGMA table_info(residents)").fetchall()]
    if 'email' not in resident_columns:
        conn.execute("ALTER TABLE residents ADD COLUMN email TEXT")

    conn.commit()
    return conn


@app.context_processor
def inject_pending_requests_count():
    try:
        conn = get_db_connection()
        count = conn.execute(
            "SELECT COUNT(*) as count FROM resident_requests WHERE status IS NULL OR status = 'Pending'"
        ).fetchone()['count']
        conn.close()
    except Exception:
        count = 0
    return {'pending_requests_count': count}


def admin_login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get('admin_logged_in') or session.get('logged_in'):
            return f(*args, **kwargs)
        flash('Admin login required.')
        return redirect(url_for('admin_login'))
    return wrap


@app.route('/')
def index():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('index.html', announcements=announcements)


@app.route('/login')
def login_redirect():
    return redirect(url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['admin_logged_in'] = True
            session['logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')


@app.route('/admin/logout')
@app.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('index'))


@app.route('/admin')
@admin_login_required
def admin_dashboard():
    return redirect(url_for('resident_requests'))


@app.route('/residents')
@admin_login_required
def residents():
    conn = get_db_connection()
    residents = conn.execute('SELECT * FROM residents').fetchall()
    conn.close()
    return render_template('residents.html', residents=residents)


@app.route('/add_resident', methods=['GET', 'POST'])
@admin_login_required
def add_resident():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        contact = request.form['contact']
        conn = get_db_connection()
        conn.execute('INSERT INTO residents (name, age, address, contact, email) VALUES (?, ?, ?, ?, ?)',
                     (name, age, address, contact, None))
        conn.commit()
        conn.close()
        flash('Resident added successfully!')
        return redirect(url_for('residents'))
    return render_template('add_resident.html')


@app.route('/admin/certificates')
@app.route('/certificates')
@admin_login_required
def certificates():
    conn = get_db_connection()
    certificates = conn.execute('''
        SELECT c.*, r.name as resident_name
        FROM certificates c
        JOIN residents r ON c.resident_id = r.id
        ORDER BY c.request_date DESC
    ''').fetchall()
    conn.close()
    return render_template('certificates.html', certificates=certificates)


@app.route('/admin/search_residents')
@admin_login_required
def search_residents():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    if query:
        rows = conn.execute(
            'SELECT id, name FROM residents WHERE name LIKE ? ORDER BY name LIMIT 10',
            ('%' + query + '%',)
        ).fetchall()
    else:
        rows = conn.execute('SELECT id, name FROM residents ORDER BY name LIMIT 10').fetchall()
    conn.close()
    return jsonify([{'id': row['id'], 'name': row['name']} for row in rows])


@app.route('/admin/update_certificate/<int:id>', methods=['POST'])
@app.route('/update_certificate/<int:id>', methods=['POST'])
@admin_login_required
def update_certificate(id):
    status = request.form['status']
    conn = get_db_connection()
    conn.execute('UPDATE certificates SET status = ? WHERE id = ?', (status, id))
    if status == 'Approved':
        seq_row = conn.execute('SELECT sequence_number FROM certificates WHERE id = ?', (id,)).fetchone()
        if not seq_row or seq_row['sequence_number'] is None:
            seq = conn.execute("SELECT COUNT(*) as cnt FROM certificates WHERE status = 'Approved'").fetchone()['cnt'] + 1
            approved_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('UPDATE certificates SET approved_date = ?, sequence_number = ? WHERE id = ?', (approved_date, seq, id))
    conn.commit()
    conn.close()
    flash('Certificate status updated!')
    return redirect(url_for('certificates'))


@app.route('/admin/announcements')
@app.route('/announcements')
@admin_login_required
def announcements():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('announcements.html', announcements=announcements)


@app.route('/track', methods=['GET', 'POST'])
def track():
    result = None
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not code:
            flash('Please enter a tracking code.')
            return render_template('track.html')
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM resident_requests WHERE tracking_code = ? LIMIT 1', (code,)).fetchone()
        if row:
            result = dict(row)
            conn.close()
            return render_template('track.html', result=result)
        row = conn.execute('SELECT c.*, r.name as resident_name FROM certificates c JOIN residents r ON c.resident_id = r.id WHERE c.tracking_code = ? LIMIT 1', (code,)).fetchone()
        conn.close()
        if row:
            result = dict(row)
            return render_template('track.html', result=result)
        flash('Tracking code not found. Please check and try again.')
    return render_template('track.html')


@app.route('/admin/add_announcement', methods=['POST'])
@app.route('/add_announcement', methods=['POST'])
@admin_login_required
def add_announcement():
    title = request.form['title']
    description = request.form['description']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    conn.execute('INSERT INTO announcements (title, description, date) VALUES (?, ?, ?)',
                 (title, description, date))
    conn.commit()
    conn.close()
    flash('Announcement added successfully!')
    return redirect(url_for('announcements'))


@app.route('/admin/announcements/<int:id>/delete', methods=['POST'])
@app.route('/announcements/<int:id>/delete', methods=['POST'])
@admin_login_required
def delete_announcement(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM announcements WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Announcement deleted successfully.')
    return redirect(url_for('announcements'))


@app.route('/resident_portal', methods=['GET', 'POST'])
def resident_portal():
    if request.method == 'POST':
        name = normalize_name(request.form.get('name'))
        age = request.form.get('age')
        age = int(age) if age and age.isdigit() else None
        address = clean_text(request.form.get('address'))
        contact = clean_text(request.form.get('contact'))
        email = normalize_email(request.form.get('email'))
        request_type = clean_text(request.form.get('request_type'))
        message = clean_text(request.form.get('message'))
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Enforce name format: First [M.] Last (middle initial optional)
        name_raw = request.form.get('name', '').strip()
        name_pattern = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+(?:\s+[A-Za-z](?:\.)?)?\s+[A-Za-z][A-Za-z\s'-]*$")
        if not name_pattern.match(name_raw):
            flash('Invalid name format. Use: FIRST [M.] LAST (middle initial optional).')
            return render_template('resident_request.html', tracking_code=None)
        tracking_code = uuid.uuid4().hex[:8].upper()
        conn = get_db_connection()
        conn.execute('INSERT INTO resident_requests (name, age, address, contact, email, request_type, message, date, tracking_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     (name, age, address, contact, email, request_type, message, date, tracking_code))
        if request_type and 'certificate' in request_type.lower():
            resident = conn.execute('SELECT id FROM residents WHERE name = ? AND email = ?', (name, email)).fetchone()
            resident_id = None
            if resident:
                resident_id = resident['id']
            else:
                conn.execute('INSERT INTO residents (name, age, address, contact, email) VALUES (?, ?, ?, ?, ?)',
                             (name, age, address, contact, email))
                resident_id = conn.execute('SELECT id FROM residents WHERE name = ? AND email = ?', (name, email)).fetchone()['id']
            conn.execute('INSERT INTO certificates (resident_id, type, status, request_date, tracking_code) VALUES (?, ?, ?, ?, ?)',
                         (resident_id, request_type, 'Pending', date, tracking_code))
        conn.commit()
        conn.close()
        session['tracking_code'] = tracking_code
        flash('Your request has been submitted. Copy the tracking code below to track your request status.')
        return redirect(url_for('resident_portal'))
    tracking_code = session.pop('tracking_code', None)
    return render_template('resident_request.html', tracking_code=tracking_code)


@app.route('/admin/resident_requests')
@app.route('/resident_requests')
@admin_login_required
def resident_requests():
    selected_type = request.args.get('type')
    selected_status = request.args.get('status')
    query = 'SELECT * FROM resident_requests'
    filters = []
    params = []
    allowed_certificate_types = [
        'Certificate of Clearance',
        'Certificate of Indigency',
        'Cedula',
        'Certificate of Residency'
    ]

    if selected_type:
        if selected_type == 'Other':
            placeholders = ','.join('?' for _ in allowed_certificate_types)
            filters.append(f'request_type NOT IN ({placeholders})')
            params.extend(allowed_certificate_types)
        else:
            filters.append('request_type = ?')
            params.append(selected_type)
    if selected_status:
        filters.append('status = ?')
        params.append(selected_status)

    if filters:
        query += ' WHERE ' + ' AND '.join(filters)
    query += ' ORDER BY date DESC'

    conn = get_db_connection()
    requests = conn.execute(query, params).fetchall()

    type_counts = {row['request_type']: row['count'] for row in conn.execute(
        'SELECT request_type, COUNT(*) as count FROM resident_requests GROUP BY request_type'
    ).fetchall()}
    request_types = [
        {'request_type': certificate_type, 'count': type_counts.get(certificate_type, 0)}
        for certificate_type in allowed_certificate_types
    ]
    other_count = sum(
        count for type_name, count in type_counts.items()
        if type_name not in allowed_certificate_types
    )
    conn.close()
    return render_template(
        'resident_requests.html',
        requests=requests,
        selected_type=selected_type,
        selected_status=selected_status,
        request_types=request_types,
        other_count=other_count
    )


@app.route('/admin/resident_requests/<int:id>/status', methods=['POST'])
@app.route('/resident_requests/<int:id>/status', methods=['POST'])
@admin_login_required
def update_resident_request_status(id):
    action = request.form.get('action')
    status = 'Approved' if action == 'approve' else 'Declined'
    selected_type = request.form.get('selected_type')
    selected_status = request.form.get('selected_status')
    conn = get_db_connection()
    row = conn.execute('SELECT email, name, request_type, tracking_code FROM resident_requests WHERE id = ?', (id,)).fetchone()
    if row:
        conn.execute('UPDATE resident_requests SET status = ? WHERE id = ?', (status, id))
        if status == 'Approved':
            seq_row = conn.execute('SELECT sequence_number FROM resident_requests WHERE id = ?', (id,)).fetchone()
            if not seq_row or seq_row['sequence_number'] is None:
                seq = conn.execute("SELECT COUNT(*) as cnt FROM resident_requests WHERE status = 'Approved'").fetchone()['cnt'] + 1
                approved_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('UPDATE resident_requests SET approved_date = ?, sequence_number = ? WHERE id = ?', (approved_date, seq, id))
        if row['request_type'] and 'certificate' in row['request_type'].lower() and row['tracking_code']:
            conn.execute('UPDATE certificates SET status = ? WHERE tracking_code = ?', (status, row['tracking_code']))
        conn.commit()
        if row['email']:
            subject = f'Your Barangay Request #{id} has been {status}'
            body = (
                f'Hello {row["name"]},\n\n'
                f'Your {row["request_type"]} request has been {status.lower()}.\n\n'
                'Thank you,\nBarangay Office'
            )
            send_email_notification(row['email'], subject, body)
    conn.close()
    redirect_args = {}
    if selected_type:
        redirect_args['type'] = selected_type
    if selected_status:
        redirect_args['status'] = selected_status
    return redirect(url_for('resident_requests', **redirect_args) if redirect_args else url_for('resident_requests'))


@app.route('/admin/resident_requests/<int:id>/delete', methods=['POST'])
@app.route('/resident_requests/<int:id>/delete', methods=['POST'])
@admin_login_required
def delete_resident_request(id):
    selected_type = request.form.get('selected_type')
    selected_status = request.form.get('selected_status')
    conn = get_db_connection()
    row = conn.execute('SELECT tracking_code FROM resident_requests WHERE id = ?', (id,)).fetchone()
    if row:
        tracking_code = row['tracking_code']
        conn.execute('DELETE FROM resident_requests WHERE id = ?', (id,))
        if tracking_code:
            conn.execute('DELETE FROM certificates WHERE tracking_code = ?', (tracking_code,))
        conn.commit()
        flash('Request deleted successfully.')
    conn.close()
    redirect_args = {}
    if selected_type:
        redirect_args['type'] = selected_type
    if selected_status:
        redirect_args['status'] = selected_status
    return redirect(url_for('resident_requests', **redirect_args) if redirect_args else url_for('resident_requests'))


if __name__ == '__main__':
    app.run(debug=True)
