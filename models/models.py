from django.db import models


# Create your models here.
class Log(models.Model):
    session = models.DateTimeField(null=True)
    email = models.CharField(null=True, max_length=255)
    id_app = models.CharField(null=True, max_length=255)
    type = models.IntegerField(null=True, blank=True)

    # la session ya trae el tiempo en unix timestamp
    # time = models.DateTimeField(null=True, auto_now_add=True)
    # dataset = models.ForeignKey(Dataset, null=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('email', 'session')


class Summary(models.Model):
    co2_mean = models.FloatField(null=True)
    speed_moving_mean = models.FloatField(null=True)
    distance = models.FloatField(null=True)
    duration = models.FloatField(null=True)
    total_fuel_used = models.FloatField(null=True)
    total_count_stop = models.FloatField(null=True)
    total_car_off = models.FloatField(null=True)
    city = models.FloatField(null=True)
    hgwy = models.FloatField(null=True)
    idle = models.FloatField(null=True)
    log = models.OneToOneField(Log, null=True, blank=True, on_delete=models.SET_NULL)


class Sensor(models.Model):
    pid = models.CharField(unique=True, max_length=255)
    user_full_name = models.CharField(null=True, max_length=255)
    user_short_name = models.CharField(null=True, max_length=255)
    ai4drive_name = models.CharField(null=True, max_length=255)
    user_unit = models.CharField(null=True, max_length=50)
    default_unit = models.CharField(null=True, max_length=50)
    logs = models.ManyToManyField(Log, through='Record')

    def __str__(self):
        return self.user_full_name


class Record(models.Model):
    log = models.ForeignKey(Log, null=True, on_delete=models.CASCADE)
    sensor = models.ForeignKey(Sensor, null=True, on_delete=models.CASCADE)
    value = models.CharField(null=True, max_length=255)
    time = models.DateTimeField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)


class Dataset(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(null=True, max_length=255)
    rows_number = models.IntegerField(null=True, default=0)
    column_names = models.TextField(null=True)
    classification_applied = models.BooleanField(null=True, default=False)
    prediction_applied = models.BooleanField(null=True, default=False)
    log = models.ForeignKey(Log, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class SVM(models.Model):
    two_first_components_plot = models.TextField(null=True)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class Prediction(models.Model):
    learning_curve_plot = models.TextField(null=True)
    prediction_plot = models.TextField(null=True)
    time = models.DateTimeField(null=True)
    rmse = models.FloatField(null=True)
    feature = models.TextField(null=True)
    epochs = models.IntegerField(null=True, default=0)
    prediction_features_type = models.TextField(null=True)
    principal_components_number = models.IntegerField(null=True, default=0)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class KMeans(models.Model):
    # Time series
    distance_plot = models.TextField(null=True)
    trip_moving_speed_plot = models.TextField(null=True)
    trip_speed_plot = models.TextField(null=True)
    fuel_used_plot = models.TextField(null=True)
    co2_plot = models.TextField(null=True)
    average_co2_plot = models.TextField(null=True)
    trip_lpk_plot = models.TextField(null=True)
    coolant_plot = models.TextField(null=True)
    instant_speed_plot = models.TextField(null=True)
    revs_plot = models.TextField(null=True)
    litres_per_km_plot = models.TextField(null=True)
    stopped_plot = models.TextField(null=True)
    moving_plot = models.TextField(null=True)
    city_plot = models.TextField(null=True)
    highway_plot = models.TextField(null=True)
    idle_plot = models.TextField(null=True)
    #
    two_first_components_plot = models.TextField(null=True)
    explained_variance_ratio = models.TextField(null=True)
    components_and_features_plot = models.TextField(null=True)
    wcss_plot = models.TextField(null=True)
    cumulative_explained_variance_ratio_plot = models.TextField(null=True)
    cluster_list = models.TextField(null=True)
    more_important_features = models.TextField(null=True)
    dataset = models.OneToOneField(Dataset, null=True, blank=True, on_delete=models.SET_NULL)


class Track(models.Model):
    address = models.CharField(null=True, max_length=255, unique=True)
    logs = models.ManyToManyField(Log, through='TrackLog')


class TrackLog(models.Model):
    log = models.ForeignKey(Log, null=True, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, null=True, on_delete=models.CASCADE)
    time = models.DateTimeField(null=True)


'''
class Profile(models.Model):
    name = models.CharField(null=True, max_length=255)
    vehicle = models.CharField(null=True, max_length=255)
    weight = models.FloatField(null=True)
    fuel_type = models.CharField(null=True, max_length=50)
    fuel_cost = models.FloatField(null=True)
'''

'''
class DataTorque(models.Model):
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    session = models.CharField(null=True, max_length=255)
    email = models.CharField(null=True, max_length=255)
    id_app = models.CharField(null=True, max_length=255)
    time = models.BigIntegerField(null=True)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
'''
