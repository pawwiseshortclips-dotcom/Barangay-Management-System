import sqlite3
import os
DB = os.path.join(os.path.dirname(__file__), '..', 'database.db')
DB = os.path.normpath(DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('Recent resident_requests (id, name, request_type, status, tracking_code, date):')
for row in cur.execute("SELECT id, name, request_type, status, tracking_code, date FROM resident_requests ORDER BY id DESC LIMIT 100"):
    print(row)
conn.close()
