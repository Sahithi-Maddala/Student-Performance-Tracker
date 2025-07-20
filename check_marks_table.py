import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

cur.execute("PRAGMA table_info(marks);")
columns = cur.fetchall()

print("📄 Columns in 'marks' table:")
for col in columns:
    print(f"{col[1]} ({col[2]})")

conn.close()
