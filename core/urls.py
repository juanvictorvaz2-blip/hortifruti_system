from django.contrib import admin
from django.urls import path, include
from estoque import views  # Importa o módulo de views completo

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Rotas do django-allauth

    # Rotas do app Estoque
    path('', views.dashboard, name='dashboard'),
    path('lote/novo/', views.lote_criar, name='lote_criar'),
    path('saida/nova/', views.dinamica_saida, name='saida_criar'),
    path('historico/', views.historico_saidas, name='historico_saidas'),
    path('lotes/', views.lotes_listar, name='lotes_listar'),
    path('<int:pk>/editar/', views.lote_editar, name='lote_editar'),
    path('<int:pk>/excluir/', views.lote_excluir, name='lote_excluir'),
    path('<int:pk>/baixa/', views.lote_dar_baixa, name='lote_dar_baixa'),
]
