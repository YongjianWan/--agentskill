import sqlite3
import json

conn = sqlite3.connect('data/meetings.db')
cursor = conn.cursor()

# 查看表结构
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('Tables:', tables)

# 查看 meetings 表
try:
    cursor.execute('SELECT * FROM meetings LIMIT 5;')
    rows = cursor.fetchall()
    print('\nMeetings data:')
    for row in rows:
        print(row)
except Exception as e:
    print('Error:', e)

conn.close()
