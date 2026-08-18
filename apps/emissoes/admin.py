from django.contrib import admin

from .models import EmissaoSeguradora


@admin.register(EmissaoSeguradora)
class EmissaoSeguradoraAdmin(admin.ModelAdmin):
    """Só leitura: quem muda estado aqui é o service, com lock e validação."""

    list_display = [
        "id",
        "cotacao",
        "seguradora",
        "etapa",
        "ambiente",
        "external_id",
        "premio_total",
        "atualizado_em",
    ]
    list_filter = ["etapa", "ambiente", "integracao", "seguradora"]
    search_fields = ["external_id", "document_number", "cotacao__id"]
    readonly_fields = [f.name for f in EmissaoSeguradora._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
