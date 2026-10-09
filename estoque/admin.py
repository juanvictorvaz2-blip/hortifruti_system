from django.contrib import admin
from .models import Fruta, LoteEntrada, CompraCeasa, Loja, SaidaEstoque, Pedido

@admin.register(Fruta)
class FrutaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'preco_banca', 'preco_atacado', 'foto', 'dias_validade_padrao')
    list_editable = ('preco_banca', 'preco_atacado', 'foto', 'dias_validade_padrao')
    search_fields = ('nome', 'categoria')
    list_filter = ('categoria',)

@admin.register(Loja)
class LojaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'endereco')
    search_fields = ('nome',)

@admin.register(LoteEntrada)
class LoteEntradaAdmin(admin.ModelAdmin):
    list_display = ('codigo_lote', 'fruta', 'quantidade_atual', 'data_validade', 'local_armazenado')
    list_filter = ('local_armazenado', 'data_validade', 'fruta')
    search_fields = ('codigo_lote', 'fruta__nome')

@admin.register(SaidaEstoque)
class SaidaEstoqueAdmin(admin.ModelAdmin):
    list_display = ('lote', 'loja_destino', 'quantidade', 'data_saida', 'responsavel')
    list_filter = ('loja_destino', 'data_saida')
