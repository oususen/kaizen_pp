# Generated manually - Change UserPermission from employee to user

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('proposals', '0007_userpermission'),
    ]

    operations = [
        # テーブルを削除して再作成
        migrations.DeleteModel(
            name='UserPermission',
        ),
        migrations.CreateModel(
            name='UserPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource', models.CharField(help_text='submit, proposals, etc.', max_length=50)),
                ('can_view', models.BooleanField(default=False)),
                ('can_edit', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'resource')},
            },
        ),
    ]
