import json

from shapely.geometry import Point, mapping
from django.db import connection, transaction
from django.http import HttpResponse
import datetime
from django.shortcuts import render, redirect
import os

# Create your views here.
from rest_framework import viewsets

from Torque.settings import DATA_URL, BASE_DIR, STATIC_URL
from models.models import Log, Record, Dataset, Sensor, Prediction, KMeans, SVM, DataTorque
from models.serializers import LogSerializer, RecordSerializer, DatasetSerializer, SensorSerializer, \
    PredictionSerializer, KMeansSerializer, SVMSerializer, DataTorqueSerializer


class LogViewSet(viewsets.ModelViewSet):
    serializer_class = LogSerializer
    queryset = Log.objects.all()


class RecordViewSet(viewsets.ModelViewSet):
    serializer_class = RecordSerializer
    queryset = Record.objects.all()


class DataTorqueViewSet(viewsets.ModelViewSet):
    serializer_class = DataTorqueSerializer
    queryset = DataTorque.objects.all()


class DatasetViewSet(viewsets.ModelViewSet):
    serializer_class = DatasetSerializer
    queryset = Dataset.objects.all()


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    queryset = Sensor.objects.all()


class PredictionViewSet(viewsets.ModelViewSet):
    serializer_class = PredictionSerializer
    queryset = Prediction.objects.all()


class KMeansViewSet(viewsets.ModelViewSet):
    serializer_class = KMeansSerializer
    queryset = KMeans.objects.all()


class SVMViewSet(viewsets.ModelViewSet):
    serializer_class = SVMSerializer
    queryset = SVM.objects.all()


def sessions_by_id_list(request):
    sessions = Log.objects.all()
    return render(request, 'sessions_list.html', context={'sessions': sessions})


def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def session_in_map(request, session_id):
    cursor = connection.cursor()

    sql = '' \
          'select distinct ' \
          'log_id, email, session, Total_Trip_Time, Total_Trip_Fuel_Used, Total_Trip_Distance, CO2_Average, ' \
          'record_time, latitude, longitude, ' \
          'max(case when pid = "ff1266" then value else null end) as `Trip_Time`, ' \
          'max(case when pid = "ff1204" then value else null end) as `Trip_Distance`, ' \
          'max(case when pid = "ff1258" then value else null end) as `CO2_Average`, ' \
          'max(case when pid = "ff1263" then value else null end) as `Trip_Speed_Average_Only_Moving`, ' \
          'max(case when pid = "ff1271" then value else null end) as `Trip_Fuel_Used`, ' \
          'max(case when pid = "ff1208" then value else null end) as `Trip_LPK_Average`, ' \
          'max(case when pid = "ff1001" then value else null end) as `GPS_Speed`, ' \
          'max(case when pid = "ff1239" then value else null end) as `GPS_Accuracy`, ' \
          'max(case when pid = "ff1257" then value else null end) as `CO2_Instantaneous` ' \
          'from ' \
          ' ( ' \
          '     select distinct ' \
          '         base.log_id, base.email, base.session, base.record_time, base.latitude, base.longitude, ' \
          '         base.pid, base.value, Total_Trip_Fuel_Used, Total_Trip_Time, ' \
          '         Total_Trip_Distance, CO2_Average, ' \
          '	        if (value <> @p, @rn:=1 ,@rn:=@rn+1) rn, @p:=value p ' \
          '     from' \
          '         ( ' \
          '             SELECT distinct ' \
          '                 l.id as log_id, l.email, l.session, r.time AS record_time, s.pid as pid, ' \
          '                 CONCAT(r.value, " ", s.user_unit) AS value, r.latitude, r.longitude ' \
          '             FROM ' \
          '                 torque_db.models_log l ' \
          '             INNER JOIN torque_db.models_record r ON r.log_id = l.id ' \
          '             INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id ' \
          '             WHERE s.pid != "ff1005" and s.pid != "ff1006" and l.id = %s ' \
          '         ) base ' \
          '         INNER JOIN ' \
          '         ( ' \
          '             SELECT DISTINCT ' \
          '                     l.id as log_id, l.session, ' \
          '                     max(case when s.pid = "ff1204" then concat(value, " ", user_unit) else null end) AS `Total_Trip_Distance`,' \
          '                     max(case when s.pid = "ff1266" then substr(sec_to_time(r.value), 1, 8) else null end) AS `Total_Trip_Time`,' \
          '                     max(case when s.pid = "ff1271" then concat(value, " ", s.user_unit) else null end) AS `Total_Trip_Fuel_Used`' \
          '             FROM ' \
          '                 torque_db.models_log l ' \
          '             INNER JOIN torque_db.models_record r ON r.log_id = l.id and l.id = %s ' \
          '             INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id ' \
          '             WHERE s.pid != "ff1005" and s.pid != "ff1006" ' \
          '                     and s.pid = "ff1204" or s.pid = "ff1266" or s.pid = "ff1271" ' \
          '             GROUP BY l.id, l.session ' \
          '             ORDER BY l.id ' \
          '         ) totals on base.log_id = totals.log_id ' \
          '         INNER JOIN ' \
          '         (' \
          '         SELECT ' \
          '                 l.id as log_id, concat(r.value, " ", s.user_unit) as `CO2_Average` ' \
          '         FROM models_log l ' \
          '         INNER JOIN models_record r on l.id = r.log_id and l.id = %s ' \
          '         INNER JOIN models_sensor s on r.sensor_id = s.id ' \
          '         WHERE s.pid != "ff1005" and s.pid != "ff1006" ' \
          '         and s.pid = "ff1258" and ' \
          '         r.time = ( ' \
          '                     SELECT max(r.time) ' \
          '                     FROM models_log l ' \
          '                     INNER JOIN models_record r on l.id = r.log_id and l.id = %s' \
          '                     INNER JOIN models_sensor s on r.sensor_id = s.id ' \
          '                     WHERE s.pid = "ff1258" ' \
          '                 ) ' \
          '         ) averages on base.log_id = averages.log_id ' \
          'cross join (select @rn:=0,@p:=null) r ' \
          'order by rn ' \
          ') s ' \
          'group by s.log_id, email, session, CO2_Average, record_time, latitude, longitude; ' % (session_id, session_id, session_id ,session_id)

    cursor.execute(sql)
    crs_list = cursor.fetchall()
    # gjson is th emain dictionary
    gjson_dict = {}
    gjson_dict["type"] = "FeatureCollection"
    feat_list = []

    for crs in crs_list:
        type_dict = {}
        pt_dict = {}
        prop_dict = {}

        type_dict["type"] = "Feature"

        pt_dict["type"] = "Point"

        # GEOJSON looks for long,lat so reverse order
        type_dict["geometry"] = mapping(Point(crs[8], crs[7]))

        prop_dict["id_session"] = crs[0]
        prop_dict["email"] = crs[1]
        prop_dict["session"] = crs[2]
        prop_dict["record_time"] = crs[6]
        prop_dict["gps_accuracy"] = crs[16]
        prop_dict["speed_GPS"] = crs[15]
        prop_dict["CO2_Instantaneous"] = crs[17]
        # prop_dict["CO2_Average"] = crs[9]
        prop_dict["Litres_Per_100_Kilometer"] = crs[14]
        type_dict["properties"] = prop_dict
        feat_list.append(type_dict)

    gjson_dict["features"] = feat_list
    # 'DISTINCT id_app, session, record_time, latitude, longitude, '
    data = json.dumps(gjson_dict, default=myconverter, sort_keys=True, indent=4, ensure_ascii=False)
    # print(data)
    return render(request, 'map.html', context={'data': data})


def viewMap(request):
    dir = os.path.join(str(BASE_DIR) + str(STATIC_URL) + 'data/')
    files = [STATIC_URL + 'data/' + arch.name for arch in os.scandir(str(dir)) if
             arch.is_file() and os.path.splitext(arch)[1] == ".kml"]

    context = {
        'files': files
    }
    return render(request, 'map.html', context=context)


@transaction.atomic
def upload_data(request):
    # print(request.query_params)
    # print(request.GET)
    session_app = request.GET.get('session')
    id_app = request.GET.get('id')
    email = request.GET.get('eml')
    time_app = request.GET.get('time')
    latitude = request.GET.get('kff1006')
    longitude = request.GET.get('kff1005')
    session_time = None

    # print("TIMESTAMP---------------------------------- ")
    # ts = int(time_app)
    # print(ts, '\n')
    # from django.utils.datetime_safe import datetime
    # print(datetime.utcfromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S' '.' '%f'))

    # TABLE LOG

    # session_time = datetime.fromtimestamp(session_app/1000) + timedelta(hours=1)\
    #                   .strftime('%Y-%m-%d %H:%M:%S' '.' '%f')
    if session_app:
        session_time = datetime.datetime.fromtimestamp(int(session_app) / 1000)
        session_time += datetime.timedelta(hours=1)
    if session_time and email and id_app:
        try:
            with transaction.atomic():
                Log.objects.get(session=session_time, email=email, id_app=id_app)
        except Log.DoesNotExist:
            try:
                with transaction.atomic():
                    Log(session=session_time, email=email, id_app=id_app).save()
            except:
                pass
    ''' 
    log, created = Log.objects.get_or_create(session=session_time, email=email, id_app=id_app)
    if created:
        Log(session=session_time, email=email, id_app=id_app, dataset_id=None).save()
    '''
    for key, value in request.GET.items():
        # print(key, " -> ", value)

        # TABLE DATA_TORQUE
        try:
            with transaction.atomic():
                DataTorque(key=key, value=value, session=session_time, email=email, id_app=id_app, time=time_app,
                           latitude=latitude, longitude=longitude).save()
        except:
            pass

        # TABLE SENSOR
        if 'FullName' in key or 'ShortName' in key or 'userUnit' in key or \
                'defaultUnit' in key or 'kff' in key:

            pid = key[-6:]
            sensor = Sensor.objects.get_or_create(pid=pid)

            if 'kff' not in key:

                if 'FullName' in key and Sensor.objects.get(pid=pid).user_full_name != value:
                    Sensor.objects.filter(pid=pid).update(user_full_name=value)

                if 'ShortName' in key and Sensor.objects.get(pid=pid).user_short_name != value:
                    Sensor.objects.filter(pid=pid).update(user_short_name=value)

                if 'userUnit' in key and Sensor.objects.get(pid=pid).user_unit != value:
                    Sensor.objects.filter(pid=pid).update(user_unit=value)

                if 'defaultUnit' in key and Sensor.objects.get(pid=pid).default_unit != value:
                    Sensor.objects.filter(pid=pid).update(default_unit=value)

            # TABLE RECORD
            elif 'kff' in key:

                if 'kff1006' in key:
                    latitude = value
                if 'kff1005' in key:
                    longitude = value

                sensor_id = Sensor.objects.get(pid=pid).id
                log_id = Log.objects.filter(id_app=id_app, email=email, session=session_time).first().id
                timestamp = int(time_app)
                date_time = datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S''.''%f')
                Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time, latitude=latitude,
                       longitude=longitude).save()

    return HttpResponse('OK!')
