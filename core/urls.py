from django.contrib import admin
from django.urls import path, include
from estoque import views

urlpatterns = [
    # Rotas do Sistema / Admin
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Habilita /accounts/login/

    # Dashboard Principal
    path('', views.dashboard, name='dashboard'),
    path('deposito/dashboard/', views.dashboard, name='dashboard_deposito'),

    # Lotes
    path('lote/novo/', views.lote_criar, name='lote_criar'),
    path('lotes/', views.lotes_listar, name='lotes_listar'),
    path('lote/<int:pk>/editar/', views.lote_editar, name='lote_editar'),
    path('lote/<int:pk>/excluir/', views.lote_excluir, name='lote_excluir'),
    path('lote/<int:pk>/baixa/', views.lote_dar_baixa, name='lote_dar_baixa'),

    # Saídas e Histórico
    path('saida/nova/', views.dinamica_saida, name='dinamica_saida'),
    path('historico/', views.historico_saidas, name='historico_saidas'),

    # Loja e Pedidos
    path('loja/', views.catalogo_loja, name='catalogo_loja'),
    path('loja/adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('loja/remover/<int:produto_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('loja/finalizar/', views.finalizar_pedido, name='finalizar_pedido'),

    # Detalhes e Separação de Pedidos
    path('pedido/<int:pedido_id>/', views.pedido_detalhe, name='pedido_detalhe'),
    path('deposito/separar/<int:pedido_id>/', views.separar_pedido, name='separar_pedido'),
]
