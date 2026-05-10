"""Cria dados de teste de Pessoa/Entidade/Tag/Demanda para verificação manual.

Idempotente: rodar duas vezes não duplica registros (busca por email/CNPJ/nome).
Exige DEBUG=True — semear dados em produção é responsabilidade explícita do admin.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Usuario
from demandas.models import Demanda, DemandaPessoa, Encaminhamento, Tema
from pessoas.models import (
    EmailPessoa,
    Entidade,
    Pessoa,
    RedeSocial,
    Tag,
    Telefone,
    Vinculo,
)


class Command(BaseCommand):
    help = "Cria dados fictícios para teste manual da Fase 2 (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Recusado: este comando só roda com DEBUG=True (ambiente de desenvolvimento)."
            )

        admin = Usuario.objects.filter(email="admin@mpd.local").first()
        if not admin:
            raise CommandError(
                "Usuário admin@mpd.local não existe. Rode `criar_usuarios_iniciais` primeiro."
            )

        # --- Tags ---
        tags_alvo = [
            ("Saúde", "#33b679"),
            ("Educação", "#3f51b5"),
            ("Comunidade", "#f4511e"),
            ("Líder local", "#8e24aa"),
        ]
        for nome, cor in tags_alvo:
            tag, criada = Tag.objects.get_or_create(nome=nome, defaults={"cor": cor})
            if criada:
                self.stdout.write(self.style.SUCCESS(f"Tag criada: {nome}"))

        # --- Pessoa: Maria Exemplo (dados fictícios) ---
        maria, criada_maria = Pessoa.objects.get_or_create(
            nome="Maria",
            sobrenome="Exemplo",
            defaults={
                "bairro": "Praia do Canto",
                "cidade": "Vitória",
                "estado": "ES",
                "criado_por": admin,
            },
        )
        if criada_maria:
            self.stdout.write(self.style.SUCCESS("Pessoa criada: Maria Exemplo"))
        if not maria.emails.exists():
            EmailPessoa.objects.create(pessoa=maria, endereco="maria.exemplo@example.com")
        if not maria.telefones.exists():
            Telefone.objects.create(
                pessoa=maria,
                numero="27999990000",
                tipo=Telefone.TIPO_CELULAR,
                eh_whatsapp=True,
            )
        if not maria.redes_sociais.exists():
            RedeSocial.objects.create(
                pessoa=maria, plataforma=RedeSocial.PLATAFORMA_INSTAGRAM, valor="maria_exemplo"
            )
        # Tags na Maria
        maria.tags.add(*Tag.objects.filter(nome__in=["Saúde", "Comunidade"]))

        # --- Entidade: Família Exemplo (fictícia) ---
        familia, criada_familia = Entidade.objects.get_or_create(
            nome="Família Exemplo",
            defaults={"tipo": "familia", "criado_por": admin},
        )
        if criada_familia:
            self.stdout.write(self.style.SUCCESS("Entidade criada: Família Exemplo"))

        # --- Vínculo Maria <-> Família Exemplo ---
        Vinculo.objects.get_or_create(pessoa=maria, entidade=familia, defaults={"papel": "Filha"})

        # --- Pessoa: João Silva (caso de teste com fixo + 2 emails) ---
        joao, criado_joao = Pessoa.objects.get_or_create(
            nome="João",
            sobrenome="Silva",
            defaults={
                "bairro": "Centro",
                "cidade": "Vitória",
                "estado": "ES",
                "criado_por": admin,
            },
        )
        if criado_joao:
            self.stdout.write(self.style.SUCCESS("Pessoa criada: João Silva"))
        if not joao.emails.exists():
            EmailPessoa.objects.create(
                pessoa=joao, endereco="joao.silva@example.com", rotulo="pessoal"
            )
            EmailPessoa.objects.create(pessoa=joao, endereco="joao@empresa.com", rotulo="trabalho")
        if not joao.telefones.exists():
            Telefone.objects.create(
                pessoa=joao, numero="2733334444", tipo=Telefone.TIPO_FIXO, rotulo="recado"
            )
            Telefone.objects.create(
                pessoa=joao,
                numero="27988887777",
                tipo=Telefone.TIPO_CELULAR,
                eh_whatsapp=True,
            )
        joao.tags.add(*Tag.objects.filter(nome__in=["Líder local", "Educação"]))

        # --- Entidade formal: Associação Bairro Centro ---
        Entidade.objects.get_or_create(
            nome="Associação de Moradores do Centro",
            defaults={
                "tipo": "associacao_de_moradores",
                "cnpj": "11222333000181",
                "bairro": "Centro",
                "cidade": "Vitória",
                "estado": "ES",
                "criado_por": admin,
            },
        )

        # --- Temas (Fase 3 / ADR 0042) ---
        temas_alvo = [
            ("Mobilidade urbana", "#039be5"),
            ("Saúde", "#33b679"),
            ("Educação", "#3f51b5"),
            ("Cultura", "#8e24aa"),
            ("Infraestrutura", "#f4511e"),
        ]
        for nome, cor in temas_alvo:
            tema, criado = Tema.objects.get_or_create(nome=nome, defaults={"cor": cor})
            if criado:
                self.stdout.write(self.style.SUCCESS(f"Tema criado: {nome}"))

        # --- Demandas exemplo (Fase 3) ---
        if not Demanda.objects.filter(titulo="Pavimentação Rua das Flores").exists():
            d1 = Demanda.objects.create(
                titulo="Pavimentação Rua das Flores",
                descricao="Moradores relatam buracos. Pedido de tapa-buracos urgente.",
                origem=Demanda.ORIGEM_RESPONSIVA,
                canal_entrada="whatsapp",
                coordenacao_responsavel=Demanda.COORDENACAO_GABINETE,
                criado_por=admin,
                responsavel=admin,
            )
            DemandaPessoa.objects.create(demanda=d1, pessoa=maria, papel="solicitante")
            d1.temas.add(*Tema.objects.filter(nome__in=["Mobilidade urbana", "Infraestrutura"]))
            Encaminhamento.objects.create(
                demanda=d1,
                destinatario_orgao="Secretaria de Obras",
                tipo_documento="oficio",
                data_envio=timezone.now().date(),
                criado_por=admin,
            )
            self.stdout.write(self.style.SUCCESS(f"Demanda criada: {d1.numero}"))

        if not Demanda.objects.filter(titulo="Moção de aplausos — coletivo cultural").exists():
            d2 = Demanda.objects.create(
                titulo="Moção de aplausos — coletivo cultural",
                descricao="Reconhecimento ao trabalho do coletivo no carnaval do bairro.",
                origem=Demanda.ORIGEM_PROATIVA,
                canal_entrada="presencial",
                coordenacao_responsavel=Demanda.COORDENACAO_COMUNICACAO,
                criado_por=admin,
                anonimo=True,
                resultado=Demanda.RESULTADO_NAO_SE_APLICA,
            )
            d2.temas.add(*Tema.objects.filter(nome="Cultura"))
            self.stdout.write(self.style.SUCCESS(f"Demanda criada: {d2.numero}"))

        self.stdout.write(self.style.SUCCESS("Dados de teste sincronizados."))
