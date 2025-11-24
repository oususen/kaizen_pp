from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0013_userprofile_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="improvementproposal",
            name="term",
            field=models.IntegerField(blank=True, null=True, verbose_name="期"),
        ),
        migrations.AddField(
            model_name="improvementproposal",
            name="quarter",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="四半期"),
        ),
    ]
