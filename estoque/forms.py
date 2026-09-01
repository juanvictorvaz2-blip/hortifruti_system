from django import forms
from .models import LoteEntrada, SaidaEstoque, Fruta, Loja
from .models import MovimentacaoEstoque

class LoteEntradaForm(forms.ModelForm):
    class Meta:
        model = LoteEntrada
        fields = [
            'fruta',
            'quantidade_inicial',
            'quantidade_atual',
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
        # Torna a quantidade_atual opcional na tela
        self.fields['quantidade_atual'].required = False
class SaidaEstoqueForm(forms.ModelForm):
    class Meta:
        model = SaidaEstoque
        fields = ['lote', 'loja_destino', 'quantidade']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra para exibir apenas lotes que ainda possuem estoque disponível
        self.fields['lote'].queryset = LoteEntrada.objects.filter(quantidade_atual__gt=0)

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
