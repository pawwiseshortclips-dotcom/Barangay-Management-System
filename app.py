from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from werkzeug.security import check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production
app.template_folder = 'templetes'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('index.html', announcements=announcements)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/residents')
@login_required
def residents():
    conn = get_db_connection()
    residents = conn.execute('SELECT * FROM residents').fetchall()
    conn.close()
    return render_template('residents.html', residents=residents)

@app.route('/add_resident', methods=['GET', 'POST'])
@login_required
def add_resident():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        contact = request.form['contact']
        conn = get_db_connection()
        conn.execute('INSERT INTO residents (name, age, address, contact) VALUES (?, ?, ?, ?)',
                     (name, age, address, contact))
        conn.commit()
        conn.close()
        flash('Resident added successfully!')
        return redirect(url_for('residents'))
    return render_template('add_resident.html')

@app.route('/certificates')
@login_required
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

@app.route('/request_certificate', methods=['POST'])
@login_required
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

@app.route('/update_certificate/<int:id>', methods=['POST'])
@login_required
def update_certificate(id):
    status = request.form['status']
    conn = get_db_connection()
    conn.execute('UPDATE certificates SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()
    flash('Certificate status updated!')
    return redirect(url_for('certificates'))

@app.route('/announcements')
@login_required
def announcements():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('announcements.html', announcements=announcements)

@app.route('/add_announcement', methods=['POST'])
@login_required
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

@app.route('/attendance')
@login_required
def attendance():
    conn = get_db_connection()
    attendance_records = conn.execute('''
        SELECT a.*, r.name as resident_name
        FROM attendance a
        JOIN residents r ON a.resident_id = r.id
        ORDER BY a.date DESC
    ''').fetchall()
    residents = conn.execute('SELECT id, name FROM residents').fetchall()
    conn.close()
    return render_template('attendance.html', attendance=attendance_records, residents=residents)

@app.route('/add_attendance', methods=['POST'])
@login_required
def add_attendance():
    event_name = request.form['event_name']
    resident_id = request.form['resident_id']
    status = request.form['status']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    conn.execute('INSERT INTO attendance (event_name, resident_id, status, date) VALUES (?, ?, ?, ?)',
                 (event_name, resident_id, status, date))
    conn.commit()
    conn.close()
    flash('Attendance recorded successfully!')
    return redirect(url_for('attendance'))

if __name__ == '__main__':
    app.run(debug=True)
