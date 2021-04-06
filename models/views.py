import json

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from shapely.geometry import Point, mapping
from django.db import connection, transaction
from django.http import HttpResponse
import datetime
from django.shortcuts import render, redirect
import os

# Create your views here.
from rest_framework import viewsets

from Torque.settings import DATA_URL, BASE_DIR, STATIC_URL
from models.models import Log, Record, Dataset, Sensor, Prediction, KMeans, SVM, DataTorque, Address
from models.serializers import LogSerializer, RecordSerializer, DatasetSerializer, SensorSerializer, \
    PredictionSerializer, KMeansSerializer, SVMSerializer, DataTorqueSerializer

geolocator = Nominatim(user_agent="http")
rev = RateLimiter(geolocator.reverse, min_delay_seconds=0.001)

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
    sessions = Log.objects.all()

    sql = '' \
          'select distinct ' \
          'log_id as session_id, ' \
          'email, ' \
          'replace(substring(session, 1, length(session) - 7), " ", ",  ") as date, ' \
          'Total_Trip_Time as `Trip Duration`, ' \
          'Total_Trip_Fuel_Used as `Trip Fuel Used`,' \
          'Total_Trip_Distance as `Trip Distance`, ' \
          'CO2_Average as `Trip CO2 Average`, ' \
          'Speed_Only_Mov_Average as `Trip Speed Only Moving Average`, ' \
          'substring(substring(record_time, 1, length(record_time) - 7), 12) as `Time Now`, ' \
          'latitude, ' \
          'longitude, ' \
          'max(case when pid = "ff1266" then value else null end) as `Duration`, ' \
          'max(case when pid = "ff1204" then value else null end) as `Distance`, ' \
          'max(case when pid = "ff1258" then value else null end) as `CO2 Average`, ' \
          'max(case when pid = "ff1263" then value else null end) as `Speed Average Only Moving`, ' \
          'max(case when pid = "ff1271" then value else null end) as `Fuel Used`, ' \
          'max(case when pid = "ff1208" then value else null end) as `Liters per kilometer Average`, ' \
          'max(case when pid = "ff1001" then value else null end) as `GPS Speed`, ' \
          'max(case when pid = "ff1239" then value else null end) as `GPS Accuracy`, ' \
          'max(case when pid = "ff1257" then value else null end) as `CO2 Instantaneous` ' \
          'from ' \
          ' ( ' \
          '     select distinct ' \
          '         base.log_id, base.email, base.session, base.record_time, base.latitude, base.longitude, ' \
          '         base.pid, base.value, Total_Trip_Fuel_Used, Total_Trip_Time, ' \
          '         Total_Trip_Distance, CO2_Average, Speed_Only_Mov_Average, ' \
          '	        if (value <> @p, @rn:=1 ,@rn:=@rn+1) rn, @p:=value p ' \
          '     from' \
          '         ( ' \
          '             SELECT distinct ' \
          '                 l.id as log_id, l.email, l.session, r.time AS record_time, s.pid as pid, ' \
          '                 CONCAT(round(r.value, 2), " ", s.user_unit) AS value, r.latitude, r.longitude ' \
          '             FROM ' \
          '                 torque_db.models_log l ' \
          '             INNER JOIN torque_db.models_record r ON r.log_id = l.id and l.id = %s ' \
          '             INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id ' \
          '             WHERE s.pid != "ff1005" and s.pid != "ff1006" ' \
          '         ) base ' \
          '         LEFT JOIN ' \
          '         ( ' \
          '             SELECT DISTINCT ' \
          '                     l.id as log_id, l.session, ' \
          '                     max(case when s.pid = "ff1204" then concat(round(value, 2), " ", user_unit) ' \
          '                             else null end) AS `Total_Trip_Distance`,' \
          '                     max(case when s.pid = "ff1266" then substr(sec_to_time(r.value), 1, 8) else null end) ' \
          '                         AS `Total_Trip_Time`,' \
          '                     max(case when s.pid = "ff1271" then concat(round(value, 2), " ", s.user_unit) ' \
          '                             else null end) AS `Total_Trip_Fuel_Used`' \
          '             FROM ' \
          '                 torque_db.models_log l ' \
          '             INNER JOIN torque_db.models_record r ON r.log_id = l.id and l.id = %s ' \
          '             INNER JOIN torque_db.models_sensor s ON s.id = r.sensor_id ' \
          '             WHERE s.pid != "ff1005" and s.pid != "ff1006" ' \
          '                     and s.pid = "ff1204" or s.pid = "ff1266" or s.pid = "ff1271" ' \
          '             GROUP BY l.id, l.session ' \
          '             ORDER BY l.id ' \
          '         ) totals on base.log_id = totals.log_id ' \
          '         LEFT JOIN ' \
          '         (' \
          '         SELECT ' \
          '                 l.id as log_id, concat(round(r.value, 2), " ", s.user_unit) as `CO2_Average` ' \
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
          '         LEFT JOIN ' \
          '         (' \
          '         SELECT ' \
          '                 l.id as log_id, concat(round(r.value, 2), " ", s.user_unit) as `Speed_Only_Mov_Average` ' \
          '         FROM models_log l ' \
          '         INNER JOIN models_record r on l.id = r.log_id and l.id = %s ' \
          '         INNER JOIN models_sensor s on r.sensor_id = s.id ' \
          '         WHERE s.pid != "ff1005" and s.pid != "ff1006" ' \
          '         and s.pid = "ff1263" and ' \
          '         r.time = ( ' \
          '                     SELECT max(r.time) ' \
          '                     FROM models_log l ' \
          '                     INNER JOIN models_record r on l.id = r.log_id and l.id = %s' \
          '                     INNER JOIN models_sensor s on r.sensor_id = s.id ' \
          '                     WHERE s.pid = "ff1263" ' \
          '                 ) ' \
          '         ) av_sp on base.log_id = av_sp.log_id ' \
          'cross join (select @rn:=0,@p:=null) r ' \
          'order by rn ' \
          ') s ' \
          'group by s.log_id, email, session, CO2_Average, Speed_Only_Mov_Average, record_time, latitude, longitude; ' \
          % (session_id, session_id, session_id, session_id, session_id, session_id)

    cursor.execute(sql)
    crs_list = cursor.fetchall()
    # gjson is th emain dictionary
    gjson_dict = {}
    gjson_dict["type"] = "FeatureCollection"
    feat_list = []
    field_names = [i[0] for i in cursor.description]

    track = []
    values = {}

    for crs in crs_list:
        type_dict = {}
        pt_dict = {}
        prop_dict = {}

        total_trip_time = field_names[3]
        values[total_trip_time] = crs[3]
        total_trip_fuel_used = field_names[4]
        values[total_trip_fuel_used] = crs[4]
        total_trip_distance = field_names[5]
        values[total_trip_distance] = crs[5]
        trip_co2_average = field_names[6]
        values[trip_co2_average] = crs[6]
        trip_speed_only_mov_average = field_names[7]
        values[trip_speed_only_mov_average] = crs[7]

        type_dict["type"] = "Feature"

        pt_dict["type"] = "Point"

        # GEOJSON looks for long,lat so reverse order
        type_dict["geometry"] = mapping(Point(crs[10], crs[9]))
        # id_session = field_names[0]
        # prop_dict[id_session] = crs[0]
        email = field_names[1]
        prop_dict[email] = crs[1]
        date = field_names[2]
        prop_dict[date] = crs[2]

        trip_time = field_names[11]
        prop_dict[trip_time] = crs[11]

        trip_distance = field_names[12]
        prop_dict[trip_distance] = crs[12]

        co2_average = field_names[13]
        prop_dict[co2_average] = crs[13]

        speed_only_mov_average = field_names[14]
        prop_dict[speed_only_mov_average] = crs[14]

        trip_fuel_used = field_names[15]
        prop_dict[trip_fuel_used] = crs[15]

        record_time = field_names[8]
        prop_dict[record_time] = crs[8]
        gps_speed = field_names[17]
        prop_dict[gps_speed] = crs[17]
        gps_accuracy = field_names[18]
        prop_dict[gps_accuracy] = crs[18]
        c02_instantaneous = field_names[19]
        prop_dict[c02_instantaneous] = crs[19]
        # prop_dict["CO2_Average"] = crs[9]
        # prop_dict["Litres_Per_100_Kilometer"] = crs[15]
        type_dict["properties"] = prop_dict
        feat_list.append(type_dict)
        coordenates = (crs[9], crs[10])
        location = rev(coordenates)
        road = location.raw['address']['road']
        if road not in track:
            track.append(road)
        # print(location.raw)
        # print(location.raw['address']['road'])
        # print(location.address.street)

    print(track)
    gjson_dict["features"] = feat_list
    # 'DISTINCT id_app, session, record_time, latitude, longitude, '
    data = json.dumps(gjson_dict, default=myconverter, sort_keys=True, indent=4, ensure_ascii=False)
    # print(data)

    summary = [values]
    # print(summary)

    # location =  geolocation.reverse()
    return render(request, 'map.html', context={'data': data, 'sessions': sessions, 'summary': summary})


def viewMap(request):
    dir = os.path.join(str(BASE_DIR) + str(STATIC_URL) + 'data/')
    files = [STATIC_URL + 'data/' + arch.name for arch in os.scandir(str(dir)) if
             arch.is_file() and os.path.splitext(arch)[1] == ".kml"]

    context = {
        'files': files
    }
    return render(request, 'map.html', context=context)


def sql_query_longs_lats(sql_query):
    cursor = connection.cursor()
    cursor.execute(sql_query)
    crs_list = cursor.fetchall()
    return crs_list


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
    log = None

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
                log = Log.objects.get(session=session_time, email=email, id_app=id_app)
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

        # TABLE SENSOR AND TABLE RECORD
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
                '''
                if longitude and latitude:
                    coordenates = (latitude, longitude)
                    location = rev(coordenates, language='es', exactly_one=True)
                    print(location.raw)
                    # print(location.raw['address']['city'])
                    # house_number = location.raw['address']['house_number']
                    road = location.raw['address']['road']
                    neighbourhood = location.raw['address']['neighbourhood']
                    borough = location.raw['address']['borough']
                    city = location.raw['address']['city']
                    county = location.raw['address']['county']
                    state = location.raw['address']['state']
                    postcode = location.raw['address']['postcode']
                    country = location.raw['address']['country']
                    country_code = location.raw['address']['country_code']
                    try:
                        with transaction.atomic():
                            Address.objects.get(road=road, neighbourhood=neighbourhood,
                                                borough=borough, city=city, county=county, state=state,
                                                postcode=postcode,
                                                country=country, country_code=country_code, log_id=log_id).save()
                    except Address.DoesNotExist:
                        Address(road=road, neighbourhood=neighbourhood, borough=borough,
                                city=city, county=county, state=state, postcode=postcode, country=country,
                                country_code=country_code, log_id=log_id).save()
                '''
                timestamp = int(time_app)
                date_time = datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S''.''%f')
                Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time, latitude=latitude,
                       longitude=longitude).save()

    return HttpResponse('OK!')
