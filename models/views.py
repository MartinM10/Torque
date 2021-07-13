import csv
import json
import re
from operator import concat

from django.core import serializers
from django.core.serializers import serialize
from django.utils.timezone import make_aware
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from shapely.geometry import Point, mapping
from django.db import connection, transaction
from django.http import HttpResponse
import datetime
from django.shortcuts import render
import os

# Create your views here.
from rest_framework import viewsets

from Torque.settings import DATA_URL, BASE_DIR, STATIC_URL
from models.models import Log, Record, Dataset, Sensor, Prediction, KMeans, SVM, DataTorque, Track, TrackLog
from models.serializers import LogSerializer, RecordSerializer, DatasetSerializer, SensorSerializer, \
    PredictionSerializer, KMeansSerializer, SVMSerializer, DataTorqueSerializer

geolocator = Nominatim(user_agent="Torque")
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


def track(session_id):
    log = Log.objects.get(id=session_id)
    addresses = log.track_set.all()
    address_list = []
    last_address = ''

    if not addresses:

        records = Log.objects.get(id=session_id).record_set.all()
        last_time = None
        i = 0
        for obj in records:
            newest_time = obj.time.second

            if i == 0:
                last_time = (newest_time - newest_time) + 15

            interval = (newest_time - last_time) % 60

            if interval >= 8:
                coordinates = (obj.latitude, obj.longitude)

                location = geolocator.reverse(coordinates, zoom=17)
                addresses = location.raw['address']
                # print(addresses)
                simple_address = ''

                try:
                    road = addresses['road']
                    simple_address += road
                except KeyError:
                    road = None

                if road:
                    '''
                    try:
                        neighbourhood = addresses['neighbourhood']
                        simple_address += ', ' + neighbourhood
                    except KeyError:
                        neighbourhood = None
                    try:
                        town = addresses['town']
                        simple_address += ', ' + town
                    except KeyError:
                        town = None
                    try:
                        city = addresses['city']
                        simple_address += ', ' + city
                    except KeyError:
                        city = None
                    '''

                    with transaction.atomic():
                        trck, created = Track.objects.get_or_create(address=simple_address)
                        if created:
                            TrackLog.objects.create(track=trck, log=log, time=obj.time).save()

                        else:
                            trck = Track.objects.get(address=simple_address)
                            TrackLog.objects.create(track=trck, log=log, time=obj.time).save()

                    if trck.address != last_address:
                        address_list.append(trck.address)
                        last_address = trck.address

                last_time = obj.time.second
                i += 1
    else:

        for obj in addresses.order_by('tracklog__time'):
            if obj.address != last_address:
                address_list.append(obj.address)
                last_address = obj.address

    # Si quiero obtener el timestamp de cada calle por la que se pasó (codigo de abajo)
    '''
    lista = TrackLog.objects.filter(log_id=session_id).order_by('time')
    print(lista)
    
    for obj in lista:
        if obj.address != last_address:
            address_list.append(obj.address)
            last_address = obj.address   
    '''
    return address_list


def download_csv(request, session_id):
    # filename = 'session' + str(session_id) + '.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="session.csv"'

    result = query(session_id=session_id)
    crs_list = result[0]
    field_names = result[1]

    writer = csv.writer(response)
    writer.writerow(field_names)

    for crs in crs_list:
        writer.writerow(crs)

    return response


def query(session_id):
    cursor = connection.cursor()
    # 'replace(left(session, 19), " ", "    ,    ") as date, ' \

    sql = '' \
          'select distinct ' \
          'log_id as session_id, ' \
          'email, ' \
          'left(session, 19) as date, ' \
          'Total_Trip_Time as `Trip Duration`, ' \
          'Total_Trip_Fuel_Used as `Trip Fuel Used`,' \
          'Total_Trip_Distance as `Trip Distance`, ' \
          'CO2_Average as `Trip CO2 Average`, ' \
          'Speed_Only_Mov_Average as `Trip Speed Only Moving Average`, ' \
          'right(left(record_time, 19), 8) as `Time Now`, ' \
          'latitude, ' \
          'longitude, ' \
          'max(case when pid = "ff1266" then substr(sec_to_time(value), 1, 8) else null end) as `Duration`, ' \
          'max(case when pid = "ff1204" then value else null end) as `Distance`, ' \
          'max(case when pid = "ff1271" then value else null end) as `Fuel Used`, ' \
          'max(case when pid = "ff1257" then value else null end) as `CO2 Instantaneous`, ' \
          'max(case when pid = "ff1258" then value else null end) as `CO2 Average`, ' \
          'max(case when pid = "05" then value else null end) as `Engine Coolant Temperature`, ' \
          'max(case when pid = "ff1208" then value else null end) as `Liters per kilometer Average`, ' \
          'max(case when pid = "ff1239" then value else null end) as `GPS Accuracy`, ' \
          'max(case when pid = "ff1001" then value else null end) as `GPS Speed`, ' \
          'max(case when pid = "0d" then value else null end) as `OBD Speed`, ' \
          'max(case when pid = "ff1237" then value else null end) as `GPS vs OBD Speed difference`, ' \
          'max(case when pid = "ff1263" then value else null end) as `Speed Average Only Moving`, ' \
          'max(case when pid = "ff129a" then value else null end) as `Android device Battery level`, ' \
          'max(case when pid = "ff1207" then value else null end) as `Litres per kilometer Instantaneous` ' \
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
    field_names = [i[0] for i in cursor.description]
    data = [crs_list, field_names]
    return data


def using_orm(request, session_id):
    sessions = Log.objects.all()
    session = Log.objects.get(id=session_id)

    # SUMMARY
    ###############################################################################################################
    co2_avg_unit = Sensor.objects.get(pid='ff1258').user_unit
    co2_avg = str(round(session.record_set.filter(sensor__pid='ff1258').last().value, 2)) + ' ' + co2_avg_unit

    speed_avg_mov_only_unit = Sensor.objects.get(pid='ff1263').user_unit
    speed_avg_mov_only = str(round(session.record_set.filter(sensor__pid='ff1263').last().value, 2)) + ' ' + \
                         speed_avg_mov_only_unit

    distance_unit = Sensor.objects.get(pid='ff1204').user_unit
    distance = str(round(session.record_set.filter(sensor__pid='ff1204').last().value, 2)) + ' ' + distance_unit

    fuel_used_unit = Sensor.objects.get(pid='ff1271').user_unit
    fuel_used = str(round(session.record_set.filter(sensor__pid='ff1271').last().value, 2)) + ' ' + fuel_used_unit

    duration_unit = Sensor.objects.get(pid='ff1266').user_unit
    duration = str(round(session.record_set.filter(sensor__pid='ff1266').last().value, 2)) + ' ' + duration_unit
    ###############################################################################################################
    # data = session.record_set.values_list().exclude(sensor__record__log_id=1).exclude(sensor__record__log_id=2)
    # print(data)
    # DATA
    # print(serializers.serialize('json', session.record_set.filter(sensor__pid='ff1001').order_by('-time')))


def session_in_map(request, session_id):
    sessions = Log.objects.all()
    session = Log.objects.get(id=session_id)
    res = query(session_id)
    # print(res)
    # using_orm(request, session_id)

    crs_list = res[0]
    gjson_dict = {}
    gjson_dict["type"] = "FeatureCollection"
    feat_list = []
    field_names = res[1]
    # track = []
    values = {}
    dict_obd_speeds = []
    dict_co2_inst = []
    dict_lit_per_km = []
    dict_lit_per_km_inst = []
    dict_temps = []
    dict_gps_speeds = []
    times = []

    for crs in crs_list:
        type_dict = {}
        pt_dict = {}
        prop_dict = {}

        # total_trip_time = field_names[3]
        total_trip_time = 'Duracion'
        values[total_trip_time] = crs[3]
        # total_trip_fuel_used = field_names[4]
        total_trip_fuel_used = 'Combustible utilizado'
        values[total_trip_fuel_used] = crs[4]
        # total_trip_distance = field_names[5]
        total_trip_distance = 'Distancia recorrida'
        values[total_trip_distance] = crs[5]
        # trip_co2_average = field_names[6]
        trip_co2_average = 'C0₂ medio emitido'
        values[trip_co2_average] = crs[6]
        # trip_speed_only_mov_average = field_names[7]
        trip_speed_only_mov_average = 'Velocidad media solo en movimiento'
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

        time_now = field_names[8]
        prop_dict[time_now] = crs[8]
        if crs[8]:
            times.append(crs[8])
            # times.append(datetime.datetime.strptime(crs[8], '%H:%M:%S').time())

        trip_time = field_names[11]
        prop_dict[trip_time] = crs[11]

        trip_distance = field_names[12]
        prop_dict[trip_distance] = crs[12]

        trip_fuel_used = field_names[13]
        prop_dict[trip_fuel_used] = crs[13]

        c02_instantaneous = field_names[14]
        prop_dict[c02_instantaneous] = crs[14]
        if crs[14]:
            dict_co2_inst.append(crs[14][0:-5])

        co2_average = field_names[15]
        prop_dict[co2_average] = crs[15]

        engine_coolant = field_names[16]
        prop_dict[engine_coolant] = crs[16]
        if crs[16]:
            dict_temps.append(crs[16][0:-3])

        liters_per_km = field_names[17]
        prop_dict[liters_per_km] = crs[17]
        if crs[17]:
            dict_lit_per_km.append(crs[17][0:-8])

        gps_accuracy = field_names[18]
        prop_dict[gps_accuracy] = crs[18]

        gps_speed = field_names[19]
        prop_dict[gps_speed] = crs[19]
        if crs[19]:
            dict_gps_speeds.append(crs[19][0:-5])

        obd_speed = field_names[20]
        prop_dict[obd_speed] = crs[20]
        if crs[20]:
            dict_obd_speeds.append(crs[20][0:-5])

        speed_diff = field_names[21]
        prop_dict[speed_diff] = crs[21]

        speed_only_mov_average = field_names[22]
        prop_dict[speed_only_mov_average] = crs[22]

        android_battery_lvl = field_names[23]
        prop_dict[android_battery_lvl] = crs[23]

        liters_per_km_inst = field_names[24]
        prop_dict[liters_per_km_inst] = crs[24]
        if crs[24]:
            dict_lit_per_km_inst.append(crs[24][0:-8])

        type_dict["properties"] = prop_dict
        feat_list.append(type_dict)

        # Name of streets
        # coordenates = (crs[9], crs[10])
        # location = rev(coordenates)
        # address = location.raw['address']
        # print(road)
        # print(location.raw['address'])
        '''
        if address:
            for key in address:
                if 'road' in key:
                    road = location.raw['address']['road']
                    if road not in track:
                        print('added: ', road)
                        track.append(road)
                else:
                    print('NO HAY NOMBRE DE CALLE --------------------- ')
                    print(address)
        '''
        # print(location.raw)

    # print(track)
    gjson_dict["features"] = feat_list
    data = json.dumps(gjson_dict, default=myconverter, sort_keys=True, indent=4, ensure_ascii=False)

    # print(obd_speeds)
    # print(times)
    # print(feat_list[2].get('properties')['OBD Speed'])

    address_list = track(session_id)

    context = {
        'data': data,
        'session': session,
        'sessions': sessions,
        'summary': values,
        'dict_gps_speeds': dict_gps_speeds,
        'dict_obd_speeds': dict_obd_speeds,
        'dict_co2_inst': dict_co2_inst,
        'dict_lit_per_km': dict_lit_per_km,
        'dict_lit_per_km_inst': dict_lit_per_km_inst,
        'dict_temps': dict_temps,
        'times': times,
        'address_list': address_list
    }

    # print(type(datetime.datetime.strptime(times[1], '%H:%M:%S').time()))
    # print(dict_gps_speeds)
    # print(len(dict_gps_speeds))
    return render(request, 'map.html', context=context)


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
        session_time = make_aware(datetime.datetime.fromtimestamp(int(session_app) / 1000))
        # print(session_time)
        st = session_time.strftime('%Y-%m-%d %H:%M:%S' '.' '%f')
        st = session_time.strptime(st, '%Y-%m-%d %H:%M:%S' '.' '%f')
        # print(type(s))
        # print(s)
        session_time = st

    # session_time += datetime.timedelta(hours=1)
    # aware_datetime = make_aware(session_time)
    # print(type(session_time))
    # print(session_time, '%Y-%m-%d %H:%M:%S' '.' '%f')

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

        # print(key)
        # print(value)
        # patron = "(kff)|(k[d|5])"
        # patron_OK = "(kff[0-9]{1,4}|k[0-9a-z]{0,3})"
        # print(patron)
        # TABLE SENSOR AND TABLE RECORD
        if 'FullName' in key or 'ShortName' in key or 'userUnit' in key or \
                'defaultUnit' in key or 'kff' in key or 'kd' in key or 'k5' in key:

            pid = ''

            if 'Name05' in key or 'Unit05' in key or '0d' in key or '0c' in key:
                pid = key[-2:]
            else:
                pid = key[-6:]

            # print(pid)
            # print(value)

            if 'kff' not in key and 'kd' not in key and 'k5' not in key and 'kc' not in key:
                sensor = Sensor.objects.get_or_create(pid=pid)

                if 'FullName' in key and Sensor.objects.get(pid=pid).user_full_name != value:
                    Sensor.objects.filter(pid=pid).update(user_full_name=value)

                if 'ShortName' in key and Sensor.objects.get(pid=pid).user_short_name != value:
                    Sensor.objects.filter(pid=pid).update(user_short_name=value)

                if 'userUnit' in key and Sensor.objects.get(pid=pid).user_unit != value:
                    Sensor.objects.filter(pid=pid).update(user_unit=value)

                if 'defaultUnit' in key and Sensor.objects.get(pid=pid).default_unit != value:
                    Sensor.objects.filter(pid=pid).update(default_unit=value)

            # TABLE RECORD
            else:  # if 'kff' in key or 'kd' in key or 'k5' in key:

                if 'kff1006' in key:
                    latitude = value
                if 'kff1005' in key:
                    longitude = value
                if 'kd' in key:
                    pid = '0d'
                if 'k5' in key:
                    pid = '05'
                if 'kc' in key:
                    pid = '0c'

                sensor_id = Sensor.objects.get(pid=pid).id
                log_id = Log.objects.filter(id_app=id_app, email=email, session=session_time).first().id

                date_time = make_aware(datetime.datetime.fromtimestamp(int(time_app) / 1000))
                dt = date_time.strftime('%Y-%m-%d %H:%M:%S' '.' '%f')
                dt = date_time.strptime(dt, '%Y-%m-%d %H:%M:%S' '.' '%f')
                date_time = dt

                if 'E' in value:
                    value = None

                Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time, latitude=latitude,
                       longitude=longitude).save()

    return HttpResponse('OK!')
