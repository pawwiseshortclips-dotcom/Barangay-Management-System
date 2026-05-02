from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import smtplib
from email.message import EmailMessage
from datetime import datetime
from werkzeug.security import check_password_hash
from functools import wraps

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


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
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
            date TEXT
        )
    ''')
    columns = [row['name'] for row in conn.execute("PRAGMA table_info(resident_requests)").fetchall()]
    if 'status' not in columns:
        conn.execute("ALTER TABLE resident_requests ADD COLUMN status TEXT DEFAULT 'Pending'")
    if 'email' not in columns:
        conn.execute("ALTER TABLE resident_requests ADD COLUMN email TEXT")

    conn.execute('''
        CREATE TABLE IF NOT EXISTS residents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            address TEXT,
            contact TEXT
        )
    ''')
    resident_columns = [row['name'] for row in conn.execute("PRAGMA table_info(residents)").fetchall()]
    if 'email' not in resident_columns:
        conn.execute("ALTER TABLE residents ADD COLUMN email TEXT")

    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            resident_id INTEGER,
            status TEXT,
            date TEXT,
            FOREIGN KEY (resident_id) REFERENCES residents (id)
        )
    ''')
    attendance_columns = [row['name'] for row in conn.execute("PRAGMA table_info(attendance)").fetchall()]
    if 'approval_status' not in attendance_columns:
        conn.execute("ALTER TABLE attendance ADD COLUMN approval_status TEXT DEFAULT 'Pending'")

    conn.commit()
    return conn

def admin_login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get('admin_logged_in'):
            return f(*args, **kwargs)
        else:
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
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('index'))

@app.route('/admin')
@admin_login_required
def admin_dashboard():
    return redirect(url_for('residents'))

@app.route('/admin/residents')
@admin_login_required
def residents():
    conn = get_db_connection()
    residents = conn.execute('SELECT * FROM residents').fetchall()
    conn.close()
    return render_template('residents.html', residents=residents)

@app.route('/admin/add_resident', methods=['GET', 'POST'])
@admin_login_required
def add_resident():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        contact = request.form['contact']
        email = request.form['email']
        conn = get_db_connection()
        conn.execute('INSERT INTO residents (name, age, address, contact, email) VALUES (?, ?, ?, ?, ?)',
                     (name, age, address, contact, email))
        conn.commit()
        conn.close()
        flash('Resident added successfully!')
        return redirect(url_for('residents'))
    return render_template('add_resident.html')

@app.route('/admin/certificates')
@admin_login_required
def certificates():
    conn = get_db_connection()
    certificates = conn.execute('''
        SELECT c.*, r.name as resident_name
        FROM certificates c
        JOIN residents r ON c.resident_id = r.id
        ORDER BY c.request_date DESC
    ''').fetchall()
    residents = conn.execute('SELECT id, name FROM residents').fetchall()
    conn.close()
    return render_template('certificates.html', certificates=certificates, residents=residents)

@app.route('/admin/request_certificate', methods=['POST'])
@admin_login_required
def request_certificate():
    resident_id = request.form['resident_id']
    cert_type = request.form['type']
    request_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    conn.execute('INSERT INTO certificates (resident_id, type, request_date) VALUES (?, ?, ?)',
                 (resident_id, cert_type, request_date))
    conn.commit()
    conn.close()
    flash('Certificate requested successfully!')
    return redirect(url_for('certificates'))

@app.route('/admin/update_certificate/<int:id>', methods=['POST'])
@admin_login_required
def update_certificate(id):
    status = request.form['status']
    conn = get_db_connection()
    conn.execute('UPDATE certificates SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()
    flash('Certificate status updated!')
    return redirect(url_for('certificates'))

@app.route('/admin/announcements')
@admin_login_required
def announcements():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('announcements.html', announcements=announcements)

@app.route('/admin/add_announcement', methods=['POST'])
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

@app.route('/admin/attendance/<int:id>/approval', methods=['POST'])
@admin_login_required
def update_attendance_approval(id):
    action = request.form.get('action')
    approval_status = 'Approved' if action == 'approve' else 'Declined'
    conn = get_db_connection()
    attendance_record = conn.execute('''
        SELECT a.event_name, a.status, r.name, r.email
        FROM attendance a
        JOIN residents r ON a.resident_id = r.id
        WHERE a.id = ?
    ''', (id,)).fetchone()
    if attendance_record:
        conn.execute('UPDATE attendance SET approval_status = ? WHERE id = ?', (approval_status, id))
        conn.commit()
        if attendance_record['email']:
            subject = f'Attendance {approval_status} for {attendance_record["event_name"]}'
            body = (
                f'Hello {attendance_record["name"]},\n\n'
                f'Your attendance for "{attendance_record["event_name"]}" has been {approval_status.lower()}.\n'
                f'Record status: {attendance_record["status"]}.\n\n'
                'Thank you,\nBarangay Office'
            )
            send_email_notification(attendance_record['email'], subject, body)
        flash(f'Attendance {approval_status.lower()} and notification sent.')
    else:
        flash('Attendance record not found.')
    conn.close()
    return redirect(url_for('attendance'))

@app.route('/admin/attendance')
@admin_login_required
def attendance():
    conn = get_db_connection()
    attendance_records = conn.execute('''
        SELECT a.*, r.name as resident_name, r.email as resident_email
        FROM attendance a
        JOIN residents r ON a.resident_id = r.id
        ORDER BY a.date DESC
    ''').fetchall()
    residents = conn.execute('SELECT id, name FROM residents').fetchall()
    conn.close()
    return render_template('attendance.html', attendance=attendance_records, residents=residents)

@app.route('/admin/add_attendance', methods=['POST'])
@admin_login_required
def add_attendance():
    event_name = request.form['event_name']
    resident_id = request.form['resident_id']
    status = request.form['status']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    conn.execute('INSERT INTO attendance (event_name, resident_id, status, approval_status, date) VALUES (?, ?, ?, ?, ?)',
                 (event_name, resident_id, status, 'Pending', date))
    conn.commit()
    conn.close()
    flash('Attendance recorded successfully and awaits approval!')
    return redirect(url_for('attendance'))

@app.route('/resident_portal', methods=['GET', 'POST'])
def resident_portal():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        contact = request.form['contact']
        email = request.form['email']
        request_type = request.form['request_type']
        message = request.form['message']
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        conn.execute('INSERT INTO resident_requests (name, age, address, contact, email, request_type, message, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (name, age, address, contact, email, request_type, message, date))
        conn.commit()
        conn.close()
        flash('Your request has been submitted. The barangay office will respond soon.')
        return redirect(url_for('resident_portal'))
    return render_template('resident_request.html')

@app.route('/admin/resident_requests')
@admin_login_required
def resident_requests():
    selected_type = request.args.get('type')
    conn = get_db_connection()
    if selected_type:
        requests = conn.execute(
            'SELECT * FROM resident_requests WHERE request_type = ? ORDER BY date DESC',
            (selected_type,)
        ).fetchall()
    else:
        requests = conn.execute('SELECT * FROM resident_requests ORDER BY date DESC').fetchall()

    request_types = conn.execute(
        'SELECT request_type, COUNT(*) as count FROM resident_requests GROUP BY request_type'
    ).fetchall()
    conn.close()
    return render_template(
        'resident_requests.html',
        requests=requests,
        selected_type=selected_type,
        request_types=request_types
    )

@app.route('/admin/resident_requests/<int:id>/status', methods=['POST'])
@admin_login_required
def update_resident_request_status(id):
    action = request.form.get('action')
    status = 'Approved' if action == 'approve' else 'Declined'
    selected_type = request.form.get('selected_type')
    conn = get_db_connection()
    row = conn.execute('SELECT email, name, request_type FROM resident_requests WHERE id = ?', (id,)).fetchone()
    if row:
        conn.execute('UPDATE resident_requests SET status = ? WHERE id = ?', (status, id))
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
    flash(f'Request {status.lower()} successfully.')
    return redirect(url_for('resident_requests', type=selected_type) if selected_type else url_for('resident_requests'))

if __name__ == '__main__':
    app.run(debug=True)
