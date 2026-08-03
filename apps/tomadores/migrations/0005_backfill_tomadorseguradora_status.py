from decimal import Decimal

from django.db import migrations


def backfill_status(apps, schema_editor):
    TomadorSeguradora = apps.get_model('tomadores', 'TomadorSeguradora')
    for vinculo in TomadorSeguradora.objects.filter(status='sem_cadastro'):
        if vinculo.taxa and Decimal(vinculo.taxa) > 0:
            vinculo.status = 'cadastro_ok'
            vinculo.save(update_fields=['status'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tomadores', '0004_tomadorseguradora_status'),
    ]

    operations = [
        migrations.RunPython(backfill_status, noop),
    ]
