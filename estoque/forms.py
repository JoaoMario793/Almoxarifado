from django import forms
from django.contrib.auth.models import Group, User
from django.db import transaction

from estoque.models import Material, Pedido, PerfilUsuario, Setor


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['codigo', 'nome', 'categoria', 'unidade_medida']
        labels = {
            'codigo': 'Código',
            'nome': 'Nome do material',
            'categoria': 'Categoria',
            'unidade_medida': 'Unidade de medida',
        }


class EntradaEstoqueForm(forms.Form):
    material = forms.ModelChoiceField(
        queryset=Material.objects.all().order_by('codigo', 'nome'),
        label='Material',
    )
    quantidade = forms.IntegerField(min_value=1, label='Quantidade de entrada')

    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        if quantidade <= 0:
            raise forms.ValidationError('Informe uma quantidade positiva maior que zero.')
        return quantidade


class PedidoCreateForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['material', 'quantidade', 'justificativa']
        labels = {
            'material': 'Material',
            'quantidade': 'Quantidade solicitada',
            'justificativa': 'Justificativa',
        }
        widgets = {
            'justificativa': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        if quantidade <= 0:
            raise forms.ValidationError('A quantidade deve ser maior que zero.')
        return quantidade


class DecisaoPedidoForm(forms.Form):
    ACAO_ATENDER = 'ATENDER'
    ACAO_RECUSAR = 'RECUSAR'
    ESCOLHAS_ACAO = [
        (ACAO_ATENDER, 'Atender pedido'),
        (ACAO_RECUSAR, 'Recusar pedido'),
    ]

    acao = forms.ChoiceField(choices=ESCOLHAS_ACAO, label='Decisão')
    motivo_recusa = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label='Motivo da recusa',
    )

    def clean(self):
        cleaned_data = super().clean()
        acao = cleaned_data.get('acao')
        motivo = (cleaned_data.get('motivo_recusa') or '').strip()
        if acao == self.ACAO_RECUSAR and not motivo:
            self.add_error('motivo_recusa', 'É obrigatório informar o motivo ao recusar um pedido.')
        cleaned_data['motivo_recusa'] = motivo
        return cleaned_data


class CadastroSolicitanteForm(forms.Form):
    nome_completo = forms.CharField(max_length=150, label='Nome')
    username = forms.CharField(max_length=150, label='Utilizador (username)')
    setor = forms.ModelChoiceField(
        queryset=Setor.objects.all().order_by('nome'),
        label='Setor de lotação',
    )
    senha_inicial = forms.CharField(
        widget=forms.PasswordInput,
        min_length=6,
        label='Senha inicial',
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Já existe um utilizador com esse nome de utilizador.')
        return username

    @transaction.atomic
    def salvar(self):
        partes = self.cleaned_data['nome_completo'].strip().split(' ', 1)
        primeiro_nome = partes[0]
        sobrenome = partes[1] if len(partes) > 1 else ''

        usuario = User.objects.create_user(
            username=self.cleaned_data['username'].strip(),
            password=self.cleaned_data['senha_inicial'],
            first_name=primeiro_nome,
            last_name=sobrenome,
        )
        grupo_solicitante, _ = Group.objects.get_or_create(name='Solicitante')
        usuario.groups.add(grupo_solicitante)

        PerfilUsuario.objects.create(
            usuario=usuario,
            setor=self.cleaned_data['setor'],
            tipo_perfil=PerfilUsuario.Perfil.SOLICITANTE,
        )
        return usuario