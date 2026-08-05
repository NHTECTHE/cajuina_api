import importlib.util
from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent / "migrations" / "0004_remove_username.py"
)


def carregar_migration():
    """Importa a migration pelo caminho — o nome do módulo começa com dígito."""
    spec = importlib.util.spec_from_file_location("migration_0004", MIGRATION_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class FakeQuerySet(list):
    """Imita o encadeamento de queryset que a guarda usa."""

    def filter(self, *args, **kwargs):
        return self

    def annotate(self, **kwargs):
        return self

    def values(self, *args, **kwargs):
        return self

    def values_list(self, *args, **kwargs):
        return self


def fake_apps(sem_email, duplicados):
    class FakeManager:
        def filter(self, *args, **kwargs):
            return FakeQuerySet(sem_email)

        def values(self, *args, **kwargs):
            return FakeQuerySet(duplicados)

    class FakeModel:
        objects = FakeManager()

    class FakeApps:
        def get_model(self, app_label, model_name):
            return FakeModel

    return FakeApps()


def test_guarda_aborta_listando_ids_sem_email():
    migration = carregar_migration()

    with pytest.raises(RuntimeError, match=r"IDs: \[7, 12\]"):
        migration.verificar_emails(fake_apps(sem_email=[7, 12], duplicados=[]), None)


def test_guarda_aborta_listando_emails_duplicados():
    migration = carregar_migration()

    with pytest.raises(RuntimeError, match="ana@empresa.com"):
        migration.verificar_emails(
            fake_apps(sem_email=[], duplicados=["ana@empresa.com"]), None
        )


def test_guarda_passa_com_base_saudavel():
    migration = carregar_migration()

    migration.verificar_emails(fake_apps(sem_email=[], duplicados=[]), None)
