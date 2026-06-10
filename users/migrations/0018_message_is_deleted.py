from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_message_type_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
