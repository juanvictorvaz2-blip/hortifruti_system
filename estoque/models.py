import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone


# Declare a classe Loja apenas UMA vez no topo
class Loja(models.Model):
    nome = models.CharField(max_length=100)
    endereco = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Endereço"
    )

    def __str__(self):
        return self.nome


class Fruta(models.Model):
    TIPO_ARMAZEM_CHOICES = [
        ('DEPOSITO', 'Depósito'),
        ('CAMARA_FRIA', 'Câmara Fria'),
    ]

    nome = models.CharField(max_length=100)
    dias_validade_padrao = models.PositiveIntegerField(
        help_text='Validade média em dias após a colheita/recebimento'
    )
    armazem_recomendado = models.CharField(
        max_length=20, choices=TIPO_ARMAZEM_CHOICES, default='DEPOSITO'
    )

    def __str__(self):
        return self.nome

    @property
    def estoque_fisico(self):
        total = LoteEntrada.objects.filter(fruta=self).aggregate(
            total=Sum('quantidade_atual')
        )['total']
        return total or Decimal('0.00')

    @property
    def estoque_reservado(self):
        total = ItemPedido.objects.filter(
            fruta=self,
            pedido__status='CONFIRMADO'
        ).aggregate(
            total=Sum('quantidade')
        )['total']
        return total or Decimal('0.00')

    @property
    def estoque_disponivel(self):
        disponivel = self.estoque_fisico - self.estoque_reservado
        return max(disponivel, Decimal('0.00'))


class LoteEntrada(models.Model):
    codigo_lote = models.CharField(max_length=50, unique=True)
    fruta = models.ForeignKey(Fruta, on_delete=models.CASCADE, related_name='lotes')
    quantidade_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=2)
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_validade = models.DateField(null=True, blank=True)
    local_armazenado = models.CharField(
        max_length=20,
        choices=Fruta.TIPO_ARMAZEM_CHOICES,
        default='DEPOSITO'
    )

    def __str__(self):
        return f'{self.codigo_lote} - {self.fruta.nome}'


class SaidaEstoque(models.Model):
    lote = models.ForeignKey(
        LoteEntrada, on_delete=models.PROTECT, related_name='saidas'
    )
    loja_destino = models.ForeignKey(Loja, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    data_saida = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f'{self.quantidade} de {self.lote.fruta.nome} -> {self.loja_destino.nome}'


class MovimentacaoEstoque(models.Model):
    TIPO_MOVIMENTACAO_CHOICES = [
        ('VENDA', 'Venda'),
        ('PERDA', 'Perda / Descarte'),
        ('TRANSFERENCIA', 'Transferência Interna'),
    ]

    lote = models.ForeignKey(
        LoteEntrada, on_delete=models.CASCADE, related_name='movimentacoes'
    )
    tipo = models.CharField(
        max_length=20, choices=TIPO_MOVIMENTACAO_CHOICES, default='VENDA'
    )
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    observacao = models.TextField(blank=True, null=True)
    data_movimentacao = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f'{self.tipo} - {self.quantidade} ({self.lote.codigo_lote})'


class Pedido(models.Model):
    CANAL_CHOICES = [
        ('TELEFONE', '📞 Direto / Telefone / WhatsApp'),
        ('LOJA', '🏬 Solicitação de Loja'),
        ('IFOOD', '🛵 iFood'),
    ]

    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('CONFIRMADO', 'Confirmado / Em Separação'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    codigo_pedido = models.CharField(
        max_length=50, unique=True, editable=False, blank=True
    )
    canal_venda = models.CharField(
        max_length=20,
        choices=CANAL_CHOICES,
        default='LOJA',
        verbose_name='Canal de Venda',
    )
    # CAMPO NOVO ADICIONADO AQUI:
    loja_solicitante = models.ForeignKey(
        Loja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Loja Solicitante',
        related_name='pedidos'
    )
    cliente_nome = models.CharField(
        max_length=150, verbose_name='Nome do Solicitante / Cliente'
    )
    cliente_telefone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name='Telefone'
    )
    codigo_ifood = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Nº Pedido iFood (Opções)',
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='CONFIRMADO'
    )
    valor_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-data_criacao']

    def save(self, *args, **kwargs):
        if not self.codigo_pedido:
            prefixo = 'IFOOD' if self.canal_venda == 'IFOOD' else 'PED'
            sufixo_unico = uuid.uuid4().hex[:6].upper()
            self.codigo_pedido = f"{prefixo}-{timezone.now().strftime('%Y%m%d')}-{sufixo_unico}"
        super().save(*args, **kwargs)

    def atualizar_valor_total(self):
        total = self.itens.aggregate(
            total=Sum(F('quantidade') * F('preco_unitario'))
        )['total'] or Decimal('0.00')

        self.valor_total = total
        self.save(update_fields=['valor_total'])

    def __str__(self):
        loja_str = f" ({self.loja_solicitante.nome})" if self.loja_solicitante else ""
        return f'{self.codigo_pedido} - {self.cliente_nome}{loja_str}'

class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name='itens'
    )
    fruta = models.ForeignKey(Fruta, on_delete=models.PROTECT)
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Quantidade em Kg ou Unidades',
    )
    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Preço Unitário (R$)',
    )
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, editable=False, default=Decimal('0.00')
    )

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)
        self.pedido.atualizar_valor_total()

    def delete(self, *args, **kwargs):
        pedido = self.pedido
        super().delete(*args, **kwargs)
        pedido.atualizar_valor_total()

    def __str__(self):
        return f'{self.quantidade}x {self.fruta.nome} no Pedido #{self.pedido.codigo_pedido}'


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    quantidade = models.IntegerField(default=0)
    preco = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.nome
