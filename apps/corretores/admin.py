from django.contrib import admin
from .models import Corretor

@admin.register(Corretor)
class CorretorAdmin(admin.ModelAdmin):
    list_display = ["nome", "cpf_cnpj", "email", "telefone", "ativo"]
    search_fields = ["nome", "cpf_cnpj", "email"]
    list_filter = ["ativo"]
