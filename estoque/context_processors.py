from .models import Notificacao

def notificacoes_pendentes(request):
    nao_lidas = Notificacao.objects.filter(lida=False).order_by('-data_criacao')
    return {
        'notificacoes_nao_lidas': nao_lidas,
        'quantidade_notificacoes': nao_lidas.count()
    }
