# Generated by Django 3.1.7 on 2021-02-24 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0023_auto_20210224_0844'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sensor',
            name='pid',
            field=models.CharField(max_length=50),
        ),
    ]
