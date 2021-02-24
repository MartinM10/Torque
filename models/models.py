from django.db import models


# Create your models here.
class Dataset(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.BigIntegerField(null=True)
    name = models.TextField(null=True)
    rows_number = models.IntegerField(null=True, default=0)
    column_names = models.TextField(null=True)
    classification_applied = models.BooleanField(null=True, default=False)
    prediction_applied = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.name


class SVM(models.Model):
    id = models.AutoField(primary_key=True)
    two_first_components_plot = models.TextField(null=True)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class Prediction(models.Model):
    id = models.AutoField(primary_key=True)
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
    id = models.AutoField(primary_key=True)
    two_first_components_plot = models.TextField(null=True)
    explained_variance_ratio = models.TextField(null=True)
    components_and_features_plot = models.TextField(null=True)
    wcss_plot = models.TextField(null=True)
    acumulative_explained_variance_ratio_plot = models.TextField(null=True)
    cluster_list = models.TextField(null=True)
    more_important_features = models.TextField(null=True)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class Sensor(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.CharField(max_length=50)
    description = models.TextField(null=True)
    measure_unit = models.TextField(null=True)

    def __str__(self):
        return self.pid


class Log(models.Model):
    id = models.AutoField(primary_key=True)
    time = models.TimeField()
    dataset = models.ForeignKey(Dataset, null=True, on_delete=models.SET_NULL)


class Record(models.Model):
    id = models.AutoField(primary_key=True)
    value = models.FloatField()
    sensor = models.OneToOneField(Sensor, null=True, on_delete=models.SET_NULL)
    log = models.ForeignKey(Log, null=True, on_delete=models.SET_NULL)
