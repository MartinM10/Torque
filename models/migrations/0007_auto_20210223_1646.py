# Generated by Django 3.1.7 on 2021-02-23 16:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0006_auto_20210223_1632'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='log',
            name='record_id',
        ),
        migrations.AddField(
            model_name='record',
            name='log_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.log'),
        ),
        migrations.AlterField(
            model_name='log',
            name='dataset_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.dataset'),
        ),
        migrations.AlterField(
            model_name='record',
            name='sensor_id',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.sensor'),
        ),
    ]
