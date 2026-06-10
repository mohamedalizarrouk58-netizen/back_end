from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_message_media_attachments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='type_message',
            field=models.CharField(
                choices=[
                    ('text', 'Text'),
                    ('image', 'Image'),
                    ('audio', 'Audio'),
                    ('file', 'File'),
                ],
                default='text',
                max_length=10,
            ),
        ),
    ]
