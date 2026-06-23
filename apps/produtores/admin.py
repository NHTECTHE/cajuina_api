from django.contrib import admin
from .models import Produtor


@admin.register(Produtor)
class ProdutorAdmin(admin.ModelAdmin):
    list_display = ["nome", "corretora", "email", "telefone", "recebimento", "percentual", "meta", "ativo"]
    search_fields = ["nome", "corretora", "email"]
    list_filter = ["ativo", "recebimento"]
