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

sql = 'select id, session, session_time, record_time, latitude, longitude, max(case when description = "GPS Accuracy" then value else char(32) end ) as `GPSAccuracy`, max(case when description = "Speed (GPS)" then value else char(32) end ) as `Speed (GPS)`, max(case when description = "CO₂ in g/km (Instantaneous)" then value else char(32) end ) as `CO₂ in g/km (Instantaneous)`, max(case when description = "CO₂ in g/km (Average)" then value else char(32) end ) as `CO₂ in g/km (Average)`, max(case when description = "Litres Per 100 Kilometer(Long Term Average)" then value else char(32) end ) as `LitresPer100Kilometer(LongTermAverage)`,max(case when description = "Android device Battery Level" then value else char(32) end ) as `AndroiddeviceBatteryLevel` from (select id, session, session_time, record_time, latitude, longitude, description, value, if (value <> @p, @rn:=1 ,@rn:=@rn+1) rn, @p:=value p from (SELECT l.id_app AS id, l.session, l.time AS session_time, s.user_full_name AS description, CONCAT(r.value, " ", s.user_unit) AS value, r.time AS record_time, r.latitude, r.longitude FROM torque_db.models_log l INNER JOIN torque_db.models_record r ON r.log_id = l.id INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id WHERE s.pid != "ff1005" and s.pid != "ff1006") t cross join (select @rn:=0,@p:=null) r order by rn) s group by id, session, session_time, record_time, latitude, longitude;'

csv_file_path = 'speedGPS.csv'

try:
    cur.execute(sql)
    rows = cur.fetchall()
finally:
    db.close()

# Continue only if there are rows returned.
if rows:
    fp = open(csv_file_path, 'w', encoding='utf-8')
    cols = [i[0] for i in cur.description]

    for c, col in enumerate(cols):
        if c == len(cols) - 1:
            fp.write(col + '\n')
        else:
            fp.write(col + ',')

    myFile = csv.writer(fp)
    myFile.writerows(rows)
    fp.close()
else:
    sys.exit("No rows found for query: {}".format(sql))
