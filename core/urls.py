from django.contrib import admin
from django.urls import path, include
from estoque import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Rotas do Sistema / Admin
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Habilita /accounts/login/

    # ==========================================
    # ÁREA PÚBLICA DO CLIENTE (PÁGINA INICIAL)
    # ==========================================
    path('', views.vitrine_cliente, name='vitrine_cliente'),
    path('vitrine/adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho_cliente'),
    path('vitrine/remover/<int:item_id>/', views.remover_do_carrinho_cliente, name='remover_do_carrinho_cliente'),
    path('vitrine/finalizar-whatsapp/', views.finalizar_pedido_whatsapp, name='finalizar_pedido_whatsapp'),

    # ==========================================
    # ÁREA INTERNA (FUNCIONÁRIOS / DEPÓSITO)
    # ==========================================
    path('deposito/dashboard/', views.dashboard, name='dashboard'),
    path('deposito/painel/', views.dashboard, name='dashboard_deposito'),

    # Lotes
    path('lote/novo/', views.lote_criar, name='lote_criar'),
    path('lotes/', views.lotes_listar, name='lotes_listar'),
    path('lote/<int:pk>/editar/', views.lote_editar, name='lote_editar'),
    path('lote/<int:pk>/excluir/', views.lote_excluir, name='lote_excluir'),
    path('lote/<int:pk>/baixa/', views.lote_dar_baixa, name='lote_dar_baixa'),

    # Saídas e Histórico
    path('saida/nova/', views.dinamica_saida, name='dinamica_saida'),
    path('historico/', views.historico_saidas, name='historico_saidas'),

    # Catálogo Interno de Lojas (Sistema de pedidos entre lojas protegido por staff)
    path('loja/', views.catalogo_loja, name='catalogo_loja'),
    # Nota: Se o seu views.py atual não usa mais o adicionar/remover/finalizar antigo,
    # mantemos apenas a rota principal 'loja/' para gerar o relatório/catálogo interno.

    # Detalhes e Separação de Pedidos
    path('pedido/<int:pedido_id>/', views.pedido_detalhe, name='pedido_detalhe'),
    path('deposito/separar/<int:pedido_id>/', views.separar_pedido, name='separar_pedido'),
    path('pedidos/historico/', views.pedidos_historico, name='pedidos_historico'),
    path('carrinho/adicionar/<int:fruta_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),

    # Compras CEASA
    path('compras/nova/', views.registrar_compra_ceasa, name='registrar_compra_ceasa'),
    path('compras/lista/', views.registrar_compra_ceasa, name='lista_compras_ceasa'),
    path('compras/conferencia/', views.listar_compras_conferencia, name='listar_compras_conferencia'),
    path('compras/conferencia/<int:pk>/', views.realizar_conferencia_compra, name='realizar_conferencia_compra'),

    # Notificações
    path('notificacoes/limpar/', views.marcar_todas_notificacoes_lidas, name='marcar_todas_lidas'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
