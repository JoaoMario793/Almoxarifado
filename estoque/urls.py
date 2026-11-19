from django.urls import path

from estoque import views

app_name = 'estoque'

urlpatterns = [
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('materiais/novo/', views.material_criar_view, name='material_criar'),
    path('materiais/<int:pk>/editar/', views.material_editar_view, name='material_editar'),
    path('entradas/', views.entrada_estoque_view, name='entrada_estoque'),
    path('solicitantes/', views.solicitantes_gerir_view, name='solicitantes'),
    path('pedidos/novo/', views.pedido_criar_view, name='pedido_criar'),
    path('pedidos/meus/', views.meus_pedidos_view, name='meus_pedidos'),
    path('pedidos/gerencia/', views.pedidos_gerencia_view, name='pedidos_gerencia'),
    path('pedidos/<int:pk>/decidir/', views.pedido_decidir_view, name='pedido_decidir'),
]