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

sql = 'select distinct l.id_app, l.session, l.time, r.time as record_time, r.latitude, r.longitude, s.user_full_name, r.value from models_log l inner join models_record r on l.id = r.log_id inner join models_sensor s on r.sensor_id = s.id where s.pid like "ff1258" and l.session = 1615810034934 order by record_time;'

csv_file_path = 'CO2.csv'

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
