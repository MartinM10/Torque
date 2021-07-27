import csv
import json
import re
from fileinput import filename
from math import trunc
from operator import concat

from django.core import serializers
from django.core.serializers import serialize
from django.utils.datetime_safe import datetime
from django.utils.timezone import make_aware
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from shapely.geometry import Point, mapping
from django.db import connection, transaction
from django.http import HttpResponse
import datetime
from django.shortcuts import render, redirect
import os
import pandas
import geopandas
import logging
# Create your views here.
from rest_framework import viewsets

from Torque.settings import DATA_URL, BASE_DIR, STATIC_URL
from models.models import Log, Record, Dataset, Sensor, Prediction, KMeans, SVM, DataTorque, Track, TrackLog
from models.serializers import LogSerializer, RecordSerializer, DatasetSerializer, SensorSerializer, \
    PredictionSerializer, KMeansSerializer, SVMSerializer, DataTorqueSerializer

geolocator = Nominatim(user_agent="Torque")

# rev = RateLimiter(geolocator.reverse, min_delay_seconds=0.001)

logging.basicConfig(filename='./logs/InfoLog.log', level=logging.INFO)

TIME_LAST_HTTP_REQUEST = datetime.datetime.now()
TIME_TO_CONSIDER_NEW_SESSION = datetime.timedelta(minutes=1)


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


def tracking(request, session_id):
    log = Log.objects.get(id=session_id)
    address_list = []
    last_address = ''

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

            location = geolocator.reverse(coordinates, zoom=17, timeout=3)
            addresses = location.raw['address']
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

    return redirect('session_map', session_id=log.id)


def print_track(session_id):
    log = Log.objects.get(id=session_id)
    addresses = log.track_set.all()
    address_list = []
    last_address = ''

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


'''
# Comparar dos rutas en concreto?
# o comparar una ruta con todas indicando un indice de coincidencia?
def compare_two_routes(streets_to_compare, streets, percentage):
    intersection = set(streets_to_compare).intersection(streets)

    if not percentage:
        percentage = len(streets_to_compare) * 0.7

    if len(intersection) < len(streets) * (percentage / 100):
        print('si')
'''


def compare_all_routes(request, session_id, percentage=60):
    all_sessions = Log.objects.all().exclude(id=session_id)
    session_to_compare = Log.objects.get(id=session_id)
    addresses_to_compare = session_to_compare.track_set.all()
    streets_to_compare = []
    last_street_to_compare = ''
    similar_routes = {}

    for obj in addresses_to_compare.order_by('tracklog__time'):
        if obj.address != last_street_to_compare:
            streets_to_compare.append(obj.address)
            last_street_to_compare = obj.address

    for session in all_sessions:
        addresses = session.track_set.all()
        streets = []
        last_street = ''

        if not session.tracklog_set.all():
            tracking(request, session.id)

        for obj in addresses.order_by('tracklog__time'):
            # streets = []
            # last_street = ''

            if obj.address != last_street:
                streets.append(obj.address)
                last_street = obj.address

        # Compare 2 Routes
        # compare_two_routes(streets_to_compare, streets)
        # al hacer la intersección entre conjuntos no se considera el orden...
        intersection = set(streets_to_compare).intersection(streets)

        # umbral = trunc(len(streets_to_compare) * (percentage / 100))
        umbral = percentage
        try:
            match_percentage = round(len(intersection) / (len(streets_to_compare)) * 100, 1)
        except:
            match_percentage = 0

        if match_percentage >= umbral:
            similar_routes[session] = [intersection, match_percentage, len(intersection)]

    context = {
        'route': streets_to_compare,
        'similar_routes': similar_routes
    }

    return render(request, 'routes.html', context=context)


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
    # DATA


def separe_sessions(request):
    sessions = Log.objects.all()

    for session in sessions:

        records = session.record_set.all()
        separated = False
        log = None
        print('NUEVA SESSION ', session.id)
        print('-------------------------------------------------------------------------------------------------------')
        i = 0

        for record in records:

            if i == 0:
                last_time = record.time

            interval = record.time - last_time

            # print('now ', record.time)
            # print('last time', last_time)

            # print('interval', interval)

            if interval > datetime.timedelta(minutes=1):
                print('time ', record.time)
                print('last time', last_time)
                print('interval', interval)
                print('session_id', session.id)
                # print('entra en el intervalo')
                # log = Log.objects.create(session=now, email=session.email, id_app=session.id_app).save()
                separated = True

            if separated:
                pass
                # print('actualiza la tabla')
                # Record.objects.update(log_id=log.id).save()

            last_time = record.time
            i = i + 1


def session_in_map(request, session_id):
    sessions = Log.objects.all()
    session = Log.objects.get(id=session_id)
    res = query(session_id)
    # using_orm(request, session_id)
    crs_list = res[0]
    gjson_dict = {}
    gjson_dict["type"] = "FeatureCollection"
    points = []
    feat_list = []
    feat_list_track = []

    field_names = res[1]
    values = {}
    obd_speeds = []
    co2_inst = []
    lit_per_km = []
    lit_per_km_inst = []
    temps = []
    gps_speeds = []
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
        points.append([crs[10], crs[9]])

        # line_string_type_dict["geometry"] = mapping()
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
            co2_inst.append(crs[14][0:-5])

        co2_average = field_names[15]
        prop_dict[co2_average] = crs[15]

        engine_coolant = field_names[16]
        prop_dict[engine_coolant] = crs[16]
        if crs[16]:
            temps.append(crs[16][0:-3])

        liters_per_km = field_names[17]
        prop_dict[liters_per_km] = crs[17]
        if crs[17]:
            lit_per_km.append(crs[17][0:-8])

        gps_accuracy = field_names[18]
        prop_dict[gps_accuracy] = crs[18]

        gps_speed = field_names[19]
        prop_dict[gps_speed] = crs[19]
        if crs[19]:
            gps_speeds.append(crs[19][0:-5])

        obd_speed = field_names[20]
        prop_dict[obd_speed] = crs[20]
        if crs[20]:
            obd_speeds.append(crs[20][0:-5])

        speed_diff = field_names[21]
        prop_dict[speed_diff] = crs[21]

        speed_only_mov_average = field_names[22]
        prop_dict[speed_only_mov_average] = crs[22]

        android_battery_lvl = field_names[23]
        prop_dict[android_battery_lvl] = crs[23]

        liters_per_km_inst = field_names[24]
        prop_dict[liters_per_km_inst] = crs[24]
        if crs[24]:
            lit_per_km_inst.append(crs[24][0:-8])

        type_dict["properties"] = prop_dict
        feat_list.append(type_dict)

        # Name of streets
        # coordenates = (crs[9], crs[10])
        # location = rev(coordenates)
        # address = location.raw['address']

        '''
        if address:
            for key in address:
                if 'road' in key:
                    road = location.raw['address']['road']
                    if road not in track:
                        # print('added: ', road)
                        track.append(road)
                else:
                    # print('NO HAY NOMBRE DE CALLE --------------------- ')
                    # print(address)
        '''
    # print(points)
    # print(line_string_dict)
    # print(line_string_type_dict)
    geojson_line_track = '{\n' \
                         '    "features": [\n' \
                         '        {\n' \
                         '            "geometry": {\n' \
                         '                "coordinates":' + str(points) + ',\n' \
                                                                          '                "type": "LineString"\n' \
                                                                          '            },\n' \
                                                                          '            "properties":{},\n' \
                                                                          '            "type": "Feature"\n' \
                                                                          '        }\n' \
                                                                          '   ],\n' \
                                                                          '    "type":"FeatureCollection"\n' \
                                                                          '}'

    dict_dataframe = {'velocidad_gps': gps_speeds, 'co2': co2_inst, 'consumo': lit_per_km}
    # print(dict_dataframe)

    gjson_dict["features"] = feat_list

    # gjson_dict_track["features"] =
    data = json.dumps(gjson_dict, default=myconverter, sort_keys=True, indent=4, ensure_ascii=False)
    # print(data)

    gdf = geopandas.GeoDataFrame.from_features(gjson_dict['features'])
    # print(gdf)

    # traj = movingpandas.Trajectory(gdf, 1)
    # print(traj)
    # traj.plot()
    # print(feat_list[2].get('properties')['OBD Speed'])

    addresses = session.track_set.all()
    address_list = []
    last_address = ''

    if addresses:
        address_list = print_track(session_id)

    gps_speed_df = pandas.DataFrame(session.record_set.filter(sensor__pid='ff1001').values_list('value'),
                                    columns=['Velocidad GPS']).astype(float)
    # print(gps_speed_df.max())

    CO2_df = pandas.DataFrame(session.record_set.filter(sensor__pid='ff1257').values_list('value'),
                              columns=['CO2']).astype(float)

    temp_df = pandas.DataFrame(session.record_set.filter(sensor__pid='05').values_list('value'),
                               columns=['Temperatura del motor']).astype(float)

    # print(gps_speed_df.describe())

    # gps_speed_query = session.record_set.filter(sensor__pid='ff1001').values_list('value', flat=True)
    # co2_query = session.record_set.filter(sensor__pid='ff1257').values_list('value', flat=True)
    # print('----------------------------------------------------------------------------------------')
    # print(gps_speed_query)
    # mydict = {'gps_speed': gps_speed_query, 'co2': co2_query}
    dict_df = pandas.DataFrame({key: pandas.Series(value) for key, value in dict_dataframe.items()}, dtype=float)
    # print(dict_df)
    # print(dict_df.describe())
    '''
    gps_speed_max = None
    gps_speed_mean = None
    gps_speed_min = None
    gps_speed_q1 = None
    gps_speed_q2 = None
    gps_speed_q3 = None

    CO2_mean = None
    CO2_max = None
    CO2_min = None
    CO2_q1 = None
    CO2_q2 = None
    CO2_q3 = None

    temp_mean = None
    temp_max = None
    temp_min = None
    temp_q1 = None
    temp_q2 = None
    temp_q3 = None

    if gps_speed_df.empty:
        gps_speed_df = None
    elif not gps_speed_df.empty:
        gps_speed_mean = gps_speed_df.mean().values[0]
        gps_speed_max = gps_speed_df.max().values[0]
        gps_speed_min = gps_speed_df.min().values[0]
        gps_speed_q1 = gps_speed_df.quantile(.25).values[0]
        gps_speed_q2 = gps_speed_df.quantile(.5).values[0]
        gps_speed_q3 = gps_speed_df.quantile(.75).values[0]

    if CO2_df.empty:
        CO2_df = None
    elif not CO2_df.empty:
        CO2_mean = CO2_df.mean().values[0]
        CO2_max = CO2_df.max().values[0]
        CO2_min = CO2_df.min().values[0]
        CO2_q1 = CO2_df.quantile(.25).values[0]
        CO2_q2 = CO2_df.quantile(.5).values[0]
        CO2_q3 = CO2_df.quantile(.75).values[0]

    if temp_df.empty:
        temp_df = None
    elif not temp_df.empty:
        temp_mean = temp_df.mean().values[0]
        temp_max = temp_df.max().values[0]
        temp_min = temp_df.min().values[0]
        temp_q1 = temp_df.quantile(.25).values[0]
        temp_q2 = temp_df.quantile(.5).values[0]
        temp_q3 = temp_df.quantile(.75).values[0]
    '''

    context = {
        'data': data,
        'geojson_track': geojson_line_track,
        'session': session,
        'sessions': sessions,
        'summary': values,
        'dict_gps_speeds': gps_speeds,
        'dict_obd_speeds': obd_speeds,
        'dict_co2_inst': co2_inst,
        'dict_lit_per_km': lit_per_km,
        'dict_lit_per_km_inst': lit_per_km_inst,
        'dict_temps': temps,
        'dataframe_describe': dict_df.describe().round(2).to_html,
        'times': times,
        'address_list': address_list
        # 'gps_speed_mean': gps_speed_mean,
        # 'gps_speed_max': gps_speed_max,
        # 'gps_speed_min': gps_speed_min,
        # 'gps_speed_q1': gps_speed_q1,
        # 'gps_speed_q2': gps_speed_q2,
        # 'gps_speed_q3': gps_speed_q3,
        # 'CO2_mean': CO2_mean,
        # 'CO2_max': CO2_max,
        # 'CO2_min': CO2_min,
        # 'CO2_q1': CO2_q1,
        # 'CO2_q2': CO2_q2,
        # 'CO2_q3': CO2_q3,
        # 'temp_mean': temp_mean,
        # 'temp_max': temp_max,
        # 'temp_min': temp_min,
        # 'temp_q1': temp_q1,
        # 'temp_q2': temp_q2,
        # 'temp_q3': temp_q3,
        # 'temperature_df_describe': temp_df,
        # 'CO2_df_describe': CO2_df,
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
    session_app = request.GET.get('session')
    id_app = request.GET.get('id')
    email = request.GET.get('eml')
    time_app = request.GET.get('time')
    latitude = request.GET.get('kff1006')
    longitude = request.GET.get('kff1005')
    session_time = None
    log = None
    '''
    now = datetime.datetime.now()
    interval_time = now - TIME_LAST_HTTP_REQUEST

    if interval_time < TIME_TO_CONSIDER_NEW_SESSION:
        print('¿Almacenar nueva sesion, con que HORA?)
    '''

    logging.info(request)

    # TABLE LOG
    # session_time = datetime.fromtimestamp(session_app/1000) + timedelta(hours=1)\
    #                   .strftime('%Y-%m-%d %H:%M:%S' '.' '%f')
    if session_app:
        session_time = make_aware(datetime.datetime.fromtimestamp(int(session_app) / 1000))
        st = session_time.strftime('%Y-%m-%d %H:%M:%S' '.' '%f')
        st = session_time.strptime(st, '%Y-%m-%d %H:%M:%S' '.' '%f')
        session_time = st

    # session_time += datetime.timedelta(hours=1)
    # aware_datetime = make_aware(session_time)

    if session_time and email and id_app:
        try:
            log = Log.objects.get(session=session_time, email=email, id_app=id_app)
        except Log.DoesNotExist:
            try:
                Log(session=session_time, email=email, id_app=id_app).save()
            except:
                pass
    ''' 
    log, created = Log.objects.get_or_create(session=session_time, email=email, id_app=id_app)
    if created:
        Log(session=session_time, email=email, id_app=id_app, dataset_id=None).save()
    '''

    for key, value in request.GET.items():

        # TABLE DATA_TORQUE (unneeded)
        '''
        try:
            with transaction.atomic():
                DataTorque(key=key, value=value, session=session_time, email=email, id_app=id_app, time=time_app,
                           latitude=latitude, longitude=longitude).save()
        except:
            pass
        '''

        # patron = "(kff)|(k[d|5])"
        # patron_OK = "(kff[0-9]{1,4}|k[0-9a-z]{0,3})"
        # print(patron)

        # TABLE SENSOR AND TABLE RECORD
        '''
        if 'FullName' in key or 'ShortName' in key or 'userUnit' in key or \
                'defaultUnit' in key or 'kff' in key or 'kd' in key or 'k5' in key:
        '''
        # if 'Name' in key or 'Unit' in key or 'k' in key:  # 'kff' in key or 'kd' in key or 'k5' in key:

        pid = ''

        '''
        if 'Name05' in key or 'Unit05' in key or '0d' in key or '0c' in key:
            pid = key[-2:]
        else:
            pid = key[-6:]
        '''

        if 'Name' in key or 'Unit' in key:

            if 'ff' in key:
                pid = key[-6:]

            if '0d' in key or '0c' in key or '05' in key or '83' in key:
                pid = key[-2:]

            '''
            other_options = ['0d', '0c', '05', '83']
            # Same as check if ('0d' in key OR '0c' in key OR ...)
            for option in other_options:
                if option in key:
                    # pid = key[-2:]
                    pid = key[key.find(option):] # .find no funciona porque key no es un string parece...
            '''

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
        elif 'kff' in key or 'kd' in key or 'k5' in key or 'kc' in key:

            if 'ff' in key:
                pid = key[-6:]
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

            if 'E' in value or 'inf' in value or 'Inf' in value:
                value = 0

            Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time, latitude=latitude,
                   longitude=longitude).save()

    return HttpResponse('OK!')
