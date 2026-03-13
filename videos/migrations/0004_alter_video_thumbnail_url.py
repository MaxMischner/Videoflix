from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0003_video_conversion_tracking"),
    ]

    operations = [
        migrations.AlterField(
            model_name="video",
            name="thumbnail_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
