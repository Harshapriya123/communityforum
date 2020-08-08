# Generated by Django 2.2.14 on 2020-08-05 21:42

import dillo.models.mixins
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0028_communities'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostJob',
            fields=[
                (
                    'post_ptr',
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to='dillo.Post',
                    ),
                ),
                ('company', models.CharField(max_length=255)),
                ('city', models.CharField(blank=True, max_length=255)),
                ('province_state', models.CharField(blank=True, max_length=255)),
                ('country', models.CharField(max_length=255)),
                (
                    'contract_type',
                    models.CharField(
                        choices=[
                            ('full-time', 'Full-time'),
                            ('freelance', 'Freelance'),
                            ('internship', 'Internship'),
                        ],
                        default='full-time',
                        max_length=255,
                    ),
                ),
                ('is_remote_friendly', models.BooleanField(default=False)),
                ('description', models.TextField(null=True)),
                ('studio_website', models.URLField(blank=True, max_length=120)),
                ('url_apply', models.URLField(max_length=550)),
                ('software', models.CharField(blank=True, max_length=256)),
                ('level', models.CharField(blank=True, max_length=128)),
                ('starts_at', models.DateField(blank=True, null=True, verbose_name='starts at')),
                ('notes', models.TextField(null=True)),
                (
                    'image',
                    models.ImageField(
                        blank=True,
                        height_field='image_height',
                        upload_to=dillo.models.mixins.get_upload_to_hashed_path,
                        width_field='image_width',
                    ),
                ),
                ('image_height', models.PositiveIntegerField(null=True)),
                ('image_width', models.PositiveIntegerField(null=True)),
            ],
            options={'abstract': False,},
            bases=('dillo.post',),
        ),
        migrations.CreateModel(
            name='PostLink',
            fields=[
                (
                    'post_ptr',
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to='dillo.Post',
                    ),
                ),
            ],
            options={'abstract': False,},
            bases=('dillo.post',),
        ),
        migrations.AlterModelOptions(
            name='community', options={'verbose_name_plural': 'communities'},
        ),
    ]
