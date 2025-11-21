# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0006_alter_department_options_department_display_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource', models.CharField(help_text='submit, proposals, etc.', max_length=50)),
                ('can_view', models.BooleanField(default=False)),
                ('can_edit', models.BooleanField(default=False)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='proposals.employee')),
            ],
            options={
                'unique_together': {('employee', 'resource')},
            },
        ),
    ]
