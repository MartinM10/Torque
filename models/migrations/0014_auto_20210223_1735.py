# Generated by Django 3.1.7 on 2021-02-23 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0013_auto_20210223_1731'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='classification_applied',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='prediction_applied',
            field=models.BooleanField(default=False, null=True),
        ),
    ]
