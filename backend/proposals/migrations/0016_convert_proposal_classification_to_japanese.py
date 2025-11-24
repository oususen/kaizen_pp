from django.db import migrations


def forward(apps, schema_editor):
    ImprovementProposal = apps.get_model("proposals", "ImprovementProposal")
    mapping = {
        "hold": "保留提案",
        "effort": "努力提案",
        "idea": "アイディア提案",
        "excellent": "優秀提案",
    }
    for old, new in mapping.items():
        ImprovementProposal.objects.filter(proposal_classification=old).update(proposal_classification=new)


def backward(apps, schema_editor):
    ImprovementProposal = apps.get_model("proposals", "ImprovementProposal")
    mapping = {
        "保留提案": "hold",
        "努力提案": "effort",
        "アイディア提案": "idea",
        "優秀提案": "excellent",
    }
    for old, new in mapping.items():
        ImprovementProposal.objects.filter(proposal_classification=old).update(proposal_classification=new)


class Migration(migrations.Migration):

    dependencies = [
        ("proposals", "0015_improvementproposal_proposal_classification"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
