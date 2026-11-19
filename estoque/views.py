from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from estoque.forms import (
    CadastroSolicitanteForm,
    DecisaoPedidoForm,
    EntradaEstoqueForm,
    MaterialForm,
    PedidoCreateForm,
)
from estoque.models import Material, Movimentacao, Pedido, PerfilUsuario


def _eh_gerencia(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if user.groups.filter(name__iexact='Gerencia').exists():
        return True
    perfil = getattr(user, 'perfil', None)
    return bool(perfil and perfil.tipo_perfil == PerfilUsuario.Perfil.GERENCIA)


def _obter_setor_usuario(user):
    perfil = getattr(user, 'perfil', None)
    return perfil.setor if perfil else None


@login_required
def catalogo_view(request):
    termo = (request.GET.get('q') or '').strip()
    materiais = Material.objects.all().order_by('codigo', 'nome')
    if termo:
        materiais = materiais.filter(
            Q(nome__icontains=termo) | Q(codigo__icontains=termo)
        )

    contexto = {
        'materiais': materiais,
        'termo': termo,
        'eh_gerencia': _eh_gerencia(request.user),
    }
    return render(request, 'estoque/catalogo.html', contexto)


@login_required
def material_criar_view(request):
    if not _eh_gerencia(request.user):
        return HttpResponseForbidden(
            'Acesso negado: apenas contas de gerência podem cadastrar materiais.'
        )

    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.saldo = 0
            material.save()
            messages.success(request, f'Material "{material.nome}" cadastrado com sucesso.')
            return redirect('estoque:catalogo')
    else:
        form = MaterialForm()

    return render(
        request,
        'estoque/material_form.html',
        {'form': form, 'titulo': 'Cadastrar material', 'eh_gerencia': True},
    )


@login_required
def material_editar_view(request, pk):
    if not _eh_gerencia(request.user):
        return HttpResponseForbidden(
            'Acesso negado: apenas contas de gerência podem editar materiais.'
        )

    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, f'Material "{material.nome}" atualizado com sucesso.')
            return redirect('estoque:catalogo')
    else:
        form = MaterialForm(instance=material)

    return render(
        request,
        'estoque/material_form.html',
        {
            'form': form,
            'material': material,
            'titulo': f'Editar material — {material.codigo}',
            'eh_gerencia': True,
        },
    )


@login_required
def entrada_estoque_view(request):
    if not _eh_gerencia(request.user):
        return HttpResponseForbidden(
            'Acesso negado: apenas contas de gerência podem registrar entradas de estoque.'
        )

    if request.method == 'POST':
        form = EntradaEstoqueForm(request.POST)
        if form.is_valid():
            material_escolhido = form.cleaned_data['material']
            quantidade = form.cleaned_data['quantidade']

            with transaction.atomic():
                material = Material.objects.select_for_update().get(pk=material_escolhido.pk)
                material.saldo += quantidade
                material.save(update_fields=['saldo', 'atualizado_em'])
                Movimentacao.objects.create(
                    tipo=Movimentacao.Tipo.ENTRADA,
                    material=material,
                    quantidade=quantidade,
                    responsavel=request.user,
                )

            messages.success(
                request,
                f'Entrada de {quantidade} ({material.unidade_medida}) registrada para "{material.nome}". '
                f'Novo saldo: {material.saldo}.',
            )
            return redirect('estoque:entrada_estoque')
    else:
        form = EntradaEstoqueForm()

    entradas_recentes = Movimentacao.objects.select_related(
        'material', 'responsavel'
    ).filter(tipo=Movimentacao.Tipo.ENTRADA)[:15]

    return render(
        request,
        'estoque/entrada_estoque.html',
        {
            'form': form,
            'entradas_recentes': entradas_recentes,
            'eh_gerencia': True,
        },
    )


@login_required
def solicitantes_gerir_view(request):
    if not _eh_gerencia(request.user):
        return HttpResponseForbidden(
            'Acesso negado: apenas contas de gerência podem gerenciar solicitantes.'
        )

    if request.method == 'POST':
        form = CadastroSolicitanteForm(request.POST)
        if form.is_valid():
            novo_user = form.salvar()
            messages.success(
                request,
                f'Conta de solicitante "{novo_user.username}" cadastrada com sucesso.',
            )
            return redirect('estoque:solicitantes')
    else:
        form = CadastroSolicitanteForm()

    perfis = PerfilUsuario.objects.select_related('usuario', 'setor').filter(
        tipo_perfil=PerfilUsuario.Perfil.SOLICITANTE
    ).order_by('usuario__username')

    return render(
        request,
        'estoque/solicitantes.html',
        {'form': form, 'perfis': perfis, 'eh_gerencia': True},
    )


@login_required
def pedido_criar_view(request):
    setor = _obter_setor_usuario(request.user)
    if setor is None:
        messages.error(
            request,
            'O seu utilizador não possui setor de lotação associado. Contacte a gerência.',
        )
        return redirect('estoque:catalogo')

    if request.method == 'POST':
        form = PedidoCreateForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.solicitante = request.user
            pedido.setor = setor
            pedido.status = Pedido.Status.PENDENTE
            pedido.save()
            messages.success(
                request,
                f'Pedido #{pedido.pk} criado com status Pendente. O saldo em estoque mantém-se inalterado até o atendimento.',
            )
            return redirect('estoque:meus_pedidos')
    else:
        form = PedidoCreateForm()

    return render(
        request,
        'estoque/pedido_form.html',
        {
            'form': form,
            'setor': setor,
            'eh_gerencia': _eh_gerencia(request.user),
        },
    )


@login_required
def meus_pedidos_view(request):
    pedidos = Pedido.objects.select_related(
        'material', 'setor', 'solicitante', 'decidido_por'
    ).filter(solicitante=request.user)

    return render(
        request,
        'estoque/meus_pedidos.html',
        {
            'pedidos': pedidos,
            'eh_gerencia': _eh_gerencia(request.user),
        },
    )


@login_required
def pedidos_gerencia_view(request):
    if not _eh_gerencia(request.user):
        return HttpResponseForbidden(
            'Acesso negado: apenas contas de gerência podem consultar ou analisar pedidos.'
        )

    pendentes = Pedido.objects.select_related(
        'material', 'solicitante', 'setor'
    ).filter(status=Pedido.Status.PENDENTE).order_by('criado_em')

    historico = Pedido.objects.select_related(
        'material', 'solicitante', 'setor', 'decidido_por'
    ).exclude(status=Pedido.Status.PENDENTE).order_by('-decidido_em', '-criado_em')[:20]

    movimentacoes = Movimentacao.objects.select_related(
        'material', 'responsavel', 'pedido', 'pedido__solicitante', 'pedido__setor'
    )[:20]

    return render(
        request,
        'estoque/pedidos_gerencia.html',
        {
            'pendentes': pendentes,
            'historico': historico,
            'movimentacoes': movimentacoes,
            'eh_gerencia': True,
        },
    )


@login_required
def pedido_decidir_view(request, pk):
    if not _eh_gerencia(request.user):
        return HttpResponseForbidden(
            'Acesso negado: apenas contas de gerência podem atender ou recusar pedidos.'
        )

    if request.method != 'POST':
        return redirect('estoque:pedidos_gerencia')

    form = DecisaoPedidoForm(request.POST)
    if not form.is_valid():
        for campo, erros in form.errors.items():
            for erro in erros:
                messages.error(request, erro)
        return redirect('estoque:pedidos_gerencia')

    acao = form.cleaned_data['acao']
    motivo_recusa = form.cleaned_data['motivo_recusa']

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().select_related(
            'material', 'solicitante', 'setor'
        ).get(pk=pk)

        if pedido.status != Pedido.Status.PENDENTE:
            messages.warning(
                request,
                f'O pedido #{pedido.pk} já foi decidido anteriormente ({pedido.get_status_display()}) e não pode ser processado novamente.',
            )
            return redirect('estoque:pedidos_gerencia')

        if acao == DecisaoPedidoForm.ACAO_RECUSAR:
            pedido.status = Pedido.Status.RECUSADO
            pedido.motivo_recusa = motivo_recusa
            pedido.decidido_por = request.user
            pedido.decidido_em = timezone.now()
            pedido.save(
                update_fields=['status', 'motivo_recusa', 'decidido_por', 'decidido_em']
            )
            messages.info(request, f'Pedido #{pedido.pk} recusado com sucesso.')
            return redirect('estoque:pedidos_gerencia')

        material = Material.objects.select_for_update().get(pk=pedido.material.pk)
        if pedido.quantidade > material.saldo:
            messages.error(
                request,
                f'Saldo insuficiente para atender o pedido #{pedido.pk} ({material.nome}): '
                f'solicitado {pedido.quantidade}, saldo atual {material.saldo}. '
                f'O pedido permanece PENDENTE.',
            )
            return redirect('estoque:pedidos_gerencia')

        material.saldo -= pedido.quantidade
        material.save(update_fields=['saldo', 'atualizado_em'])

        pedido.status = Pedido.Status.ATENDIDO
        pedido.decidido_por = request.user
        pedido.decidido_em = timezone.now()
        pedido.save(update_fields=['status', 'decidido_por', 'decidido_em'])

        Movimentacao.objects.create(
            tipo=Movimentacao.Tipo.SAIDA,
            material=material,
            quantidade=pedido.quantidade,
            responsavel=request.user,
            pedido=pedido,
        )

        messages.success(
            request,
            f'Pedido #{pedido.pk} atendido! Saída de {pedido.quantidade} {material.unidade_medida} '
            f'para {pedido.solicitante.get_full_name() or pedido.solicitante.username} '
            f'({pedido.setor.nome}). Saldo atual: {material.saldo}.',
        )

    return redirect('estoque:pedidos_gerencia')