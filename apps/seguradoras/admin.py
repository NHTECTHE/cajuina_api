from django.contrib import admin
from .models import Seguradora


@admin.register(Seguradora)
class SeguradoraAdmin(admin.ModelAdmin):
    list_display = ["nome", "taxa_comissao", "dia_vencimento", "ativo"]
    search_fields = ["nome"]
    list_filter = ["ativo"]
