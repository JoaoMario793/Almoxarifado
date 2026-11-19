from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from estoque.models import Material, Movimentacao, PerfilUsuario, Setor


class Command(BaseCommand):
    help = 'Popula o banco SQLite com dados fictícios para o sistema de almoxarifado.'

    @transaction.atomic
    def handle(self, *args, **options):
        grupo_gerencia, _ = Group.objects.get_or_create(name='Gerencia')
        grupo_solicitante, _ = Group.objects.get_or_create(name='Solicitante')

        setor_almox, _ = Setor.objects.get_or_create(
            nome='Almoxarifado e Patrimônio',
            defaults={'sigla': 'ALMOX'},
        )
        setor_lab, _ = Setor.objects.get_or_create(
            nome='Coordenação de Informática',
            defaults={'sigla': 'COINF'},
        )
        setor_acad, _ = Setor.objects.get_or_create(
            nome='Secretaria Acadêmica',
            defaults={'sigla': 'SECAC'},
        )

        gerente, created = User.objects.get_or_create(
            username='gerente_demo',
            defaults={
                'first_name': 'Marcos',
                'last_name': 'Oliveira',
                'email': 'gerente.demo@exemplo.edu.br',
            },
        )
        if created:
            gerente.set_password('SenhaForte123!')
            gerente.save()
        gerente.groups.add(grupo_gerencia)
        PerfilUsuario.objects.get_or_create(
            usuario=gerente,
            defaults={
                'setor': setor_almox,
                'tipo_perfil': PerfilUsuario.Perfil.GERENCIA,
            },
        )

        solicitantes_dados = [
            ('solicitante1', 'Ana', 'Souza', 'ana.souza@exemplo.edu.br', setor_lab),
            ('solicitante2', 'Lucas', 'Pereira', 'lucas.pereira@exemplo.edu.br', setor_acad),
        ]
        for username, nome, sobrenome, email, setor in solicitantes_dados:
            user, u_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nome,
                    'last_name': sobrenome,
                    'email': email,
                },
            )
            if u_created:
                user.set_password('SenhaForte123!')
                user.save()
            user.groups.add(grupo_solicitante)
            PerfilUsuario.objects.get_or_create(
                usuario=user,
                defaults={
                    'setor': setor,
                    'tipo_perfil': PerfilUsuario.Perfil.SOLICITANTE,
                },
            )

        materiais_iniciais = [
            ('MAT-001', 'Caneta Esferográfica Azul', 'Expediente', 'un', 25),
            ('MAT-002', 'Álcool em Gel 70%', 'Limpeza e Higiene', 'un', 10),
            ('MAT-003', 'Cabo HDMI 2.0', 'Informática', 'un', 0),
        ]
        for codigo, nome, categoria, unidade, saldo_inicial in materiais_iniciais:
            material, m_created = Material.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nome': nome,
                    'categoria': categoria,
                    'unidade_medida': unidade,
                    'saldo': saldo_inicial,
                },
            )
            if m_created and saldo_inicial > 0:
                Movimentacao.objects.create(
                    tipo=Movimentacao.Tipo.ENTRADA,
                    material=material,
                    quantidade=saldo_inicial,
                    responsavel=gerente,
                )

        self.stdout.write(self.style.SUCCESS('Dados fictícios carregados com sucesso.'))