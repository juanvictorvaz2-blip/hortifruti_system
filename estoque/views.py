from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import LoteEntrada, SaidaEstoque, Fruta, Loja
from .forms import LoteEntradaForm, SaidaEstoqueForm
from .forms import BaixaLoteForm, LoteEntradaForm
from .models import LoteEntrada


@login_required
def dashboard(request):
    hoje = timezone.now().date()
    limite_alerta = hoje + timedelta(days=5)  # Lotes que vencem nos próximos 5 dias

    # Consultas do banco de dados
    total_frutas = Fruta.objects.count()
    total_lojas = Loja.objects.count()

    # Lotes ativos (com estoque disponível)
    lotes_ativos = LoteEntrada.objects.filter(quantidade_atual__gt=0)

    # Lotes próximos do vencimento (vencem entre hoje e os próximos 5 dias)
    lotes_criticos = lotes_ativos.filter(
        data_validade__gte=hoje, data_validade__lte=limite_alerta
    ).order_by('data_validade')

    # Lotes já vencidos
    lotes_vencidos = lotes_ativos.filter(data_validade__lt=hoje)

    # Últimas 5 saídas de estoque registradas
    ultimas_saidas = SaidaEstoque.objects.select_related(
        'lote__fruta', 'loja_destino'
    ).order_by('-data_saida')[:5]

    context = {
        'total_frutas': total_frutas,
        'total_lojas': total_lojas,
        'lotes_ativos_count': lotes_ativos.count(),
        'lotes_criticos': lotes_criticos,
        'lotes_vencidos': lotes_vencidos,
        'ultimas_saidas': ultimas_saidas,
    }

    return render(request, 'estoque/dashboard.html', context)


@login_required
def lote_criar(request):
    if request.method == 'POST':
        form = LoteEntradaForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            # Preenche quantidade_atual se tiver ficado vazia
            if lote.quantidade_atual is None:
                lote.quantidade_atual = lote.quantidade_inicial
            lote.save()
            messages.success(request, 'Lote cadastrado com sucesso!')
            return redirect('lotes_listar')
        else:
            messages.error(
                request,
                'Erro ao salvar o lote. Verifique os campos abaixo.',
            )
    else:
        form = LoteEntradaForm()

    return render(request, 'estoque/lote_form.html', {'form': form})

@login_required
def dinamica_saida(request):
    if request.method == 'POST':
        form = SaidaEstoqueForm(request.POST)
        if form.is_valid():
            saida = form.save(commit=False)
            lote = saida.lote

            # Subtrai do saldo do lote selecionado
            if lote.quantidade_atual >= saida.quantidade:
                lote.quantidade_atual -= saida.quantidade
                lote.save()
                saida.save()
                messages.success(
                    request,
                    f'Saída de {saida.quantidade} enviada para {saida.loja_destino} com sucesso!',
                )
                return redirect('dashboard')
            else:
                form.add_error(
                    'quantidade',
                    f'Quantidade indisponível no lote. Saldo atual: {lote.quantidade_atual}',
                )
                messages.error(
                    request,
                    'A quantidade solicitada é maior que o saldo disponível no lote.',
                )
    else:
        form = SaidaEstoqueForm()
    return render(request, 'estoque/saida_form.html', {'form': form})


@login_required
def historico_saidas(request):
    saidas = SaidaEstoque.objects.select_related(
        'lote', 'lote__fruta', 'loja_destino'
    ).order_by('-data_saida')

    # Captura parâmetros via GET
    fruta_id = request.GET.get('fruta')
    loja_id = request.GET.get('loja')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Filtros condicionais
    if fruta_id:
        saidas = saidas.filter(lote__fruta_id=fruta_id)
    if loja_id:
        saidas = saidas.filter(loja_destino_id=loja_id)
    if data_inicio:
        saidas = saidas.filter(data_saida__date__gte=data_inicio)
    if data_fim:
        saidas = saidas.filter(data_saida__date__lte=data_fim)

    frutas = Fruta.objects.all()
    lojas = Loja.objects.all()

    context = {
        'saidas': saidas,
        'frutas': frutas,
        'lojas': lojas,
        'filtros': {
            'fruta': fruta_id,
            'loja': loja_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        },
    }
    return render(request, 'estoque/historico_saidas.html', context)
@login_required
def lotes_listar(request):
    # Busca lotes do Depósito (ignorando diferença entre maiúsculas/minúsculas)
    lotes_deposito = LoteEntrada.objects.filter(
        local_armazenado__iexact='DEPOSITO'
    ).order_by('data_validade')

    # Busca lotes da Câmara Fria (ignorando diferença entre maiúsculas/minúsculas)
    lotes_camara_fria = LoteEntrada.objects.filter(
        local_armazenado__iexact='CAMARA_FRIA'
    ).order_by('data_validade')

    # Pega qualquer lote que não se encaixou nos dois filtros acima (para depuração)
    lotes_outros = LoteEntrada.objects.exclude(
        local_armazenado__iexact='DEPOSITO'
    ).exclude(local_armazenado__iexact='CAMARA_FRIA')

    context = {
        'lotes_deposito': lotes_deposito,
        'lotes_camara_fria': lotes_camara_fria,
        'lotes_outros': lotes_outros,
    }
    return render(request, 'estoque/lotes_listar.html', context)
@login_required
def lote_editar(request, pk):
    lote = get_object_or_404(LoteEntrada, pk=pk)
    if request.method == 'POST':
        form = LoteEntradaForm(request.POST, instance=lote)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'Lote {lote.codigo_lote} atualizado com sucesso!'
            )
            return redirect('lotes_listar')
    else:
        form = LoteEntradaForm(instance=lote)

    return render(
        request, 'estoque/lote_form.html', {'form': form, 'lote': lote}
    )


# VIEW: Excluir Lote
@login_required
def lote_excluir(request, pk):
    lote = get_object_or_404(LoteEntrada, pk=pk)
    if request.method == 'POST':
        codigo = lote.codigo_lote
        lote.delete()
        messages.success(request, f'Lote {codigo} removido com sucesso!')
        return redirect('lotes_listar')

    return render(request, 'estoque/lote_confirm_delete.html', {'lote': lote})


# VIEW: Dar Baixa / Saída de Lote
@login_required
def lote_dar_baixa(request, pk):
    lote = get_object_or_404(LoteEntrada, pk=pk)

    if request.method == 'POST':
        form = BaixaLoteForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            qtd_baixa = movimentacao.quantidade

            # Valida se há quantidade suficiente em estoque
            if qtd_baixa <= 0:
                messages.error(
                    request, 'A quantidade de baixa deve ser maior que zero.'
                )
            elif qtd_baixa > lote.quantidade_atual:
                messages.error(
                    request,
                    f'Quantidade indisponível! Estoque atual é de {lote.quantidade_atual}.',
                )
            else:
                # Abate a quantidade atual do lote
                lote.quantidade_atual -= qtd_baixa
                lote.save()

                # Salva a movimentação
                movimentacao.lote = lote
                movimentacao.usuario = request.user
                movimentacao.save()

                messages.success(
                    request,
                    f'Baixa de {qtd_baixa} realizada com sucesso no lote {lote.codigo_lote}!',
                )
                return redirect('lotes_listar')
    else:
        form = BaixaLoteForm()

    return render(
        request, 'estoque/lote_dar_baixa.html', {'form': form, 'lote': lote}
        )
