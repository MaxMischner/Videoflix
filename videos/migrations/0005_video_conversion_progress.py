from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("videos", "0004_alter_video_thumbnail_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="video",
            name="conversion_progress",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
