from django.contrib import admin

from .models import (
    ContatoAdicional,
    Socio,
    Tomador,
    TomadorArquivo,
    TomadorSeguradora,
)


class ContatoAdicionalInline(admin.TabularInline):
    model = ContatoAdicional
    extra = 0


class SocioInline(admin.TabularInline):
    model = Socio
    extra = 0


class TomadorArquivoInline(admin.TabularInline):
    model = TomadorArquivo
    extra = 0
    readonly_fields = ("nome_original", "tamanho", "criado_em")


class TomadorSeguradoraInline(admin.TabularInline):
    model = TomadorSeguradora
    extra = 0
    fields = ("seguradora", "taxa", "premio_minimo", "dias_vencimento")


@admin.register(Tomador)
class TomadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "cidade", "uf", "produtor", "criado_em")
    search_fields = ("nome", "cnpj", "contato")
    list_filter = ("uf", "produtor", "ativar_cotacao")
    inlines = [
        ContatoAdicionalInline,
        SocioInline,
        TomadorSeguradoraInline,
        TomadorArquivoInline,
    ]
