from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_restore_active_clients'),
    ]

    operations = [
        migrations.AddField(
            model_name='facture',
            name='email_client_envoye',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='facture',
            name='date_email_client',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
