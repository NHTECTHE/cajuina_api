from django.contrib import admin

from .models import Modalidade, ModalidadeSeguradora


class ModalidadeSeguradoraInline(admin.TabularInline):
    model = ModalidadeSeguradora
    extra = 1
    autocomplete_fields = ["seguradora"]


@admin.register(Modalidade)
class ModalidadeAdmin(admin.ModelAdmin):
    list_display = ["nome", "ativo"]
    search_fields = ["nome"]
    list_filter = ["ativo"]
    inlines = [ModalidadeSeguradoraInline]


@admin.register(ModalidadeSeguradora)
class ModalidadeSeguradoraAdmin(admin.ModelAdmin):
    list_display = ["modalidade", "seguradora", "codigo_seguradora", "ativo"]
    search_fields = ["modalidade__nome", "seguradora__nome", "codigo_seguradora"]
    list_filter = ["ativo", "seguradora"]
    autocomplete_fields = ["modalidade", "seguradora"]
