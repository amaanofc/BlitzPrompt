# Generated by Django 5.1.7 on 2025-03-27 00:31

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_prompt_rating'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='prompt',
            old_name='is_published',
            new_name='published',
        ),
        migrations.AddField(
            model_name='prompt',
            name='is_favorited',
            field=models.ManyToManyField(blank=True, related_name='favorites', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='prompt',
            name='usage_count',
            field=models.IntegerField(default=0),
        ),
    ]
