from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_user_two_factor_enabled_otpcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='image_data',
            field=models.TextField(blank=True, null=True),
        ),
    ]
