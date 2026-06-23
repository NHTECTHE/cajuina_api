from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Produtor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=255)),
                ("corretora", models.CharField(blank=True, default="", max_length=255)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("telefone", models.CharField(blank=True, default="", max_length=20)),
                (
                    "recebimento",
                    models.CharField(
                        blank=True,
                        choices=[("lucro", "Lucro"), ("comissao", "Comissão"), ("premio", "Prêmio")],
                        default="",
                        max_length=20,
                    ),
                ),
                ("percentual", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("meta", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Produtor",
                "verbose_name_plural": "Produtores",
                "db_table": "produtores",
                "ordering": ["nome"],
            },
        ),
    ]
