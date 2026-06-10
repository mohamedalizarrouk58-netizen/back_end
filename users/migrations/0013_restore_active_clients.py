from django.db import migrations


def restore_soft_deleted_clients(apps, schema_editor):
    Client = apps.get_model('users', 'Client')
    Client.objects.filter(is_deleted=True).update(is_deleted=False)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_alter_client_telephone'),
    ]

    operations = [
        migrations.RunPython(restore_soft_deleted_clients, migrations.RunPython.noop),
    ]
