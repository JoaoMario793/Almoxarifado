from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Setor(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    sigla = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Setor'
        verbose_name_plural = 'Setores'

    def __str__(self):
        return f'{self.nome} ({self.sigla})' if self.sigla else self.nome


class PerfilUsuario(models.Model):
    class Perfil(models.TextChoices):
        GERENCIA = 'GERENCIA', 'Gerência'
        SOLICITANTE = 'SOLICITANTE', 'Solicitante'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    setor = models.ForeignKey(
        Setor,
        on_delete=models.PROTECT,
        related_name='perfis',
    )
    tipo_perfil = models.CharField(
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.SOLICITANTE,
    )

    class Meta:
        verbose_name = 'Perfil de utilizador'
        verbose_name_plural = 'Perfis de utilizadores'

    def __str__(self):
        return f'{self.usuario.username} - {self.get_tipo_perfil_display()}'

    @property
    def is_gerencia(self):
        return self.tipo_perfil == self.Perfil.GERENCIA or self.usuario.is_staff


class Material(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    nome = models.CharField(max_length=150)
    categoria = models.CharField(max_length=100)
    unidade_medida = models.CharField(max_length=30)
    saldo = models.PositiveIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['codigo', 'nome']
        verbose_name = 'Material'
        verbose_name_plural = 'Materiais'

    def __str__(self):
        return f'{self.codigo} - {self.nome}'

    @property
    def status_disponibilidade(self):
        return 'Disponível' if self.saldo > 0 else 'Sem estoque'


class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        ATENDIDO = 'ATENDIDO', 'Atendido'
        RECUSADO = 'RECUSADO', 'Recusado'

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='pedidos',
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pedidos_solicitados',
    )
    setor = models.ForeignKey(
        Setor,
        on_delete=models.PROTECT,
        related_name='pedidos',
    )
    quantidade = models.PositiveIntegerField()
    justificativa = models.TextField()
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    motivo_recusa = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='pedidos_decididos',
    )
    decidido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f'Pedido #{self.pk} - {self.material.nome} ({self.get_status_display()})'

    def clean(self):
        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError({'quantidade': 'A quantidade deve ser maior que zero.'})
        if self.status == self.Status.RECUSADO and not self.motivo_recusa.strip():
            raise ValidationError({'motivo_recusa': 'Informe o motivo da recusa.'})


class Movimentacao(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA = 'SAIDA', 'Saída'

    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='movimentacoes',
    )
    quantidade = models.PositiveIntegerField()
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='movimentacoes_registradas',
    )
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Movimentação'
        verbose_name_plural = 'Movimentações'

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.material.nome} ({self.quantidade})'