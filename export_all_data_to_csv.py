import pymysql
import csv
import sys

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

sessions_list = 'SELECT ' \
                '   DISTINCT id, id_app, session ' \
                'FROM ' \
                '   models_log ' \
                'ORDER BY id DESC;'


csv_file_path = 'data'

try:
    cur.execute(sessions_list)
    sessions_rows = cur.fetchall()
finally:
    pass

# Continue only if there are rows returned.
if sessions_rows:

    for row in sessions_rows:
        print('Session ID: ' + str(row[0]) + '  ||  Id_app: ' + str(row[1]) + '  ||  Date: ' + str(row[2]))
    try:
        session_id = raw_input('Enter id of session you wish export to csv: ')

        sql = '' \
              'SELECT ' \
              'DISTINCT id_app, session, record_time, latitude, longitude, ' \
              'MAX(CASE WHEN description = "GPS Accuracy" THEN value ELSE char(32) END ) AS `GPSAccuracy`, ' \
              'MAX(CASE WHEN description = "Speed (GPS)" THEN value ELSE char(32) END ) AS `Speed (GPS)`, ' \
              'MAX(CASE WHEN description = "CO₂ in g/km (Instantaneous)" THEN value ELSE char(32) END ) ' \
              'AS `CO₂ in g/km (Instantaneous)`, ' \
              'MAX(CASE WHEN description = "CO₂ in g/km (Average)" THEN value ELSE char(32) END ) ' \
              'AS `CO₂ in g/km (Average)`, ' \
              'MAX(CASE WHEN description = "Litres Per 100 Kilometer(Long Term Average)" THEN value ELSE char(32) END ) ' \
              'AS `LitresPer100Kilometer(LongTermAverage)`, ' \
              'MAX(CASE WHEN description = "Android device Battery Level" THEN value ELSE char(32) END ) ' \
              'AS `AndroiddeviceBatteryLevel` ' \
              'FROM ' \
              '(' \
              ' SELECT DISTINCT ' \
              '     id_app, session, record_time, latitude, longitude, description, value, ' \
              '     if (value <> @p, @rn:=1 ,@rn:=@rn+1) rn, @p:=value p ' \
              ' FROM ' \
              '     (' \
              '         SELECT DISTINCT ' \
              '             l.id_app, l.session, s.user_full_name AS description, ' \
              '             CONCAT(r.value, " ", s.user_unit) AS value, r.time AS record_time, ' \
              '             r.latitude, r.longitude FROM torque_db.models_log l ' \
              '         INNER JOIN torque_db.models_record r ON r.log_id = l.id ' \
              '         INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id ' \
              '         WHERE s.pid != "ff1005" AND s.pid != "ff1006" AND l.id = %s' \
              '         ORDER BY r.time' \
              '     ) t ' \
              'CROSS JOIN ' \
              '     (' \
              '         SELECT @rn:=0,@p:=null) r ORDER BY rn) s ' \
              'GROUP BY id_app, session, record_time, latitude, longitude;' % session_id

        cur.execute(sql)
        rows = cur.fetchall()

        fp = open(csv_file_path + '_' + session_id + '.csv', 'w', encoding='utf-8')

        cols = [i[0] for i in cur.description]

        for c, col in enumerate(cols):
            if c == len(cols) - 1:
                fp.write(col + '\n')
            else:
                fp.write(col + ',')

        myFile = csv.writer(fp)
        myFile.writerows(rows)
        fp.close()
    finally:
        db.close()
else:
    sys.exit("No rows found for query: {}".format(sessions_list))
