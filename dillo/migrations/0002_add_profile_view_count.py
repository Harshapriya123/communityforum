# Generated by Django 2.2.2 on 2020-01-24 00:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile', name='views_count', field=models.PositiveIntegerField(default=0),
        ),
    ]