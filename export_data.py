import pymysql
import csv
import sys

from django.utils.datetime_safe import datetime
from pip._vendor.distlib.compat import raw_input

db_opts = {
    'user': 'martin',
    'password': 'martinjs',
    'host': 'localhost',
    'database': 'torque_db',
    # local
    # 'port': 3306
    # server
    'port': 3307
}

db = pymysql.connect(**db_opts)
cur = db.cursor()
cur1 = db.cursor()
cur2 = db.cursor()
cur3 = db.cursor()

sessions_list = 'select ' \
                '   distinct id, id_app, session, time ' \
                'from ' \
                '   models_log ' \
                'order by id desc;'

# sql = 'select distinct l.id_app, l.session, r.time as record_time, r.latitude, r.longitude, s.user_full_name, r.value from models_log l inner join models_record r on l.id = r.log_id inner join models_sensor s on r.sensor_id = s.id where s.pid like "ff1001" and l.session = 1615807853045 order by record_time;'

csv_file_path = 'test.csv'

try:
    # cur.execute(sql)
    # rows = cur.fetchall()
    cur.execute(sessions_list)
    sessions_rows = cur.fetchall()
finally:
    pass

# Continue only if there are rows returned.
if sessions_rows:
    for row in sessions_rows:
        print('session ID: ' + str(row[0]) + ' --> date: ' + datetime.utcfromtimestamp(row[2] / 1000).strftime(
            '%Y-%m-%d %H:%M:%S' '.' '%f'))
    try:
        session_id = raw_input('Enter id of session you wish export to csv: ')

        sql_speed = \
                ' select ' \
                '     distinct l.id_app, l.session, r.time as record_time,' \
                '     r.latitude, r.longitude, s.user_full_name, r.value' \
                ' from ' \
                '     models_log l ' \
                ' inner join ' \
                '     models_record r on l.id = r.log_id' \
                ' inner join models_sensor s on r.sensor_id = s.id ' \
                ' where s.pid like "ff1001" and l.id = %s order by record_time;' % session_id

        sql_co2 = \
            ' select ' \
            '     distinct l.id_app, l.session, r.time as record_time,' \
            '     r.latitude, r.longitude, s.user_full_name, r.value' \
            ' from ' \
            '     models_log l ' \
            ' inner join ' \
            '     models_record r on l.id = r.log_id' \
            ' inner join models_sensor s on r.sensor_id = s.id ' \
            ' where s.pid like "ff1258" and l.id = %s order by record_time;' % session_id

        sql_litres_per_100km = \
            ' select ' \
            '     distinct l.id_app, l.session, r.time as record_time,' \
            '     r.latitude, r.longitude, s.user_full_name, r.value' \
            ' from ' \
            '     models_log l ' \
            ' inner join ' \
            '     models_record r on l.id = r.log_id' \
            ' inner join models_sensor s on r.sensor_id = s.id ' \
            ' where s.pid like "ff5203" and l.id = %s order by record_time;' % session_id

        cur1.execute(sql_speed)
        rows1 = cur1.fetchall()

        cur2.execute(sql_co2)
        rows2 = cur2.fetchall()

        cur3.execute(sql_litres_per_100km)
        rows3 = cur3.fetchall()

        if rows1:
            fp = open(csv_file_path + '_speed', 'w', encoding='utf-8')
            myFile = csv.writer(fp)
            myFile.writerows(rows1)
            fp.close()

        if rows2:
            fp = open(csv_file_path + '_co2', 'w', encoding='utf-8')
            myFile = csv.writer(fp)
            myFile.writerows(rows2)
            fp.close()

        if rows3:
            fp = open(csv_file_path + '_litres_per_100km', 'w', encoding='utf-8')
            myFile = csv.writer(fp)
            myFile.writerows(rows3)
            fp.close()

    finally:
        db.close()

else:
    sys.exit("No rows found for query: {}".format(sessions_list))
