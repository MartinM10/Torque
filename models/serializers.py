from rest_framework import serializers

from models.models import Log, Dataset, Sensor, Record, KMeans, Prediction, SVM


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id', 'time', 'dataset']


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ['id', 'date', 'name', 'rows_number', 'column_names', 'classification_applied', 'prediction_applied']


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['id', 'pid', 'description', 'measure_unit']


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = ['id', 'value', 'sensor', 'log']


class KMeansSerializer(serializers.ModelSerializer):
    class Meta:
        model = KMeans
        fields = ['id', 'two_first_components_plot', 'explained_variance_ratio',
                  'components_and_features_plot', 'wcss_plot', 'acumulative_explained_variance_ratio_plot',
                  'cluster_list', 'more_important_features', 'dataset']


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = ['id', 'learning_curve_plot', 'prediction_plot', 'time',
                  'rmse', 'feature', 'epochs', 'prediction_features_type',
                  'principal_components_number', 'dataset']


class SVMSerializer(serializers.ModelSerializer):
    class Meta:
        model = SVM
        fields = ['id', 'two_first_components_plot', 'dataset']
