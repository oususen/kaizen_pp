from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("proposals", "0027_proposalcontributor_reward_amount"),
    ]

    operations = [
        migrations.AlterField(
            model_name="proposal",
            name="reduction_hours",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True
            ),
        ),
        migrations.AlterField(
            model_name="improvementproposal",
            name="reduction_hours",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="削減時間(Hr/月)"
            ),
        ),
    ]
