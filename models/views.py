from django.http import HttpResponse
from django.utils.datetime_safe import datetime
from django.shortcuts import render
import os

# Create your views here.
from rest_framework import viewsets

from Torque.settings import DATA_URL, BASE_DIR
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


def viewMap(request):
    filename = 'data/torqueTrackLog.kml'
    data = (
        os.path.join(BASE_DIR, "data/torqueTrackLog.kml"),
    )
    print(data)

    context = {
        'data': data
    }
    return render(request, 'map.html', context={'data': data})


def upload_data(request):
    # print(request.query_params)
    # print(request.GET)
    session_app = request.GET.get('session')
    id_app = request.GET.get('id')
    time_app = request.GET.get('time')
    latitude = request.GET.get('kff1006')
    longitude = request.GET.get('kff1005')

    # print("TIMESTAMP---------------------------------- ")
    # ts = int(time_app)
    # print(ts, '\n')
    # from django.utils.datetime_safe import datetime
    # print(datetime.utcfromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S' '.' '%f'))

    # TABLE LOG
    if session_app:
        log, created = Log.objects.get_or_create(session=session_app, id_app=id_app)
        if created:
            print('-----------------------------LOG-----------------------')
            print(log)
            Log(session=session_app, id_app=id_app, time=None, dataset_id=None).save()

    for key, value in request.GET.items():
        # print(key, " -> ", value)

        # TABLE DATA_TORQUE
        DataTorque(key=key, value=value, session=session_app, id_app=id_app, time=time_app,
                   latitude=latitude, longitude=longitude).save()

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
                log_id = Log.objects.filter(session=session_app).first().id
                timestamp = int(time_app)
                date_time = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S''.''%f')
                Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time, latitude=latitude,
                       longitude=longitude).save()

    return HttpResponse('Ok!')
