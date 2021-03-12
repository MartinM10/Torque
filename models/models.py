from django.db import models


# Create your models here.
class Dataset(models.Model):
    date = models.BigIntegerField(null=True)
    name = models.CharField(null=True, max_length=255)
    rows_number = models.IntegerField(null=True, default=0)
    column_names = models.TextField(null=True)
    classification_applied = models.BooleanField(null=True, default=False)
    prediction_applied = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.name


class SVM(models.Model):
    two_first_components_plot = models.TextField(null=True)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class Prediction(models.Model):
    learning_curve_plot = models.TextField(null=True)
    prediction_plot = models.TextField(null=True)
    time = models.IntegerField(null=True)
    rmse = models.FloatField(null=True)
    feature = models.TextField(null=True)
    epochs = models.IntegerField(null=True, default=0)
    prediction_features_type = models.TextField(null=True)
    principal_components_number = models.IntegerField(null=True, default=0)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class KMeans(models.Model):
    two_first_components_plot = models.TextField(null=True)
    explained_variance_ratio = models.TextField(null=True)
    components_and_features_plot = models.TextField(null=True)
    wcss_plot = models.TextField(null=True)
    acumulative_explained_variance_ratio_plot = models.TextField(null=True)
    cluster_list = models.TextField(null=True)
    more_important_features = models.TextField(null=True)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class Sensor(models.Model):
    pid = models.CharField(unique=True, max_length=255)
    user_full_name = models.CharField(null=True, max_length=255)
    user_short_name = models.CharField(null=True, max_length=255)
    user_unit = models.CharField(null=True, max_length=50)
    default_unit = models.CharField(null=True, max_length=50)

    def __str__(self):
        return self.pid


class Log(models.Model):
    session = models.BigIntegerField(null=True)
    id_app = models.CharField(null=True, max_length=255)
    time = models.DateTimeField(null=True, auto_now_add=True)
    dataset = models.ForeignKey(Dataset, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('id_app', 'session')


class Profile(models.Model):
    name = models.CharField(null=True, max_length=255)
    vehicle = models.CharField(null=True, max_length=255)
    weight = models.FloatField(null=True)
    fuel_type = models.CharField(null=True, max_length=50)
    fuel_cost = models.FloatField(null=True)


class Record(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    log = models.ForeignKey(Log, on_delete=models.CASCADE)
    value = models.FloatField()
    time = models.DateTimeField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)


class DataTorque(models.Model):
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    session = models.CharField(null=True, max_length=255)
    id_app = models.CharField(null=True, max_length=255)
    time = models.BigIntegerField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
