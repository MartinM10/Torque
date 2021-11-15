# Generated by Django 3.1.7 on 2021-11-11 13:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0009_auto_20211008_1104'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.BigIntegerField(auto_created=True, null=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('rows_number', models.IntegerField(default=0, null=True)),
                ('column_names', models.TextField(null=True)),
                ('classification_applied', models.BooleanField(default=False, null=True)),
                ('prediction_applied', models.BooleanField(default=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SVM',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('two_first_components_plot', models.TextField(null=True)),
                ('dataset', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='Prediction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('learning_curve_plot', models.TextField(null=True)),
                ('prediction_plot', models.TextField(null=True)),
                ('time', models.DateTimeField(null=True)),
                ('rmse', models.FloatField(null=True)),
                ('feature', models.TextField(null=True)),
                ('epochs', models.IntegerField(default=0, null=True)),
                ('prediction_features_type', models.TextField(null=True)),
                ('principal_components_number', models.IntegerField(default=0, null=True)),
                ('dataset', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='KMeans',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('two_first_components_plot', models.TextField(null=True)),
                ('explained_variance_ratio', models.TextField(null=True)),
                ('components_and_features_plot', models.TextField(null=True)),
                ('wcss_plot', models.TextField(null=True)),
                ('acumulative_explained_variance_ratio_plot', models.TextField(null=True)),
                ('cluster_list', models.TextField(null=True)),
                ('more_important_features', models.TextField(null=True)),
                ('dataset', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.dataset')),
            ],
        ),
        migrations.AddField(
            model_name='log',
            name='dataset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='models.dataset'),
        ),
    ]