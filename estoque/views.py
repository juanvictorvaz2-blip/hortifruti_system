import urllib.parse
from datetime import date, timedelta
from decimal import Decimal
from .models import Notificacao
from django.urls import reverse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError  # Ajustado para importação correta
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# Importação de Forms
from .forms import (
    BaixaLoteForm,
    CompraCeasaForm,
    LoteEntradaForm,
    SaidaEstoqueForm,
)

# Importação de Models
from .models import (
    CompraCeasa,
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

            # 2. Copia o local de armazenamento padrão da Fruta
            if not lote.local_armazenado and hasattr(fruta, 'local_armazenado'):
                lote.local_armazenado = fruta.local_armazenado

            # 3. Calcula a data de validade usando os dias de validade da Fruta
            if not lote.data_validade and hasattr(fruta, 'dias_validade') and fruta.dias_validade:
                lote.data_validade = date.today() + timedelta(days=fruta.dias_validade)
            elif not lote.data_validade:
                lote.data_validade = date.today() + timedelta(days=7)  # Padrão de 7 dias

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
    mostrar_zerados = request.GET.get('mostrar_zerados') == 'true'

    if mostrar_zerados:
        lotes_base = LoteEntrada.objects.all()
    else:
        lotes_base = LoteEntrada.objects.filter(quantidade_atual__gt=0)

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
        return redirect('lotes_listar')

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


from django.db.models import Sum
from django.shortcuts import render
from .models import Fruta, Loja
def catalogo_loja(request):
    produtos_base = Fruta.objects.filter(
        lotes__quantidade_atual__gt=0
    ).annotate(
        total_estoque=Sum('lotes__quantidade_atual')
    ).distinct().order_by('nome')

    frutas = produtos_base.filter(categoria='FRUTA')
    legumes = produtos_base.filter(categoria='LEGUME')
    verduras = produtos_base.filter(categoria='VERDURA')
    outros = produtos_base.filter(categoria='OUTRO')

    # --- MONTAGEM DO TEXTO DO CATÁLOGO PARA O WHATSAPP ---
    texto_catalogo = "📋 *RELATÓRIO DE ESTOQUE ATUAL - DEPÓSITO*\n"
    texto_catalogo += "Segue a lista de produtos disponíveis para análise de compras:\n\n"

    categorias = [
        ("🍎 FRUTAS", frutas),
        ("🥕 LEGUMES", legumes),
        ("🥬 VERDURAS", verduras),
        ("📦 OUTROS / INSUMOS", outros),
    ]

    for titulo, queryset in categorias:
        if queryset.exists():
            texto_catalogo += f"*{titulo}*\n"
            for item in queryset:
                texto_catalogo += f"• {item.nome}: *{item.total_estoque} un*\n"
            texto_catalogo += "\n"

    texto_catalogo += "_Atualizado em tempo real pelo sistema._"

    # Substitua pelo número de WhatsApp do seu chefe (com DDI e DDD, ex: 5513999999999)
    # Se deixar o número vazio (''), o WhatsApp vai perguntar para quem deseja enviar.
    whatsapp_catalogo_url = f"https://api.whatsapp.com/send?phone=5545999512946&text={urllib.parse.quote(texto_catalogo)}"
    # -----------------------------------------------------

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
        'frutas': frutas,
        'legumes': legumes,
        'verduras': verduras,
        'outros': outros,
        'carrinho_itens': carrinho_itens,
        'lojas': lojas,
        'whatsapp_catalogo_url': whatsapp_catalogo_url, # Passando o link para o template
    }
    return render(request, 'estoque/catalogo_loja.html', context)

def adicionar_ao_carrinho(request, produto_id):
    fruta = get_object_or_404(Fruta, id=produto_id)
    quantidade_solicitada = Decimal(request.POST.get('quantidade', 1))

    if quantidade_solicitada > fruta.estoque_disponivel:
        messages.error(
            request,
            f'Quantidade indisponível! Estoque livre: {fruta.estoque_disponivel} Kg/Unid. '
            f'(Estoque reservado em outros pedidos: {fruta.estoque_reservado} Kg/Unid.)'
        )
        return redirect('catalogo_loja')

    carrinho = request.session.get('carrinho', {})
    str_id = str(produto_id)

    if str_id in carrinho:
        carrinho[str_id] += float(quantidade_solicitada)
    else:
        carrinho[str_id] = float(quantidade_solicitada)

    request.session['carrinho'] = carrinho
    messages.success(request, f'{fruta.nome} adicionado ao carrinho com sucesso!')

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

        pedido = Pedido.objects.create(
            cliente_nome=nome_solicitante,
            loja_solicitante=loja,
            usuario=request.user if request.user.is_authenticated else None,
            status='CONFIRMADO'
        )

        for fruta_id, qtd in carrinho.items():
            fruta = get_object_or_404(Fruta, id=fruta_id)

            ItemPedido.objects.create(
                pedido=pedido,
                fruta=fruta,
                quantidade=Decimal(str(qtd)),
                preco_unitario=Decimal('0.00')
            )

        # --- GERAÇÃO DA NOTIFICAÇÃO PARA O SININHO ---
        link_pedido = reverse('pedido_detalhe', args=[pedido.id])

        Notificacao.objects.create(
            mensagem=f"Novo pedido #{pedido.codigo_pedido} da Loja {loja.nome} por {nome_solicitante}.",
            link=link_pedido
        )
        # ---------------------------------------------

        request.session['carrinho'] = {}
        messages.success(request, f"Pedido #{pedido.codigo_pedido} enviado com sucesso ao depósito!")

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
                ).order_by('data_validade', 'data_entrada')

                for lote in lotes:
                    if qtd_necessaria <= 0:
                        break

                    qtd_retirar = min(lote.quantidade_atual, qtd_necessaria)
                    lote.quantidade_atual -= qtd_retirar
                    lote.save()

                    # Registra a saída no estoque para rastreabilidade
                    SaidaEstoque.objects.create(
                        lote=lote,
                        loja_destino=pedido.loja_solicitante,
                        quantidade=qtd_retirar,
                        responsavel=request.user if request.user.is_authenticated else None
                    )

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


@login_required
def pedidos_historico(request):
    pedidos = Pedido.objects.prefetch_related('itens__fruta').select_related('loja_solicitante', 'usuario').all()

    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    status_filtro = request.GET.get('status')
    loja_id = request.GET.get('loja')
    canal_filtro = request.GET.get('canal')

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


@login_required
def registrar_compra_ceasa(request):
    if request.method == 'POST':
        form = CompraCeasaForm(request.POST)
        if form.is_valid():
            compra = form.save(commit=False)

            nome_novo = form.cleaned_data.get('nome_nova_fruta')

            if nome_novo:
                nova_fruta, created = Fruta.objects.get_or_create(
                    nome=nome_novo,
                    defaults={
                        'dias_validade_padrao': 7,
                        'armazem_recomendado': 'DEPOSITO'
                    }
                )
                compra.fruta = nova_fruta

            if not compra.fruta:
                form.add_error('fruta', 'Selecione uma fruta existente ou digite o nome de uma nova variedade.')
                return render(request, 'estoque/registrar_compra.html', {'form': form})

            compra.responsavel_compra = request.user
            compra.status = 'PENDENTE'
            compra.save()
            form.save_m2m()

            return redirect('registrar_compra_ceasa')
    else:
        form = CompraCeasaForm()

    return render(request, 'estoque/registrar_compra.html', {'form': form})


@login_required
def listar_compras_conferencia(request):
    compras_pendentes = CompraCeasa.objects.filter(status='PENDENTE').order_by('-data_compra')
    return render(request, 'estoque/conferencia_compras.html', {'compras_pendentes': compras_pendentes})


@login_required
def realizar_conferencia_compra(request, pk):
    compra = get_object_or_404(CompraCeasa, pk=pk)

    if request.method == 'POST':
        quantidade_conferida = request.POST.get('quantidade_conferida')
        observacao = request.POST.get('observacao', '')

        if quantidade_conferida:
            compra.quantidade_comprada = float(quantidade_conferida)
            compra.status = 'CONFERIDO'
            compra.save()

            return redirect('listar_compras_conferencia')

    return render(request, 'estoque/detalhe_conferencia.html', {'compra': compra})

@login_required
def realizar_conferencia_compra(request, pk):
    compra = get_object_or_404(CompraCeasa, pk=pk)

    if request.method == 'POST':
        quantidade_conferida = request.POST.get('quantidade_conferida')
        observacao = request.POST.get('observacao', '')

        if quantidade_conferida:
            with transaction.atomic():
                # Atualiza os dados da compra CEASA
                compra.quantidade_comprada = Decimal(quantidade_conferida)
                compra.status = 'CONFERIDO'
                compra.save()

                dias_validade = getattr(compra.fruta, 'dias_validade_padrao', 7) or 7
                data_val = timezone.now().date() + timedelta(days=dias_validade)
                armazem = getattr(compra.fruta, 'armazem_recomendado', 'DEPOSITO') or 'DEPOSITO'

                # CRIAÇÃO DO LOTE COM OS PREÇOS E DADOS DA COMPRA
                lote = LoteEntrada.objects.create(
                    fruta=compra.fruta,
                    quantidade_inicial=compra.quantidade_comprada,
                    quantidade_atual=compra.quantidade_comprada,
                    preco_custo=compra.preco_custo,
                    preco_venda_caixa=compra.preco_venda_caixa,
                    preco_venda_banca=compra.preco_venda_banca,
                    data_validade=data_val,
                    local_armazenado=armazem,
                    codigo_lote=f"CEASA-{compra.id}-{timezone.now().strftime('%d%m%Y')}"
                )

                # Copia as lojas destinatárias da CompraCeasa para o LoteEntrada (ManyToManyField)
                if hasattr(compra, 'lojas_destinatarias') and compra.lojas_destinatarias.exists():
                    lote.lojas_destinatarias.set(compra.lojas_destinatarias.all())

            messages.success(request, f"Compra #{compra.id} conferida e Lote gerado no estoque com sucesso!")
            return redirect('listar_compras_conferencia')

    return render(request, 'estoque/detalhe_conferencia.html', {'compra': compra})
