# Generated by Django 5.1.7 on 2025-03-28 13:35

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_apiusage_conversation_message'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={},
        ),
        migrations.RemoveField(
            model_name='comment',
            name='is_edited',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='updated_at',
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['created_at'], name='core_commen_created_97080c_idx'),
        ),
        migrations.AddConstraint(
            model_name='comment',
            constraint=models.UniqueConstraint(condition=models.Q(('parent__isnull', True)), fields=('prompt', 'author', 'content'), name='unique_comment_per_author'),
        ),
        migrations.AddConstraint(
            model_name='comment',
            constraint=models.UniqueConstraint(condition=models.Q(('parent__isnull', False)), fields=('parent', 'author', 'content'), name='unique_reply_per_author'),
        ),
    ]
