# Generated by Django 3.1.7 on 2021-03-10 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0004_auto_20210310_1507'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='id_app',
            field=models.CharField(max_length=255, null=True),
        ),
    ]