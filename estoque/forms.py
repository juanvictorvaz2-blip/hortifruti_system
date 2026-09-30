from django import forms
from .models import LoteEntrada, SaidaEstoque, Fruta, Loja
from .models import MovimentacaoEstoque
from .models import CompraCeasa, Fruta

class LoteEntradaForm(forms.ModelForm):
    class Meta:
        model = LoteEntrada
        fields = [
            'fruta',
            'quantidade_inicial',
            'quantidade_atual',
            'preco_custo',
            'preco_venda_caixa',
            'preco_venda_banca',
            'lojas_destinatarias',
            'data_validade',
            'local_armazenado',
        ]
        widgets = {
            'fruta': forms.Select(attrs={'class': 'form-control'}),
            'quantidade_inicial': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': 'Ex: 100.00',
                }
            ),
            'quantidade_atual': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': 'Deixe em branco para usar a Qtd Inicial',
                }
            ),
            'preco_custo': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': '0.00',
                }
            ),
            'preco_venda_caixa': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': '0.00',
                }
            ),
            'preco_venda_banca': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': '0.00',
                }
            ),
            'lojas_destinatarias': forms.CheckboxSelectMultiple(
                attrs={'class': 'list-unstyled'}
            ),
            'data_validade': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'local_armazenado': forms.Select(
                attrs={'class': 'form-control'},
                choices=Fruta.TIPO_ARMAZEM_CHOICES,
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantidade_atual'].required = False
        self.fields['data_validade'].required = False
        self.fields['local_armazenado'].required = False
        self.fields['preco_custo'].required = False
        self.fields['preco_venda_caixa'].required = False
        self.fields['preco_venda_banca'].required = False
        self.fields['lojas_destinatarias'].required = False

class SaidaEstoqueForm(forms.ModelForm):
    class Meta:
        model = SaidaEstoque
        fields = ['lote', 'loja_destino', 'quantidade']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lote'].queryset = LoteEntrada.objects.filter(quantidade_atual__gt=0)

class CompraCeasaForm(forms.ModelForm):
    nome_nova_fruta = forms.CharField(
        max_length=100,
        required=False,
        label="Nome da Fruta / Variedade",
        help_text="Digite se a fruta não estiver na lista abaixo (ex: Maçã Gala 120)."
    )

    class Meta:
        model = CompraCeasa
        fields = [
            'fruta', 'nome_nova_fruta', 'quantidade_comprada',
            'preco_custo', 'preco_venda_caixa', 'preco_venda_banca',
            'lojas_destinatarias'
        ]
        widgets = {
            'fruta': forms.Select(attrs={'class': 'form-select'}),
            'lojas_destinatarias': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'quantidade_comprada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda_caixa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda_banca': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fruta'].required = False

class BaixaLoteForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoEstoque
        fields = ['tipo', 'quantidade', 'observacao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': 'Qtd. a retirar',
                }
            ),
            'observacao': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Motivo da baixa ou observações (opcional)',
                }
            ),
        }

