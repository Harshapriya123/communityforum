# Generated by Django 2.2.11 on 2020-06-08 18:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0025_jobs_add_properties'),
    ]

    operations = [
        migrations.AddField(
            model_name='event', name='is_online', field=models.BooleanField(default=False),
        ),
    ]
