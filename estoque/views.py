from datetime import timedelta
from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import ProtectedError
from decimal import Decimal
from django.db import transaction

# Importação de Forms
from .forms import BaixaLoteForm, LoteEntradaForm, SaidaEstoqueForm

# Importação de Models
from .models import (
    Fruta,
    ItemPedido,
    Loja,
    LoteEntrada,
    MovimentacaoEstoque,
    Pedido,
    SaidaEstoque,
)


@login_required
def dashboard(request):
    hoje = timezone.now().date()
    limite_alerta = hoje + timedelta(days=5)

    # Indicadores gerais
    total_frutas = Fruta.objects.count()
    total_lojas = Loja.objects.count()

    # Controle de Lotes
    lotes_ativos = LoteEntrada.objects.filter(quantidade_atual__gt=0)
    lotes_criticos = lotes_ativos.filter(
        data_validade__gte=hoje, data_validade__lte=limite_alerta
    ).order_by('data_validade')
    lotes_vencidos = lotes_ativos.filter(data_validade__lt=hoje)

    # Histórico de saídas recentes
    ultimas_saidas = SaidaEstoque.objects.select_related(
        'lote__fruta', 'loja_destino'
    ).order_by('-data_saida')[:5]

    # Pedidos das lojas aguardando separação/atendimento
    pedidos_pendentes = Pedido.objects.filter(
        status__in=['PENDENTE', 'CONFIRMADO', 'RASCUNHO']
    ).order_by('-data_criacao')

    context = {
        'total_frutas': total_frutas,
        'total_lojas': total_lojas,
        'lotes_ativos_count': lotes_ativos.count(),
        'lotes_criticos': lotes_criticos,
        'lotes_vencidos': lotes_vencidos,
        'ultimas_saidas': ultimas_saidas,
        'pedidos_pendentes': pedidos_pendentes,
        'total_pendentes': pedidos_pendentes.count(),
    }

    return render(request, 'estoque/dashboard.html', context)


@login_required
def lote_criar(request):
    if request.method == 'POST':
        form = LoteEntradaForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            fruta = lote.fruta

            # 1. Copia a quantidade_inicial para a quantidade_atual se estiver em branco
            if not lote.quantidade_atual:
                lote.quantidade_atual = lote.quantidade_inicial

            # 2. Copia o local de armazenamento padrão da Fruta (se o usuário não selecionou)
            if not lote.local_armazenado and hasattr(fruta, 'local_armazenado'):
                lote.local_armazenado = fruta.local_armazenado

            # 3. Calcula a data de validade usando os dias de validade da Fruta
            # (Substitua 'dias_validade' pelo nome do campo no model Fruta, se for diferente)
            if not lote.data_validade and hasattr(fruta, 'dias_validade') and fruta.dias_validade:
                lote.data_validade = date.today() + timedelta(days=fruta.dias_validade)
            elif not lote.data_validade:
                lote.data_validade = date.today() + timedelta(days=7)  # Padrão de 7 dias caso a fruta não tenha o campo

            lote.save()
            messages.success(request, f'Lote de {fruta.nome} cadastrado com sucesso!')
            return redirect('dashboard')
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

    fruta_id = request.GET.get('fruta')
    loja_id = request.GET.get('loja')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

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
    # Verifica se o usuário pediu para exibir também os lotes zerados (?mostrar_zerados=true)
    mostrar_zerados = request.GET.get('mostrar_zerados') == 'true'

    # Busca base de lotes
    if mostrar_zerados:
        lotes_base = LoteEntrada.objects.all()
    else:
        lotes_base = LoteEntrada.objects.filter(quantidade_atual__gt=0) # Esconde lotes com quantidade 0

    # Aplica os filtros por local de armazenamento
    lotes_deposito = lotes_base.filter(
        local_armazenado__iexact='DEPOSITO'
    ).order_by('data_validade')

    lotes_camara_fria = lotes_base.filter(
        local_armazenado__iexact='CAMARA_FRIA'
    ).order_by('data_validade')

    lotes_outros = lotes_base.exclude(
        local_armazenado__iexact='DEPOSITO'
    ).exclude(
        local_armazenado__iexact='CAMARA_FRIA'
    ).order_by('data_validade')

    context = {
        'lotes_deposito': lotes_deposito,
        'lotes_camara_fria': lotes_camara_fria,
        'lotes_outros': lotes_outros,
        'mostrar_zerados': mostrar_zerados,
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


@login_required
def lote_excluir(request, pk):
    lote = get_object_or_404(LoteEntrada, pk=pk)

    if request.method == 'POST':
        try:
            codigo = lote.codigo_lote
            lote.delete()
            messages.success(request, f"Lote {codigo} excluído com sucesso!")
        except ProtectedError:
            messages.error(
                request,
                f"Não é possível excluir o lote {lote.codigo_lote} pois existem saídas de estoque vinculadas a ele."
            )
        return redirect('lotes_listar')  # Ou a URL para onde deseja redirecionar

    return render(request, 'estoque/lote_confirmar_exclusao.html', {'lote': lote})


@login_required
def lote_dar_baixa(request, pk):
    lote = get_object_or_404(LoteEntrada, pk=pk)

    if request.method == 'POST':
        form = BaixaLoteForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            qtd_baixa = movimentacao.quantidade

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
                lote.quantidade_atual -= qtd_baixa
                lote.save()

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


def catalogo_loja(request):
    produtos = Fruta.objects.filter(
        lotes__quantidade_atual__gt=0
    ).annotate(
        total_estoque=Sum('lotes__quantidade_atual')
    ).distinct().order_by('nome')

    carrinho_sessao = request.session.get('carrinho', {})
    carrinho_itens = []

    for fruta_id, qtd in carrinho_sessao.items():
        try:
            fruta = Fruta.objects.get(id=fruta_id)
            carrinho_itens.append({
                'produto': fruta,
                'quantidade': qtd,
            })
        except Fruta.DoesNotExist:
            continue

    lojas = Loja.objects.all()

    context = {
        'produtos': produtos,
        'carrinho_itens': carrinho_itens,
        'lojas': lojas,
    }
    return render(request, 'estoque/catalogo_loja.html', context)


def adicionar_ao_carrinho(request, produto_id):
    fruta = get_object_or_404(Fruta, id=produto_id)
    quantidade_solicitada = Decimal(request.POST.get('quantidade', 1))

    # Validação contra o estoque DISPONÍVEL (descontando reservas de outros pedidos)
    if quantidade_solicitada > fruta.estoque_disponivel:
        messages.error(
            request,
            f'Quantidade indisponível! Estoque livre: {fruta.estoque_disponivel} Kg/Unid. '
            f'(Estoque reservado em outros pedidos: {fruta.estoque_reservado} Kg/Unid.)'
        )
        return redirect('catalogo_loja')

    # Lógica para adicionar/atualizar o item no carrinho da sessão
    carrinho = request.session.get('carrinho', {})
    str_id = str(produto_id)

    # Exemplo simples de atualização no dicionário de sessão
    if str_id in carrinho:
        carrinho[str_id] += float(quantidade_solicitada)
    else:
        carrinho[str_id] = float(quantidade_solicitada)

    request.session['carrinho'] = carrinho
    messages.success(request, f'{fruta.nome} adicionado ao carrinho com sucesso!')

    # RETURN OBRIGATÓRIO NO FINAL DA VIEW
    return redirect('catalogo_loja')

def remover_do_carrinho(request, produto_id):
    carrinho = request.session.get('carrinho', {})
    str_id = str(produto_id)

    if str_id in carrinho:
        del carrinho[str_id]
        request.session['carrinho'] = carrinho
        messages.info(request, "Item removido do carrinho.")

    return redirect('catalogo_loja')


def finalizar_pedido(request):
    if request.method == 'POST':
        carrinho = request.session.get('carrinho', {})

        if not carrinho:
            messages.error(request, "Seu carrinho está vazio.")
            return redirect('catalogo_loja')

        nome_solicitante = request.POST.get('nome_solicitante')
        loja_id = request.POST.get('loja')

        if not nome_solicitante or not loja_id:
            messages.error(request, "Por favor, preencha o nome e selecione a loja.")
            return redirect('catalogo_loja')

        loja = get_object_or_404(Loja, id=loja_id)

        # CRIA O PEDIDO SALVANDO CORRETAMENTE O NOME E A LOJA NOS CAMPOS CERTOS
        pedido = Pedido.objects.create(
            cliente_nome=nome_solicitante,
            loja_solicitante=loja,  # <--- Vincula à loja correta
            usuario=request.user if request.user.is_authenticated else None,
            status='CONFIRMADO'
        )

        for fruta_id, qtd in carrinho.items():
            fruta = get_object_or_404(Fruta, id=fruta_id)

            ItemPedido.objects.create(
                pedido=pedido,
                fruta=fruta,
                quantidade=Decimal(str(qtd)),
                preco_unitario=Decimal('0.00')  # Ajuste se tiver o preço da fruta cadastrado
            )

        # Limpa o carrinho
        request.session['carrinho'] = {}
        messages.success(request, f"Pedido #{pedido.codigo_pedido} enviado com sucesso ao depósito!")

        return redirect('pedidos_historico')  # Redireciona para o histórico recém-criado

    return redirect('catalogo_loja')


@login_required
def separar_pedido(request, pedido_id):
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, id=pedido_id)

        if pedido.status not in ['PENDENTE', 'CONFIRMADO', 'RASCUNHO']:
            messages.warning(request, f"O pedido #{pedido.codigo_pedido} já foi processado anteriormente.")
            return redirect('dashboard')

        with transaction.atomic():
            for item in pedido.itens.all():
                qtd_necessaria = item.quantidade
                lotes = LoteEntrada.objects.filter(
                    fruta=item.fruta, quantidade_atual__gt=0
                ).order_by('data_validade')

                for lote in lotes:
                    if qtd_necessaria <= 0:
                        break

                    qtd_retirar = min(lote.quantidade_atual, qtd_necessaria)
                    lote.quantidade_atual -= qtd_retirar
                    lote.save()
                    qtd_necessaria -= qtd_retirar

            pedido.status = 'CONCLUIDO'
            pedido.save()

        messages.success(request, f"Pedido #{pedido.codigo_pedido} separado e concluído com sucesso!")

    return redirect('dashboard')


@login_required
def pedido_detalhe(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    itens = pedido.itens.select_related('fruta').all()

    context = {
        'pedido': pedido,
        'itens': itens,
    }
    return render(request, 'estoque/pedido_detalhe.html', context)


@transaction.atomic
def concluir_pedido(pedido):
    """
    Consome o estoque físico dos lotes ativos usando a regra PEPS/FIFO:
    Prioriza lotes com data de validade mais próxima e quantidade_atual > 0.
    """
    if pedido.status == 'CONCLUIDO':
        return

    for item in pedido.itens.all():
        quantidade_necessaria = item.quantidade

        # Busca os lotes ativos da fruta ordenados pela validade (mais antigo primeiro)
        lotes_disponiveis = LoteEntrada.objects.filter(
            fruta=item.fruta,
            quantidade_atual__gt=0
        ).order_by('data_validade', 'data_entrada')

        for lote in lotes_disponiveis:
            if quantidade_necessaria <= 0:
                break

            if lote.quantidade_atual >= quantidade_necessaria:
                # O lote cobre todo o restante da demanda
                lote.quantidade_atual -= quantidade_necessaria

                # Registra a saída real para rastreabilidade
                SaidaEstoque.objects.create(
                    lote=lote,
                    loja_destino=pedido.loja, # se houver relação com Loja
                    quantidade=quantidade_necessaria,
                    responsavel=pedido.usuario
                )

                lote.save()
                quantidade_necessaria = Decimal('0.00')
            else:
                # O lote cobre apenas parte da demanda (baixa parcial)
                quantidade_baixada = lote.quantidade_atual
                quantidade_necessaria -= quantidade_baixada
                lote.quantidade_atual = Decimal('0.00')

                SaidaEstoque.objects.create(
                    lote=lote,
                    loja_destino=pedido.loja,
                    quantidade=quantidade_baixada,
                    responsavel=pedido.usuario
                )

                lote.save()

    # Atualiza o status do pedido para CONCLUIDO
    pedido.status = 'CONCLUIDO'
    pedido.save()


@login_required
def pedidos_historico(request):
    pedidos = Pedido.objects.prefetch_related('itens__fruta').select_related('loja_solicitante', 'usuario').all()

    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    status_filtro = request.GET.get('status')
    loja_id = request.GET.get('loja')
    canal_filtro = request.GET.get('canal')

    # Filtro padrão: Pedidos de HOJE caso não seja informada nenhuma data
    if not data_inicio and not data_fim and request.GET.get('filtrar') != 'todos':
        hoje = timezone.now().date()
        pedidos = pedidos.filter(data_criacao__date=hoje)
        data_inicio = hoje.strftime('%Y-%m-%d')
        data_fim = hoje.strftime('%Y-%m-%d')
    else:
        if data_inicio:
            pedidos = pedidos.filter(data_criacao__date__gte=data_inicio)
        if data_fim:
            pedidos = pedidos.filter(data_criacao__date__lte=data_fim)

    if status_filtro:
        pedidos = pedidos.filter(status=status_filtro)

    if loja_id:
        pedidos = pedidos.filter(loja_solicitante_id=loja_id)

    if canal_filtro:
        pedidos = pedidos.filter(canal_venda=canal_filtro)

    # Métricas do período filtrado
    total_faturado = pedidos.filter(status='CONCLUIDO').aggregate(total=Sum('valor_total'))['total'] or 0
    total_pedidos = pedidos.count()
    pedidos_concluidos = pedidos.filter(status='CONCLUIDO').count()
    pedidos_pendentes = pedidos.filter(status='CONFIRMADO').count()

    lojas = Loja.objects.all()

    context = {
        'pedidos': pedidos,
        'lojas': lojas,
        'total_faturado': total_faturado,
        'total_pedidos': total_pedidos,
        'pedidos_concluidos': pedidos_concluidos,
        'pedidos_pendentes': pedidos_pendentes,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'status_filtro': status_filtro,
        'loja_id': loja_id,
        'canal_filtro': canal_filtro,
    }
    return render(request, 'estoque/pedidos_historico.html', context)
