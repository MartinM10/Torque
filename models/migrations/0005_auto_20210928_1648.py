# Generated by Django 3.1.7 on 2021-09-28 16:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0004_auto_20210729_1511'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DataTorque',
        ),
        migrations.RemoveField(
            model_name='kmeans',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='prediction',
            name='dataset',
        ),
        migrations.DeleteModel(
            name='Profile',
        ),
        migrations.RemoveField(
            model_name='svm',
            name='dataset',
        ),
        migrations.RemoveField(
            model_name='log',
            name='dataset',
        ),
        migrations.DeleteModel(
            name='Dataset',
        ),
        migrations.DeleteModel(
            name='KMeans',
        ),
        migrations.DeleteModel(
            name='Prediction',
        ),
        migrations.DeleteModel(
            name='SVM',
        ),
    ]
