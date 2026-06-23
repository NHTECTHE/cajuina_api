import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corretores", "0001_initial"),
        ("produtores", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="produtor",
            name="corretora",
        ),
        migrations.AddField(
            model_name="produtor",
            name="corretora",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="produtores",
                to="corretores.corretor",
            ),
        ),
    ]
