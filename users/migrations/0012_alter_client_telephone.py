from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_user_image_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='telephone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
