# Generated by Django 2.2.2 on 2020-02-29 00:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0007_profile_setup_stages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='setup_stage',
            field=models.CharField(
                choices=[
                    ('avatar', 'Avatar'),
                    ('bio', 'Bio'),
                    ('links', 'links'),
                    ('tags', 'Tags'),
                ],
                default='avatar',
                max_length=10,
            ),
        ),
    ]
