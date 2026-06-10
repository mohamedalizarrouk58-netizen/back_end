from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_facture_email_client'),
    ]

    operations = [
        migrations.AddField(
            model_name='fichereparation',
            name='frais_societe',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Frais de service de la société',
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name='fichereparation',
            name='prix_supplementaire',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Prix supplémentaire / charges additionnelles',
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name='facture',
            name='montant_frais_societe',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='facture',
            name='montant_main_oeuvre',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='facture',
            name='montant_pieces',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='facture',
            name='montant_supplementaire',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
