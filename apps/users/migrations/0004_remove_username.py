from django.db import migrations, models

import apps.users.managers


def verificar_emails(apps_registry, schema_editor):
    """Aborta antes de qualquer DDL se algum usuário não puder logar depois.

    Sem username, quem estiver sem e-mail perde o acesso silenciosamente.
    Melhor falhar aqui, com os IDs na mão, do que descobrir em produção.
    """
    CustomUser = apps_registry.get_model("users", "CustomUser")

    sem_email = list(
        CustomUser.objects.filter(
            models.Q(email__isnull=True) | models.Q(email="")
        ).values_list("id", flat=True)
    )
    if sem_email:
        raise RuntimeError(
            "Migration abortada: os usuários abaixo estão sem e-mail e ficariam "
            f"sem acesso ao sistema. IDs: {sem_email}. "
            "Preencha o e-mail deles e rode a migration novamente."
        )

    duplicados = list(
        CustomUser.objects.values("email")
        .annotate(total=models.Count("id"))
        .filter(total__gt=1)
        .values_list("email", flat=True)
    )
    if duplicados:
        raise RuntimeError(
            f"Migration abortada: e-mails duplicados encontrados: {duplicados}. "
            "Deixe um usuário por e-mail e rode a migration novamente."
        )


def reverter_verificacao(apps_registry, schema_editor):
    """Nada a desfazer — a verificação não altera dados."""


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_customuser_cargo"),
    ]

    operations = [
        migrations.RunPython(verificar_emails, reverter_verificacao),
        migrations.RemoveField(
            model_name="customuser",
            name="username",
        ),
        migrations.AlterModelManagers(
            name="customuser",
            managers=[
                ("objects", apps.users.managers.CustomUserManager()),
            ],
        ),
    ]
