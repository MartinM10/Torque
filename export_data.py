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

sql = 'SELECT l.id_app AS id, l.session, l.time AS session_time, s.user_full_name AS description, CONCAT(r.value, " ", s.user_unit) AS value, r.time AS record_time, r.latitude, r.longitude FROM torque_db.models_log l INNER JOIN torque_db.models_record r ON r.log_id = l.id INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id;'
csv_file_path = '/home/martin/Descargas/my_csv_file.csv'

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