from rest_framework import serializers

from models.models import Log, Sensor, Record


class LogSerializer(serializers.HyperlinkedModelSerializer):
    # logs = serializers.HyperlinkedIdentityField(many=True, read_only=True, view_name='record-detail')

    class Meta:
        model = Log
        # fields = '__all__'
        fields = ['id', 'session', 'email', 'id_app'] # , 'logs']
        ordering = ['id']


class SensorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Sensor
        fields = '__all__'
        # fields = ['id', 'pid', 'description', 'measure_unit']
        ordering = ['id']


class RecordSerializer(serializers.HyperlinkedModelSerializer):
    # log = LogSerializer(read_only=True)
    # logId = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Log.objects.all(), source='log')
    # sensors = SensorSerializer(many=True, read_only=True, source='sensor_set')

    class Meta:
        model = Record
        fields = '__all__'
        # fields = ['id', 'sensor', 'log', 'value', 'time', 'latitude', 'longitude']
        ordering = ['id']
