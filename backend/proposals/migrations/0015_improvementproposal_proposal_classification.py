from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0014_improvementproposal_term_quarter"),
    ]

    operations = [
        migrations.AddField(
            model_name="improvementproposal",
            name="proposal_classification",
            field=models.CharField(
                blank=True,
                choices=[
                    ("hold", "保留提案"),
                    ("effort", "努力提案"),
                    ("idea", "アイディア提案"),
                    ("excellent", "優秀提案"),
                ],
                max_length=20,
                verbose_name="提案判定",
            ),
        ),
    ]
