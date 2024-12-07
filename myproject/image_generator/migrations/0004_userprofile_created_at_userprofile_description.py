# Generated by Django 5.1.3 on 2024-12-07 08:11

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("image_generator", "0003_usercustommodel"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="description",
            field=models.TextField(blank=True, max_length=255, null=True),
        ),
    ]