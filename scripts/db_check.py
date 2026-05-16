import os, sqlite3, json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'database.db')
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
print('resident_requests columns:', [row['name'] for row in conn.execute("PRAGMA table_info(resident_requests)").fetchall()])
print('certificates columns:', [row['name'] for row in conn.execute("PRAGMA table_info(certificates)").fetchall()])
conn.close()
