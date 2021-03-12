import pymysql
import csv
import sys

db_opts = {
    'user': 'martin',
    'password': 'martinjs',
    'host': 'localhost',
    'database': 'torque_db'
}

db = pymysql.connect(**db_opts)
cur = db.cursor()

sql = 'select * from export_csv;'

csv_file_path = 'my_csv_file.csv'

try:
    cur.execute(sql)
    rows = cur.fetchall()
finally:
    db.close()

# Continue only if there are rows returned.
if rows:
    fp = open(csv_file_path, 'w', encoding='utf-8')
    myFile = csv.writer(fp)
    myFile.writerows(rows)
    fp.close()
else:
    sys.exit("No rows found for query: {}".format(sql))