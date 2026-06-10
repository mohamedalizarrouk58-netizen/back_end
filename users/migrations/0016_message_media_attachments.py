from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_fiche_facture_fee_breakdown'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='fichier',
            field=models.FileField(blank=True, null=True, upload_to='messages/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='message',
            name='type_message',
            field=models.CharField(
                choices=[('text', 'Text'), ('image', 'Image'), ('audio', 'Audio')],
                default='text',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='contenu',
            field=models.TextField(blank=True),
        ),
    ]
