import sqlite3
from app import app, DB_PATH

client = app.test_client()

r = client.get('/')
print('GET / ->', r.status_code)

post_data = {
    'name': 'Test User',
    'age': '30',
    'address': '123 Test St',
    'contact': '09171234567',
    'email': 'testuser@example.com',
    'request_type': 'Certificate',
    'message': 'Testing request'
}

r2 = client.post('/resident_portal', data=post_data, follow_redirects=True)
print('POST /resident_portal ->', r2.status_code)

# Check DB entries
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
try:
    cur.execute('SELECT COUNT(*) FROM resident_requests')
    count = cur.fetchone()[0]
except Exception as e:
    print('DB check failed:', e)
    count = None
conn.close()
print('resident_requests count ->', count)
