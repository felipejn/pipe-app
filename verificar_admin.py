import sqlite3, os

db = os.path.join('instance', 'pipe.db')
conn = sqlite3.connect(db)
for row in conn.execute('SELECT id, username, is_admin FROM utilizadores'):
    print(row)
conn.close()