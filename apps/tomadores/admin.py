from django.contrib import admin
from .models import Tomador, ContatoAdicional, Socio


class ContatoAdicionalInline(admin.TabularInline):
    model = ContatoAdicional
    extra = 0


class SocioInline(admin.TabularInline):
    model = Socio
    extra = 0


@admin.register(Tomador)
class TomadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "cidade", "uf", "produtor", "criado_em")
    search_fields = ("nome", "cnpj", "contato")
    list_filter = ("uf", "produtor", "ativar_cotacao")
    inlines = [ContatoAdicionalInline, SocioInline]
