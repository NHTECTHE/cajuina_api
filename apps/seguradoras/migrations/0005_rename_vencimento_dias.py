from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('seguradoras', '0004_seguradora_api_ou_name_seguradora_api_senha_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='seguradora',
            old_name='dia_vencimento',
            new_name='vencimento_dias',
        ),
        migrations.AlterField(
            model_name='seguradora',
            name='vencimento_dias',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(30),
                ],
            ),
        ),
    ]
