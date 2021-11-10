import json
import os
from builtins import print

import numpy as np
import pandas as pd
import seaborn as sns

from django.contrib import messages
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils.datetime_safe import datetime
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from geopy.geocoders import Nominatim
from matplotlib import pyplot as plt

from shapely.geometry import Point, mapping
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse, FileResponse
import datetime
from django.shortcuts import render, redirect
import pandas
import logging

# Create your views here.
from rest_framework import viewsets
from weasyprint import HTML

from Torque.settings import MEDIA_ROOT
from ai import k_means as km, svm
from ai.common import get_base64
from models.models import Log, Record, Sensor, Track, TrackLog
from models.serializers import LogSerializer, RecordSerializer, SensorSerializer

geolocator = Nominatim(user_agent="Torque")

# rev = RateLimiter(geolocator.reverse, min_delay_seconds=0.001)

logging.basicConfig(filename='./logs/InfoLog.log', level=logging.INFO)
logging.basicConfig(filename='./logs/WarningLog.log', level=logging.WARNING)
logging.basicConfig(filename='./logs/ErrorLog.log', level=logging.ERROR)

TIME_LAST_HTTP_REQUEST = datetime.datetime.now()
TIME_TO_CONSIDER_NEW_SESSION = datetime.timedelta(minutes=1)

exclude_sensor_list = ['', 'GPS Latitude', 'GPS Longitude', 'Android device Battery Level']


class LogViewSet(viewsets.ModelViewSet):
    serializer_class = LogSerializer
    queryset = Log.objects.all()


class RecordViewSet(viewsets.ModelViewSet):
    serializer_class = RecordSerializer
    queryset = Record.objects.all()


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    queryset = Sensor.objects.all()


def sessions_by_id_list(request):
    sessions = Log.objects.all()
    return render(request, 'sessions_list.html', context={'sessions': sessions})


def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def upload_csv(request):
    if request.method == 'GET':
        return render(request, 'upload_csv.html')

    if not request.FILES:
        messages.error(request, 'Seleccione un fichero con extensión .CSV')
        return render(request, 'upload_csv.html')

    csv_file = request.FILES['file']
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'El fichero no tiene extensión .CSV')

    return pca_request(request)


def export_pdf(request, filename):
    path_to_file = os.path.join(MEDIA_ROOT, 'reports', filename)
    response = FileResponse(open(path_to_file, 'rb'), as_attachment=True)
    return response


def pca_request(request):
    # Apply k-means to the CSV
    if request.method == 'POST':
        two_first_components_plot, components_and_features_plot, wcss_plot, cumulative_explained_variance_ratio_plot, \
        explained_variance_ratio, cluster_list, more_important_features, svm_params = \
            km.start(request.FILES.get("file"))
        # Apply SVM to the data labelled by k-means
        svm_plot = svm.start(
            svm_params['df'], svm_params['x_scaled_reduced'], svm_params['clusters_number'])

        explained_variance_ratio = [explained_variance_ratio[i] * 100 for i in
                                    range(len(explained_variance_ratio))]

        filename = 'report.pdf'
        if request.FILES:
            filename = request.FILES['file'].name
            filename = filename.replace('csv', 'pdf')

        context = {
            'twoFirstComponentsPlot': two_first_components_plot,
            'componentsAndFeaturesPlot': components_and_features_plot,
            'wcssPlot': wcss_plot,
            'cumulativeExplainedVarianceRatioPlot': cumulative_explained_variance_ratio_plot,
            'explainedVarianceRatio': explained_variance_ratio,
            'clusterList': cluster_list,
            'moreImportantFeatures': more_important_features,
            'svmPlot': svm_plot,
            'filename': filename
        }

        path_to_file = os.path.join(MEDIA_ROOT, 'reports', filename)
        html = render_to_string("html_to_pdf.html", context)
        HTML(string=html).write_pdf(path_to_file)
        # result = html.write_pdf()
        return render(request, 'classification_result.html', context=context)


def svm_classification_request(request):
    classification_list = svm.classify_svm(request.FILES.get("file"), int(
        request.args.get('dataset-rows-number')))

    return JsonResponse({'classificationList': classification_list})


def tracking_all_sessions(request):
    sessions = Log.objects.all()
    address_list = []
    last_address = ''

    with transaction.atomic():
        logging.info('TRACKING_ALL_SESSIONS STARTED')
        # Vaciamos la tabla primero
        TrackLog.objects.all().delete()
        logging.info('Se vacia la tabla TrackLog para volver a obtener los nombres de las calles de todas las sesiones')
        # print(TrackLog.objects.all())

        for session in sessions:

            records = Log.objects.get(id=session.id).record_set.all()
            last_time = None
            i = 0

            for obj in records:
                newest_time = obj.time.second

                if i == 0:
                    last_time = (newest_time - newest_time) + 15

                interval = (newest_time - last_time) % 60

                if interval >= 10:
                    coordinates = (obj.latitude, obj.longitude)

                    location = geolocator.reverse(coordinates, zoom=17, timeout=10)
                    addresses = location.raw['address']
                    simple_address = ''

                    try:
                        road = addresses['road']
                        simple_address += road
                    except KeyError:
                        road = None

                    if road:
                        with transaction.atomic():
                            trck, created = Track.objects.get_or_create(address=simple_address)
                            if created:
                                TrackLog.objects.create(track=trck, log=session, time=obj.time).save()

                            else:
                                trck = Track.objects.get(address=simple_address)
                                TrackLog.objects.create(track=trck, log=session, time=obj.time).save()

                        if trck.address != last_address:
                            address_list.append(trck.address)
                            last_address = trck.address

                    last_time = obj.time.second
                    i += 1
            # print('session acabada ', session.id)
            # logging.info('TRACKING_ALL_SESSIONS FINISHED')
            context = {
                'text': 'Se han obtenido todos los nombres de las calles de todos los recorridos'
            }

    return render(request, 'success.html', context=context)


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

        if interval >= 10:
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


def obtain_summary(session_id):
    dataframe = obtain_dataframe(session_id)
    dictionary = {}

    if 'FUEL_USED' in dataframe.columns:
        dictionary['TOTAL_FUEL_USED'] = dataframe['TOTAL_FUEL_USED'].tolist()

    if 'TRIPTIME' in dataframe.columns:
        dictionary['TOTAL_TIME'] = dataframe['TOTAL_TIME'].tolist()

    if 'TRIP' in dataframe.columns:
        dictionary['TOTAL_TRIP'] = dataframe['TOTAL_TRIP'].tolist()

    if 'TOTAL_HGWY' in dataframe.columns:
        dictionary['TOTAL_HGWY'] = dataframe['TOTAL_HGWY'].tolist()

    if 'TOTAL_CITY' in dataframe.columns:
        dictionary['TOTAL_CITY'] = dataframe['TOTAL_CITY'].tolist()

    if 'TOTAL_IDLE' in dataframe.columns:
        dictionary['TOTAL_IDLE'] = dataframe['TOTAL_IDLE'].tolist()

    return dictionary


def download_summary_all_sessions(request):
    logs = Log.objects.all().order_by('-id')
    final_df = pandas.DataFrame()

    for log in logs:

        dataframe = obtain_dataframe(log.id)
        dict_dataframe = {}

        if 'TOTAL_FUEL_USED' in dataframe.columns:
            fuel = dataframe['TOTAL_FUEL_USED'].tolist()
            dict_dataframe['TOTAL_FUEL_USED'] = fuel

        if 'TOTAL_TIME' in dataframe.columns:
            duration = dataframe['TOTAL_TIME'].tolist()
            dict_dataframe['TOTAL_TIME'] = duration

        if 'TOTAL_TRIP' in dataframe.columns:
            distance = dataframe['TOTAL_TRIP'].tolist()
            dict_dataframe['TOTAL_TRIP'] = distance

        if 'TOTAL_HGWY' in dataframe.columns:
            highway = dataframe['TOTAL_HGWY'].tolist()
            dict_dataframe['TOTAL_HGWY'] = highway

        if 'TOTAL_CITY' in dataframe.columns:
            city = dataframe['TOTAL_CITY'].tolist()
            dict_dataframe['TOTAL_CITY'] = city

        if 'TOTAL_IDLE' in dataframe.columns:
            idle = dataframe['TOTAL_IDLE'].tolist()
            dict_dataframe['TOTAL_IDLE'] = idle

        if 'STOP_LESS_4_SEC' in dataframe.columns:
            stop_less_4sec = dataframe['STOP_LESS_4_SEC'].tolist()
            dict_dataframe['STOP_LESS_4_SEC'] = stop_less_4sec

        if 'STOP_LESS_6_SEC' in dataframe.columns:
            stop_less_6sec = dataframe['STOP_LESS_6_SEC'].tolist()
            dict_dataframe['STOP_LESS_6_SEC'] = stop_less_6sec

        if 'STOP_MORE_EQ_6_SEC' in dataframe.columns:
            stop_more_eq_6sec = dataframe['STOP_MORE_EQ_6_SEC'].tolist()
            dict_dataframe['STOP_MORE_EQ_6_SEC'] = stop_more_eq_6sec

        if 'TOTAL_STOP_COUNT' in dataframe.columns:
            stop_count = dataframe['TOTAL_STOP_COUNT'].tolist()
            dict_dataframe['TOTAL_STOP_COUNT'] = stop_count

        if 'TOTAL_CAR_OFF' in dataframe.columns:
            car_off = dataframe['TOTAL_CAR_OFF'].tolist()
            dict_dataframe['TOTAL_CAR_OFF'] = car_off

        dict_df = pandas.DataFrame({key: pandas.Series(value) for key, value in dict_dataframe.items()}, dtype=float)
        dict_df.insert(loc=0, column='SESSION_ID', value=log.id)

        final_df = final_df.append(dict_df)

    final_df.drop_duplicates(inplace=True)
    final_df.reset_index(drop=True, inplace=True)
    print(final_df)

    filename = 'all_sessions'
    time_now = datetime.datetime.now()

    content = 'attachment; filename=' + filename + '_%s.csv' % time_now.isoformat()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content  # 'attachment; filename="session.csv"'
    final_df.to_csv(path_or_buf=response, index=False)

    return response


def download_csv_all_sessions(request):
    logs = Log.objects.all().order_by('id')
    final_df = pandas.DataFrame()

    for log in logs:
        dict_df = obtain_dataframe(log.id)
        dict_df.insert(loc=0, column='SESSION_ID', value=log.id)
        final_df = final_df.append(dict_df)

    clean_dataset(final_df)
    final_df.reset_index(drop=True, inplace=True)

    filename = 'all_sessions'
    time_now = datetime.datetime.now()

    content = 'attachment; filename=' + filename + '_%s.csv' % time_now.isoformat()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content  # 'attachment; filename="session.csv"'
    final_df.to_csv(path_or_buf=response, index=False)

    return response


def obtain_dataframe(session_id):
    log = Log.objects.get(id=session_id)
    records = log.record_set.all()
    dictionary = {}
    sensors_id = records.values_list('sensor_id', flat=True) \
        .exclude(sensor__user_full_name__in=exclude_sensor_list).distinct().order_by('sensor_id')

    for sensor_id in list(sensors_id):
        sensor_name = Sensor.objects.get(id=sensor_id). \
            user_short_name.replace('%', '').replace('₂', '2').replace(' ', '_'). \
            replace('(', '_').replace(')', '').replace(
            '.',
            '_').upper()
        values = records.filter(sensor_id=sensor_id).values_list('value', flat=True)
        list_values = list(values)
        dictionary[sensor_name] = list_values

    # records.filter(sensor__pid='')
    # print(dictionary)
    dict_df = pandas.DataFrame({key: pandas.Series(value) for key, value in dictionary.items()}, dtype=float)

    # Calculated data
    stops = obtain_stops(session_id)
    # print(stops)
    dict_df.insert(loc=len(dict_df.columns), column='STOP_LESS_4_SEC', value=stops['stop_less_4_seconds'])
    dict_df.insert(loc=len(dict_df.columns), column='STOP_LESS_6_SEC', value=stops['stop_less_6_seconds'])
    dict_df.insert(loc=len(dict_df.columns), column='STOP_MORE_EQ_6_SEC', value=stops['stop_more_eq_6_seconds'])
    dict_df.insert(loc=len(dict_df.columns), column='TOTAL_STOP_COUNT', value=stops['total_stop_count'])
    dict_df.insert(loc=len(dict_df.columns), column='TOTAL_CAR_OFF', value=stops['count_car_off'])

    if 'TRIPTIME' in dict_df.columns:
        dict_df.insert(loc=len(dict_df.columns), column='TOTAL_TIME', value=dict_df['TRIPTIME'].max())

    if 'TRIP' in dict_df.columns:
        dict_df.insert(loc=len(dict_df.columns), column='TOTAL_TRIP', value=dict_df['TRIP'].max())

    if 'FUEL_USED' in dict_df.columns:
        dict_df.insert(loc=len(dict_df.columns), column='TOTAL_FUEL_USED', value=dict_df['FUEL_USED'].max())

    if 'HGWY' in dict_df.columns:
        dict_df.insert(loc=len(dict_df.columns), column='TOTAL_HGWY', value=dict_df['HGWY'].iloc[-1])

    if 'CITY' in dict_df.columns:
        dict_df.insert(loc=len(dict_df.columns), column='TOTAL_CITY', value=dict_df['CITY'].iloc[-1])

    if 'IDLE' in dict_df.columns:
        dict_df.insert(loc=len(dict_df.columns), column='TOTAL_IDLE', value=dict_df['IDLE'].iloc[-1])

    clean_dataset(dict_df)

    return dict_df


def download_csv(request, session_id):
    dict_df = obtain_dataframe(session_id)
    # hasta aca
    # dataframe = obtain_dataframe(session_id=session_id)

    filename = 'session' + str(session_id)
    time_now = datetime.datetime.now()

    content = 'attachment; filename=' + filename + '_%s.csv' % time_now.isoformat()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content  # 'attachment; filename="session.csv"'
    dict_df.to_csv(path_or_buf=response, index=False)
    # print(dataframe)

    return response


def export_data_to_csv(request):
    session_queryset = Log.objects.all().order_by('-id')
    sensors = Sensor.objects.all().exclude(user_full_name__in=exclude_sensor_list).order_by('id')

    context = {
        'sessions': session_queryset,
        'sensors': sensors,
    }

    return render(request, 'export_csv.html', context=context)


def obtain_sensors_from_session(request, session_id):
    session = Log.objects.get(id=session_id)
    records = session.record_set.all()

    sensors = records.values_list('sensor_id', 'sensor__user_full_name') \
        .exclude(sensor__user_full_name__in=exclude_sensor_list).distinct().order_by('sensor_id')

    # sensors = sensors.values_list('sensor_id', 'sensor__user_full_name')
    return JsonResponse({"sensors": list(sensors)})


def obtain_sessions_from_sensor(request, sensor_id):
    sensor = Sensor.objects.get(id=sensor_id)
    records = sensor.record_set.all()

    sessions = records.values('log_id', 'log__email', 'log__session') \
        .exclude(sensor__user_full_name__in=exclude_sensor_list).distinct().order_by('-log_id')

    # print(sessions)
    # sessions = sessions.values_list('sensor_id', 'log__email', 'log__session')
    # print(sessions)
    return JsonResponse({"sessions": list(sessions)})


@csrf_exempt
def generate_custom_csv(request):
    id_session = request.POST['sesiones']
    id_sensors = [value for key, value in request.POST.items() if 'sensor' in key]
    log = Log.objects.get(id=id_session)
    dictionary = {}

    for id_sensor in id_sensors:
        sensor_name = Sensor.objects.get(id=id_sensor).user_short_name.replace('%', '').replace('₂', '2'). \
            replace(' ', '_').replace('(', '_').replace(')', '').replace('.', '_').upper()

        values = log.record_set.filter(sensor_id=id_sensor).values_list('value', flat=True)
        # print(sensor_name)
        list_values = list(values)
        dictionary[sensor_name] = list_values

    dict_df = pandas.DataFrame({key: pandas.Series(value) for key, value in dictionary.items()}, dtype=float)
    clean_dataset(dict_df)
    # print(dict_df)
    # dict_df.reset_index(drop=True, inplace=True)

    filename = 'session' + str(id_session)
    time_now = datetime.datetime.now()

    content = 'attachment; filename=' + filename + '_%s.csv' % time_now.isoformat()
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = content  # 'attachment; filename="session.csv"'
    dict_df.to_csv(path_or_buf=response, index=False)

    return response


@csrf_exempt
def generate_csv_multiple_sessions(request):
    id_sensor = request.POST['sensores']
    sensor = Sensor.objects.get(id=id_sensor)
    id_sessiones = [value for key, value in request.POST.items() if 'session' in key]

    # log = Log.objects.get(id=id_sensor)
    dictionary = {}

    for id_session in id_sessiones:
        '''
        sensor_name = Log.objects.get(id=id_session).replace('%', '').user_short_name.replace('₂', '2'). \
            replace(' ', '_').replace('(', '_').replace(')', '').replace('.', '_').upper()
        '''
        values = sensor.record_set.filter(log_id=id_session).values_list('value', flat=True)
        # print(sensor_name)
        dictionary[id_session] = list(values)

    dict_df = pandas.DataFrame({key: pandas.Series(value) for key, value in dictionary.items()}, dtype=float)
    clean_dataset(dict_df)
    dict_df = dict_df.set_index(dict_df.columns[0]).transpose()

    filename = sensor.user_short_name.replace('%', '').replace('₂', '2'). \
                   replace(' ', '_').replace('(', '_').replace(')', '').replace('.', '_').upper() + '_all_sessions'
    time_now = datetime.datetime.now()
    content = 'attachment; filename=' + filename + '_%s.csv' % time_now.isoformat()
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = content  # 'attachment; filename="session.csv"'
    dict_df.to_csv(path_or_buf=response, index=False)

    return response
    # return HttpResponse('OK')


def export_sensors_for_react_app(request):
    sensors = Sensor.objects.all().exclude(user_full_name__in=exclude_sensor_list)
    data = []
    final_dict = {}
    for sensor in sensors:
        item = {
            'pid': sensor.user_short_name.replace('%', '').replace('₂', '2'). \
                replace(' ', '_').replace('(', '_').replace(')', '').replace('.', '_').upper(),
            'description': sensor.user_full_name,
            'measurement_unit': sensor.user_unit
        }
        data.append(item)
    final_dict['sensors'] = data
    jsonData = json.dumps(final_dict, ensure_ascii=False, indent=2).encode('utf8')
    # print(jsonData)
    content = 'attachment; filename=sensors_information.json'
    response = HttpResponse(jsonData, content_type='application/json')

    response['Content-Disposition'] = content  # 'attachment; filename="session.csv"'

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
          'Total_Trip_Fuel_Used as `Trip Fuel Used(l)`,' \
          'Total_Trip_Distance as `Trip Distance(km)`, ' \
          'CO2_Average as `Trip CO2 Average(g/km)`, ' \
          'Speed_Only_Mov_Average as `Trip Speed Only Moving Average(km/h)`, ' \
          'right(left(record_time, 19), 8) as `Time Now`, ' \
          'latitude, ' \
          'longitude, ' \
          'max(case when pid = "ff1266" then substr(sec_to_time(value), 1, 8) else null end) as `Duration`, ' \
          'max(case when pid = "ff1204" then value else null end) as `Distance(km)`, ' \
          'max(case when pid = "ff1271" then value else null end) as `Fuel Used(l)`, ' \
          'max(case when pid = "ff1257" then value else null end) as `CO2 Instantaneous(g/km)`, ' \
          'max(case when pid = "ff1258" then value else null end) as `CO2 Average(g/km)`, ' \
          'max(case when pid = "05" then value else null end) as `Engine Coolant Temperature(ºC)`, ' \
          'max(case when pid = "ff1208" then value else null end) as `Liters per kilometer Average(l/100km)`, ' \
          'max(case when pid = "ff1239" then value else null end) as `GPS Accuracy(m)`, ' \
          'max(case when pid = "ff1001" then value else null end) as `GPS Speed(km/h)`, ' \
          'max(case when pid = "0d" then value else null end) as `OBD Speed(km/h)`, ' \
          'max(case when pid = "ff1237" then value else null end) as `GPS vs OBD Speed difference(km/h)`, ' \
          'max(case when pid = "ff1263" then value else null end) as `Speed Average Only Moving(km/h)`, ' \
          'max(case when pid = "ff129a" then value else null end) as `Android device Battery level`, ' \
          'max(case when pid = "ff1207" then value else null end) as `Litres per kilometer Instantaneous(l/100km)`, ' \
          'max(case when pid = "0c" then value else null end) as `Engine RPM(rpm)` ' \
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
          '                 round(r.value, 2) AS value, r.latitude, r.longitude ' \
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
          '                     max(case when s.pid = "ff1204" then round(value, 2) ' \
          '                             else null end) AS `Total_Trip_Distance`,' \
          '                     max(case when s.pid = "ff1266" then substr(sec_to_time(r.value), 1, 8) else null end) ' \
          '                         AS `Total_Trip_Time`,' \
          '                     max(case when s.pid = "ff1271" then round(value, 2) ' \
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
          '                 l.id as log_id, round(r.value, 2) as `CO2_Average` ' \
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
          '                 l.id as log_id, round(r.value, 2) as `Speed_Only_Mov_Average` ' \
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


@transaction.atomic
def separe_sessions(request):
    logging.info('SEPARE_SESSIONS STARTED ')

    sessions = Log.objects.all()
    time_for_new_session = datetime.timedelta(hours=0, minutes=1, seconds=30)

    for session in sessions:

        records = session.record_set.all().order_by('time')
        separated = False
        log = None
        i = 0
        first_time_speed = True
        timekeeper = datetime.timedelta(hours=0, minutes=0, seconds=0)
        last_time_speed = 0
        contador = 0

        for record in records:

            if i == 0:
                last_time = record.time

            with transaction.atomic():
                if not separated:
                    if record.sensor.pid == 'ff1001' and record.value == '0.0':
                        # print(timekeeper)
                        # print(last_time_speed)
                        if first_time_speed:
                            first_time_speed = False
                            last_time_speed = record.time
                        elif not first_time_speed:
                            timekeeper += record.time - last_time_speed

                        if timekeeper > time_for_new_session:
                            # timekeeper = datetime.timedelta(hours=0, minutes=0, seconds=0)
                            separated = True

                            try:
                                # print('se crea nueva SESION\n')
                                l = Log(session=record.time, email=session.email,
                                        id_app=session.id_app)
                                l.save()
                                logging.info('Se crea una nueva sesion ' + str(l.id))

                                update_records = Record.objects.filter(log_id=record.log_id, time__gte=record.time)

                                for rec in update_records:
                                    contador += 1
                                    r = Record.objects.get(id=rec.id)
                                    r.log_id = l.id
                                    r.save()
                                break

                            except Exception as e:
                                logging.error('No se ha podido crear la sesion ', l.id, ' - ', record.time, ' por: ',
                                              e.args)
                                # print('No se ha podido crear la sesion ', l.id, ' - ', record.time, ' por: ', e.args)
                                # raise e

                            # print('deberia entrar')
                            # print('La sesion ', session.id, ' deberia dividirse en la sesion ', record.time)
                            # print('acumulados: ', timekeeper)

                        last_time_speed = record.time

                    elif record.sensor.pid == 'ff1001' and record.value != '0.0':
                        first_time_speed = True
                        # print('reiniciar contador')
                        timekeeper = datetime.timedelta(hours=0, minutes=0, seconds=0)

                # else:
                # if log:
                # contador += 1
                # r = Record.objects.get(id=record.id)
                # r.log_id = log.id
                # r.save()
                # pass
                # print('Separado')
                # Record.objects.update(log_id=log.id, time__gt=record.time).save()
                # session.record_set.filter(time__gte=record.time).update(log_id=log.id) REVISAR EL LOG.ID

            last_time = record.time
            i = i + 1

        logging.info('De la sesion ' + str(session.id) + ' se actualizaron ' + str(contador) + ' registros')
        # print('De la sesion ', session.id, ' se actualizaran ', contador, ' registros')

    # Session with not enought info --> DELETE
    for session in sessions:
        records = session.record_set.all().order_by('time')
        distance = records.filter(sensor__pid='ff1204').aggregate(Max('value'))
        duration = records.filter(sensor__pid='ff1266').aggregate(Max('value'))
        delete = False
        # print(time)
        # Check number of records

        if records.count() < 300:
            delete = True
            # print('DELETED SESION ', session.id, 'POCOS REGISTROS')
            logging.info('DELETED SESION ' + str(session.id) + ' POCOS REGISTROS')
        else:
            if not distance['value__max'] and not duration['value__max']:
                delete = True
                # print('DELETED SESION ', session.id, 'NI RECORRIDO NI DURACION')
                logging.info('DELETED SESION ' + str(session.id) + ' NI RECORRIDO NI DURACION')
            if distance['value__max'] and float(distance['value__max']) < 2:
                delete = True
                # print('entra')
                # print('DELETED SESION ', session.id, ' POR CORTO RECORRIDO')
                logging.info('DELETED SESION ' + str(session.id) + ' POR CORTO RECORRIDO')

            if duration['value__max']:
                duration = duration['value__max']
                duration_session = datetime.timedelta(seconds=float(duration))
                if duration_session < datetime.timedelta(minutes=15):
                    delete = True
                    # print('DELETED SESION ', session.id, ' POR CORTA DURACION')
                    logging.info('DELETED SESION ' + str(session.id) + ' POR CORTA DURACION')

        if delete:
            session.delete()
            logging.info('Se han eliminado sesiones')
        if not delete:
            logging.info('No se han eliminado sesiones')

    context = {
        'text': 'Se han separado las sesiones correctamente'
    }
    return render(request, 'success.html', context=context)


def obtain_stops(session_id):
    session = Log.objects.get(id=session_id)
    records = session.record_set.filter(sensor__pid='0d') | session.record_set.filter(sensor__pid='0c'). \
        order_by('id')

    timekeeper = datetime.timedelta(hours=0, minutes=0, seconds=0)
    timekeeper_car_off = datetime.timedelta(hours=0, minutes=0, seconds=0)
    total_stop_count = 0
    stop_less_4_seconds = 0
    counted_4_seconds = False
    stop_less_6_seconds = 0
    counted_6_seconds = False
    stop_more_eq_6_seconds = 0
    counted_more_eq_6_seconds = False
    count_car_off = 0
    counted_car_off = False
    # Possible traffic light
    counted_stop = False
    first_time = True
    first_time_car_off = True
    reset = False
    reset_car_off = False

    for record in records:
        if record.sensor.pid == '0d':

            if record.value and float(record.value) == 0:

                if reset:
                    reset = False

                if first_time:
                    first_time = False
                    last_time = record.time

                timekeeper += record.time - last_time

                if not counted_4_seconds and timekeeper < datetime.timedelta(hours=0, minutes=0, seconds=4):
                    stop_less_4_seconds += 1
                    counted_4_seconds = True

                if not counted_6_seconds and timekeeper <= datetime.timedelta(hours=0, minutes=0, seconds=6):
                    stop_less_6_seconds += 1
                    stop_less_4_seconds -= 1
                    counted_6_seconds = True

                if not counted_more_eq_6_seconds and timekeeper > datetime.timedelta(hours=0, minutes=0, seconds=6):
                    stop_more_eq_6_seconds += 1
                    stop_less_6_seconds -= 1
                    counted_more_eq_6_seconds = True

                if not counted_stop:
                    counted_stop = True
                    total_stop_count = total_stop_count + 1

                last_time = record.time

            else:
                if not reset:
                    reset = True
                    timekeeper = datetime.timedelta(hours=0, minutes=0, seconds=0)
                    counted_stop = False
                    first_time = True
                    counted_4_seconds = False
                    counted_6_seconds = False
                    counted_more_eq_6_seconds = False

        if record.sensor.pid == '0c':

            if record.value and float(record.value) == 0:
                if reset_car_off:
                    reset_car_off = False

                # print('COCHE CALADO a las ', record.time)

                if first_time_car_off:
                    first_time_car_off = False
                    last_time = record.time

                else:
                    if not counted_car_off:
                        counted_car_off = True
                        count_car_off += 1

                timekeeper_car_off += record.time - last_time
                last_time = record.time

            else:
                if not reset_car_off:
                    reset_car_off = True
                    timekeeper_car_off = datetime.timedelta(hours=0, minutes=0, seconds=0)
                    counted_car_off = False
                    first_time_car_off = True

    '''
    print('paradas totales: ', total_stop_count)
    print('stop_less_4_seconds: ', stop_less_4_seconds)
    print('stop_less_6_seconds: ', stop_less_6_seconds)
    print('stop_more_eq_6_seconds: ', stop_more_eq_6_seconds)
    print('numero de caladas: ', count_car_off)
    '''
    dictionary = {
        'total_stop_count': total_stop_count,
        'stop_less_4_seconds': stop_less_4_seconds,
        'stop_less_6_seconds': stop_less_6_seconds,
        'stop_more_eq_6_seconds': stop_more_eq_6_seconds,
        'count_car_off': count_car_off
    }
    return dictionary


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

    field_names = res[1]
    # values = {}
    obd_speeds = []
    co2_inst = []
    co2_avg = []
    lit_per_km = []
    lit_per_km_inst = []
    engine_revs = []
    temps = []
    gps_speeds = []
    times = []

    # print(crs_list)

    start_coordinates = [crs_list[0][9], crs_list[0][10]]
    finish_coordinates = [crs_list[len(crs_list) - 1][9], crs_list[len(crs_list) - 1][10]]

    for crs in crs_list:
        type_dict = {}
        pt_dict = {}
        prop_dict = {}

        # total_trip_time = field_names[3]
        total_trip_time = 'Duracion'
        # values[total_trip_time] = crs[3]
        # total_trip_fuel_used = field_names[4]
        total_trip_fuel_used = 'Combustible'
        # values[total_trip_fuel_used] = crs[4]
        # total_trip_distance = field_names[5]
        total_trip_distance = 'Distancia'
        # values[total_trip_distance] = crs[5]
        # trip_co2_average = field_names[6]
        trip_co2_average = 'C0₂ medio'
        # values[trip_co2_average] = crs[6]
        # trip_speed_only_mov_average = field_names[7]
        trip_speed_only_mov_average = 'Velocidad media (movimiento)'
        # values[trip_speed_only_mov_average] = crs[7]

        type_dict["type"] = "Feature"

        pt_dict["type"] = "Point"

        # GEOJSON looks for long,lat so reverse order
        type_dict["geometry"] = mapping(Point(crs[10], crs[9]))
        points.append([crs[10], crs[9]])

        email = field_names[1]
        prop_dict[email] = crs[1]

        date = field_names[2]
        prop_dict[date] = crs[2]

        time_now = field_names[8]
        prop_dict[time_now] = crs[8]
        if crs[8]:
            times.append(crs[8])

        trip_time = field_names[11]
        prop_dict[trip_time] = crs[11]

        trip_distance = field_names[12]
        prop_dict[trip_distance] = crs[12]

        trip_fuel_used = field_names[13]
        prop_dict[trip_fuel_used] = crs[13]

        c02_instantaneous = field_names[14]
        prop_dict[c02_instantaneous] = crs[14]
        if crs[14]:
            co2_inst.append(crs[14])

        co2_average = field_names[15]
        prop_dict[co2_average] = crs[15]
        if crs[15]:
            co2_avg.append(crs[15])

        engine_coolant = field_names[16]
        prop_dict[engine_coolant] = crs[16]
        if crs[16]:
            temps.append(crs[16])

        liters_per_km = field_names[17]
        prop_dict[liters_per_km] = crs[17]
        if crs[17]:
            lit_per_km.append(crs[17])

        gps_accuracy = field_names[18]
        prop_dict[gps_accuracy] = crs[18]

        gps_speed = field_names[19]
        prop_dict[gps_speed] = crs[19]
        if crs[19]:
            gps_speeds.append(crs[19])

        obd_speed = field_names[20]
        prop_dict[obd_speed] = crs[20]
        if crs[20]:
            obd_speeds.append(crs[20])

        speed_diff = field_names[21]
        prop_dict[speed_diff] = crs[21]

        speed_only_mov_average = field_names[22]
        prop_dict[speed_only_mov_average] = crs[22]

        android_battery_lvl = field_names[23]
        prop_dict[android_battery_lvl] = crs[23]

        liters_per_km_inst = field_names[24]
        prop_dict[liters_per_km_inst] = crs[24]
        if crs[24]:
            lit_per_km_inst.append(crs[24])

        engine_rpm = field_names[25]
        prop_dict[engine_rpm] = crs[25]
        if crs[25]:
            engine_revs.append(crs[25])

        type_dict["properties"] = prop_dict
        feat_list.append(type_dict)

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
    # print(co2_avg)
    dict_dataframe = {}
    values = {}
    dataframe = obtain_dataframe(session_id)

    if 'SPEED' in dataframe.columns:
        obd_speeds = dataframe['SPEED'].tolist()
        dict_dataframe['SPEED'] = obd_speeds
        # values['Velocidad media'] = str(round(dataframe['SPEED'].mean(), 2)) + ' km/h'

    if 'GPS_SPD' in dataframe.columns:
        gps_speeds = dataframe['GPS_SPD'].tolist()
        dict_dataframe['GPS_SPD'] = gps_speeds

    if 'CO2' in dataframe.columns:
        co2_inst = dataframe['CO2'].tolist()
        dict_dataframe['CO2'] = co2_inst
        values['CO₂ medio'] = str(round(dataframe['CO2'].mean(), 2)) + ' g/km'

    if 'AV_CO2' in dataframe.columns:
        co2_avg = dataframe['AV_CO2'].tolist()
        dict_dataframe['AV_CO2'] = co2_avg

    if 'LPK' in dataframe.columns:
        lit_per_km_inst = dataframe['LPK'].tolist()
        dict_dataframe['LPK'] = lit_per_km_inst

    if 'TRIP_LPK' in dataframe.columns:
        lit_per_km = dataframe['TRIP_LPK'].tolist()
        dict_dataframe['TRIP_LPK'] = lit_per_km

    if 'COOLANT' in dataframe.columns:
        temps = dataframe['COOLANT'].tolist()
        dict_dataframe['COOLANT'] = temps

    if 'REVS' in dataframe.columns:
        engine_revs = dataframe['REVS'].tolist()
        dict_dataframe['REVS'] = engine_revs

    # Summary
    if 'TRIP_SPEED' in dataframe.columns:
        values['Velocidad media (en movimiento)'] = str(
            round(dataframe['TRIP_SPEED'].iloc[dataframe['TRIP_SPEED'].size - 1], 2)) + ' km/h'

    if 'TOTAL_TRIP' in dataframe.columns:
        values['Distancia'] = str(round(dataframe['TOTAL_TRIP'].iloc[0], 2)) + ' km'

    if 'TOTAL_TIME' in dataframe.columns:
        seconds = dataframe['TOTAL_TIME'].iloc[0]
        values['Duracion'] = str(datetime.timedelta(seconds=seconds))

    if 'TOTAL_FUEL_USED' in dataframe.columns:
        values['Combustible'] = str(round(dataframe['TOTAL_FUEL_USED'].iloc[0], 2)) + ' l'

    if 'TOTAL_STOP_COUNT' in dataframe.columns:
        values['Paradas totales'] = int(dataframe['TOTAL_STOP_COUNT'].iloc[0])

    if 'TOTAL_CAR_OFF' in dataframe.columns:
        values['Caladas'] = int(dataframe['TOTAL_CAR_OFF'].iloc[0])

    if 'CITY' in dataframe.columns:
        values['Ciudad'] = str(round(dataframe['CITY'].iloc[-1], 2)) + '%'

    if 'HGWY' in dataframe.columns:
        values['Autovía'] = str(round(dataframe['HGWY'].iloc[-1], 2)) + '%'

    if 'IDLE' in dataframe.columns:
        values['Idle'] = str(round(dataframe['IDLE'].iloc[-1], 2)) + '%'

    for key in list(dict_dataframe):
        if dict_dataframe[key].__len__() == 0:
            dict_dataframe.pop(key)

    # print(dict_dataframe)
    gjson_dict["features"] = feat_list

    data = json.dumps(gjson_dict, default=myconverter, sort_keys=True, indent=4, ensure_ascii=False)
    # print(data)

    addresses = session.track_set.all()
    address_list = []
    last_address = ''

    if addresses:
        address_list = print_track(session_id)

    # print(dict_dataframe)
    dict_df = pandas.DataFrame({key: pandas.Series(value) for key, value in dict_dataframe.items()}, dtype=float)
    # print(dict_df)
    # clean_dataset(dict_df)
    # print(dict_df)
    dataframe_describe = None

    if not dict_df.empty:
        dataframe_describe = dict_df.describe(include='all').round(2).to_html

    # print(values)

    # calcular el valor p del coeficiente de correlación entre puntos y asistencias
    # pearsonr(df[' puntos '], df[' asiste '])
    plt.figure(figsize=(16, 6))

    heatmap = sns.heatmap(dict_df.corr(), cmap="Blues", vmin=-1, vmax=1, annot=True)
    heatmap.set_title('Correlation Heatmap', fontdict={'fontsize': 12}, pad=12)
    heatmap_plot = get_base64(plt, 'tight')
    heatmap_plot = heatmap_plot.decode('ascii')

    # print(dict_df.corr())
    # print(dataframe)
    '''
    print(dataframe.drop(columns=[
        'GPS_SPD',
        'TRIP',
        'GPS_ACC',
        'TRIPTIME',
        'TRIPMSPEED',
        'TRIP_SPEED',
        'AV_CO2',
        'SPD_DIFF',
        'TRIP_LPK',
        'STOP_LESS_4_SEC',
        'STOP_LESS_6_SEC',
        'STOP_MORE_EQ_6_SEC',
        'TOTAL_STOP_COUNT',
        'TOTAL_TRIP',
        'TOTAL_TIME',
        'TOTAL_FUEL_USED',
        'TOTAL_CAR_OFF']).corr())
    '''
    # print('correlacion entre velocidad y contaminacion: ', dataframe['SPEED'].corr(dataframe['CO2']))

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
        'dataframe_describe': dataframe_describe,
        'times': times,
        'address_list': address_list,
        'start_coordinates': start_coordinates,
        'finish_coordinates': finish_coordinates,
        'heatmap_plot': heatmap_plot
    }

    return render(request, 'map.html', context=context)


def clean_dataset(df):
    assert isinstance(df, pd.DataFrame), "df needs to be a pd.DataFrame"
    df.dropna(inplace=True)
    indices_to_keep = ~df.isin([np.nan, np.inf, -np.inf]).any(1)
    return df[indices_to_keep].astype(np.float64)


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

    # logging.info(request)

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

    for key, value in request.GET.items():

        # TABLE SENSOR AND TABLE RECORD
        pid = ''

        if 'Name' in key or 'Unit' in key:

            if 'ff' in key:
                pid = key[-6:]

            if '0d' in key or '0c' in key or '05' in key or '83' in key:
                pid = key[-2:]

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

            if 'kff1006' in key:
                latitude = value
            if 'kff1005' in key:
                longitude = value

            elif 'kff1005' not in key and 'kff1006' not in key:
                if 'ff' in key:
                    pid = key[-6:]
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
                    logging.info('POSIBLE ERROR. key: ', key, ' value: ', value)
                    # value = None
                elif value:
                    try:
                        Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time, latitude=latitude,
                               longitude=longitude).save()
                    except Exception as e:
                        logging.info('Error al intentar guardar en la tabla records, motivo: ', e.args)
                        print('Error al intentar guardar en la tabla records, motivo: ', e.args)
                        print('Key: ', key, ' value: ', value)

    return HttpResponse('OK!')
