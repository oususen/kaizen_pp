from django.db import migrations, models


def populate_classification_points(apps, schema_editor):
    ImprovementProposal = apps.get_model("proposals", "ImprovementProposal")
    mapping = {
        "�ۗ����": 0,
        "�w�͒��": 1,
        "�A�C�f�B�A���": 4,
        "�D�G���": 8,
    }
    for classification, points in mapping.items():
        ImprovementProposal.objects.filter(
            proposal_classification=classification
        ).update(classification_points=points)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0020_add_serial_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="improvementproposal",
            name="classification_points",
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.RunPython(populate_classification_points, noop),
    ]
