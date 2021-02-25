from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from django.template.backends import django
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from rest_framework import viewsets
from rest_framework.decorators import api_view

from models.models import Log, Record, Dataset, Sensor, Prediction, KMeans, SVM, DataTorque
from models.serializers import LogSerializer, RecordSerializer, DatasetSerializer, SensorSerializer, \
    PredictionSerializer, KMeansSerializer, SVMSerializer


class LogViewSet(viewsets.ModelViewSet):
    serializer_class = LogSerializer
    queryset = Log.objects.all()


class RecordViewSet(viewsets.ModelViewSet):
    serializer_class = RecordSerializer
    queryset = Record.objects.all()


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
    session = request.GET.get('session')
    for key, value in request.GET.items():
        print(key, " -> ", value)
        DataTorque(key=key, value=value, session=session).save()

        '''
        if key != 'time' and key != 'id' and key != 'v' and key != 'session':
            record = Record(value=value, sensor_id=key, log_id=None)
            record.save()
        '''

    return HttpResponse('Ok!')
