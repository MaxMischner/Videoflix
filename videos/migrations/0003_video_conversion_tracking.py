from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0002_mediafile"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="conversion_status",
            field=models.CharField(default="not_requested", max_length=32),
        ),
        migrations.AddField(
            model_name="video",
            name="conversion_updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="video",
            name="last_conversion_job_id",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
