import sqlite3, os

db = os.path.join('instance', 'pipe.db')
conn = sqlite3.connect(db)
conn.execute("UPDATE utilizadores SET is_admin = 1 WHERE username = 'felipejn'")
conn.commit()

for row in conn.execute('SELECT id, username, is_admin FROM utilizadores'):
    print(row)

conn.close()
print("Feito.")