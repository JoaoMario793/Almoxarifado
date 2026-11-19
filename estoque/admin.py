from django.contrib import admin

from estoque.models import Material, Movimentacao, Pedido, PerfilUsuario, Setor


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla')
    search_fields = ('nome', 'sigla')


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_perfil', 'setor')
    list_filter = ('tipo_perfil', 'setor')
    search_fields = ('usuario__username', 'usuario__first_name', 'setor__nome')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'categoria', 'unidade_medida', 'saldo', 'status_disponibilidade')
    list_filter = ('categoria', 'unidade_medida')
    search_fields = ('codigo', 'nome')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'material', 'solicitante', 'setor', 'quantidade', 'status', 'criado_em')
    list_filter = ('status', 'setor')
    search_fields = ('material__nome', 'solicitante__username', 'justificativa')


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'material', 'quantidade', 'responsavel', 'criado_em')
    list_filter = ('tipo',)
    search_fields = ('material__nome', 'responsavel__username')