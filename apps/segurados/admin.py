from django.contrib import admin
from .models import Segurado


@admin.register(Segurado)
class SegуradoAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "cidade", "estado"]
    search_fields = ["nome", "cnpj", "cidade"]
