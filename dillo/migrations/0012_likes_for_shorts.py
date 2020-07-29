# Generated by Django 2.2.2 on 2020-03-04 00:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0011_shorts_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='likes',
            name='content_type',
            field=models.ForeignKey(
                limit_choices_to=models.Q(
                    models.Q(('app_label', 'dillo'), ('model', 'Post')),
                    models.Q(('app_label', 'dillo'), ('model', 'Comment')),
                    models.Q(('app_label', 'dillo'), ('models', 'Short')),
                    _connector='OR',
                ),
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.ContentType',
            ),
        ),
        migrations.AlterField(
            model_name='short',
            name='url',
            field=models.URLField(help_text='A YouTube or Vimeo link', max_length=120),
        ),
    ]
