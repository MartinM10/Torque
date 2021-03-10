from django.http import HttpResponse
from django.utils.datetime_safe import datetime
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets

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


def upload_data(request):
    # print(request.query_params)
    # print(request.GET)
    session_app = request.GET.get('session')
    id_app = request.GET.get('id')
    time_app = request.GET.get('time')

    # print("TIMESTAMP---------------------------------- ")
    # ts = int(time_app)
    # print(ts, '\n')
    # from django.utils.datetime_safe import datetime
    # print(datetime.utcfromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S' '.' '%f'))

    # TABLE LOG
    if session_app:
        log = Log.objects.filter(session=session_app, id_app=id_app)
        if not log:
            Log(session=session_app, id_app=id_app, time=None, dataset_id=None).save()

    for key, value in request.GET.items():
        # print(key, " -> ", value)

        # TABLE DATA_TORQUE
        DataTorque(key=key, value=value, session=session_app, id_app=id_app, time=time_app).save()

        # TABLE SENSOR
        if 'FullName' in key or 'ShortName' in key or 'userUnit' in key or \
                'defaultUnit' in key or 'kff' in key:

            pid = key[-4:]
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
                sensor_id = Sensor.objects.get(pid=pid).id
                log_id = Log.objects.filter(session=session_app).first().id
                timestamp = int(time_app)
                date_time = datetime.utcfromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S''.''%f')
                Record(sensor_id=sensor_id, log_id=log_id, value=value, time=date_time).save()

    return HttpResponse('Ok!')
