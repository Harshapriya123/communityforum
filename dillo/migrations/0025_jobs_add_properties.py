# Generated by Django 2.2.11 on 2020-04-28 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0024_job_updates'),
    ]

    operations = [
        migrations.AddField(
            model_name='job', name='level', field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='job', name='software', field=models.CharField(blank=True, max_length=256),
        ),
    ]
