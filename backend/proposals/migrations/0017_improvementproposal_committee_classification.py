from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0016_convert_proposal_classification_to_japanese"),
    ]

    operations = [
        migrations.AddField(
            model_name="improvementproposal",
            name="committee_classification",
            field=models.CharField(
                blank=True,
                choices=[
                    ("保留提案", "保留提案"),
                    ("努力提案", "努力提案"),
                    ("アイディア提案", "アイディア提案"),
                    ("優秀提案", "優秀提案"),
                ],
                max_length=20,
                verbose_name="改善委員判定",
            ),
        ),
    ]
