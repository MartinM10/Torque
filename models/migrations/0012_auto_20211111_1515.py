# Generated by Django 3.1.7 on 2021-11-11 15:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0011_auto_20211111_1450'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='log',
            name='dataset',
        ),
        migrations.AddField(
            model_name='dataset',
            name='log',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='models.log'),
        ),
        migrations.AddField(
            model_name='sensor',
            name='logs',
            field=models.ManyToManyField(through='models.Record', to='models.Log'),
        ),
    ]
