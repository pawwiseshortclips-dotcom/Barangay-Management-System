import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')

if not os.path.exists(DB_PATH):
    print('Database not found:', DB_PATH)
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
count = cur.execute("SELECT COUNT(*) FROM resident_requests WHERE LOWER(request_type)='attendance'").fetchone()[0]
if count > 0:
    cur.execute("DELETE FROM resident_requests WHERE LOWER(request_type)='attendance'")
    conn.commit()
    print(f'Deleted {count} resident_requests rows with request_type=Attendance')
else:
    print('No attendance rows found in resident_requests')
conn.close()
