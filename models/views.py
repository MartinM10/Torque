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
          'SELECT ' \
          'DISTINCT id_app, session, email, record_time, latitude, longitude, ' \
          'MAX(CASE WHEN description = "GPS Accuracy" THEN value ELSE null END ) AS `GPSAccuracy`, ' \
          'MAX(CASE WHEN description = "Speed (GPS)" THEN value ELSE null END ) AS `Speed (GPS)`, ' \
          'MAX(CASE WHEN description = "CO₂ in g/km (Instantaneous)" THEN value ELSE null END ) ' \
          'AS `CO₂ in g/km (Instantaneous)`, ' \
          'MAX(CASE WHEN description = "CO₂ in g/km (Average)" THEN value ELSE null END ) ' \
          'AS `CO₂ in g/km (Average)`, ' \
          'MAX(CASE WHEN description = "Litres Per 100 Kilometer(Long Term Average)" THEN value ELSE null END ) ' \
          'AS `LitresPer100Kilometer(LongTermAverage)`, ' \
          'MAX(CASE WHEN description = "Android device Battery Level" THEN value ELSE null END ) ' \
          'AS `AndroiddeviceBatteryLevel` ' \
          'FROM ' \
          '(' \
          ' SELECT DISTINCT ' \
          '     id_app, session, email, record_time, latitude, longitude, description, value, ' \
          '     if (value <> @p, @rn:=1 ,@rn:=@rn+1) rn, @p:=value p ' \
          ' FROM ' \
          '     (' \
          '         SELECT DISTINCT ' \
          '             l.id_app, l.session, l.email, s.user_full_name AS description, ' \
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
          'GROUP BY id_app, session, email, record_time, latitude, longitude;' % session_id

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
        type_dict["geometry"] = mapping(Point(crs[5], crs[4]))

        prop_dict["id_app"] = crs[0]
        prop_dict["session"] = crs[1]
        prop_dict["email"] = crs[2]
        prop_dict["record_time"] = crs[3]
        prop_dict["gps_accuracy"] = crs[6]
        prop_dict["speed_GPS"] = crs[7]
        prop_dict["CO2_Instantaneous"] = crs[8]
        prop_dict["CO2_Average"] = crs[9]
        prop_dict["Litres_Per_100_Kilometer"] = crs[10]
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
