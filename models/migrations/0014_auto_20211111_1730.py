# Generated by Django 3.1.7 on 2021-11-11 17:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0013_auto_20211111_1527'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='log',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='models.log'),
        ),
    ]
