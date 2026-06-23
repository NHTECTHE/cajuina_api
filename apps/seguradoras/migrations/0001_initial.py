from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Seguradora",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=255)),
                ("valor_licitacao", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("valor_execucao", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("taxa_comissao", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                (
                    "dia_vencimento",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(31),
                        ],
                    ),
                ),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Seguradora",
                "verbose_name_plural": "Seguradoras",
                "db_table": "seguradoras",
                "ordering": ["nome"],
            },
        ),
    ]
